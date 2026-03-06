"""
工作流生成 Agent

使用 deepagent 加载 bisheng-workflow-generator skill（SKILL.md），
结合上下文信息（工具、知识库、用户需求）生成毕昇工作流；
提供 validate_workflow 工具供 agent 自检与迭代，提升生成质量。
"""

import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_core.runnables.config import RunnableConfig
from langchain_core.callbacks import UsageMetadataCallbackHandler

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

from models.intent import EnhancedIntent
from agents.tool_agent import ToolPlan
from agents.knowledge_agent import KnowledgeMatch
from core.utils import extract_json
from core.prompt_loader import get_prompt_loader

logger = logging.getLogger(__name__)

# 项目根目录（bisheng_generator 的上级），用于 deepagent skills 路径
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
# 两处 skills：ral/skills（含 bisheng-workflow-generator）、ral/.cursor/skills
_SKILLS_DIR = _REPO_ROOT / "skills"
_CURSOR_SKILLS_DIR = _REPO_ROOT / ".cursor" / "skills"
_BISHENG_SKILL_DIR = _SKILLS_DIR / "bisheng-workflow-generator"


def _resolve_skills_paths() -> Tuple[str, List[str]]:
    """
    解析 backend root_dir 与 skills 虚拟路径列表。
    root_dir 使用 resolve() 得到绝对路径；
    skills 只包含实际存在的目录，避免加载失败导致重试。
    """
    root = str(_REPO_ROOT.resolve())
    paths = []
    if _SKILLS_DIR.exists():
        paths.append("/skills/")
    else:
        logger.warning("skills 目录不存在，将不加载 ral/skills：%s", _SKILLS_DIR)
    if _CURSOR_SKILLS_DIR.exists():
        paths.append("/.cursor/skills/")
    else:
        logger.debug(".cursor/skills 不存在，跳过：%s", _CURSOR_SKILLS_DIR)
    if not paths:
        logger.warning("未找到任何 skills 目录（已检查 skills 与 .cursor/skills），工作流生成可能失败")
    return root, paths


def _log_skills_match_status(root_dir: str, skills_paths: List[str]) -> None:
    """打印 skills 目录与 bisheng-workflow-generator 的匹配情况，便于排查加载失败。"""
    skills_ok = _SKILLS_DIR.exists()
    bisheng_skill_ok = _BISHENG_SKILL_DIR.exists() and (_BISHENG_SKILL_DIR / "SKILL.md").exists()
    logger.info(
        "skills 匹配情况: root_dir=%s, 传入 paths=%s, /skills/ 目录存在=%s, "
        "bisheng-workflow-generator(SKILL.md) 存在=%s",
        root_dir,
        skills_paths,
        skills_ok,
        bisheng_skill_ok,
    )
    if not bisheng_skill_ok and skills_ok:
        logger.warning(
            "bisheng-workflow-generator 未找到，请确认存在 %s",
            _BISHENG_SKILL_DIR / "SKILL.md",
        )


def _get_last_assistant_content(messages: List[Any]) -> str:
    """从 agent 返回的 messages 中取最后一条带 content 的 assistant 消息。"""
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if hasattr(msg, "type") and msg.type == "ai":
            text = getattr(msg, "content", None)
            if isinstance(text, str) and text.strip():
                return text
        if isinstance(msg, dict):
            if msg.get("type") == "ai" or msg.get("role") == "assistant":
                text = msg.get("content", "")
                if isinstance(text, str) and text.strip():
                    return text
    return ""


def _validate_workflow_impl(
    workflow: Dict[str, Any], tool_plan: Optional[ToolPlan] = None
) -> List[str]:
    """
    程序化校验毕昇工作流 JSON，返回问题列表（空表示通过）。
    用于 validate_workflow 工具及后续可选的后处理校验。
    """
    issues: List[str] = []
    nodes = workflow.get("nodes") or []
    edges = workflow.get("edges") or []
    node_ids = {n.get("id") for n in nodes if n.get("id")}

    # 1. edges 引用的 node 必须存在
    for e in edges:
        src, tgt = e.get("source"), e.get("target")
        if src and src not in node_ids:
            issues.append(f"边引用了不存在的节点 source: {src}")
        if tgt and tgt not in node_ids:
            issues.append(f"边引用了不存在的节点 target: {tgt}")

    # 2. 必须有 start、input、output 等基础节点
    types_seen = {n.get("data", {}).get("type") for n in nodes}
    for required in ("start", "input", "output"):
        if required not in types_seen:
            issues.append(f"缺少必需节点类型: {required}")

    valid_tool_keys: set = set()
    if tool_plan and tool_plan.selected_tools:
        valid_tool_keys = {t.tool_key for t in tool_plan.selected_tools}

    # 3. 每个 tool 节点：tool_key 必须在候选内；输出必须被某 LLM 引用
    tool_node_ids = []
    for node in nodes:
        data = node.get("data", {})
        if data.get("type") != "tool":
            continue
        nid = node.get("id", "")
        tool_node_ids.append(nid)
        tk = data.get("tool_key", "")
        if valid_tool_keys and tk and tk not in valid_tool_keys:
            issues.append(
                f"工具节点 {nid} 的 tool_key '{tk}' 不在候选列表中，"
                "必须与候选工具的 tool_key 完全一致（含 MCP 后缀）"
            )

    # 4. 每个 tool 节点的输出应被至少一个 LLM 节点引用（禁止死分支）
    llm_refs = set()
    for node in nodes:
        data = node.get("data", {})
        if data.get("type") != "llm":
            continue
        for grp in data.get("group_params", []):
            for p in grp.get("params", []):
                val = p.get("value")
                if not isinstance(val, str):
                    continue
                # 匹配 {{#tool_xxx.output#}} 或 #tool_xxx.output#
                for m in re.finditer(r"#(tool_[a-zA-Z0-9_]+)\.output#", val):
                    llm_refs.add(m.group(1))
    for tid in tool_node_ids:
        if tid and tid not in llm_refs:
            issues.append(
                f"工具节点 {tid} 的输出未被任何 LLM 节点引用（禁止死分支），"
                "请在至少一个 LLM 节点的输入中使用 {{#" + tid + ".output#}}"
            )

    return issues


def _make_validate_workflow_tool(tool_plan: Optional[ToolPlan]) -> Any:
    """构造 validate_workflow 工具（闭包 tool_plan），供 deepagent 自检与迭代。"""

    @tool
    def validate_workflow(workflow_json_str: str) -> str:
        """验证毕昇工作流 JSON 是否符合规范。
        输入为 JSON 字符串（可含 ```json 代码块）。
        返回问题列表，每行一条；若无问题返回 OK。
        请根据返回的问题修正 JSON 后再次调用，直到返回 OK 或已迭代多次。"""
        w = extract_json(workflow_json_str)
        if not w:
            return "无法解析为合法 JSON，请确保输入是有效的毕昇工作流 JSON（可用 ```json 代码块包裹）。"
        issues = _validate_workflow_impl(w, tool_plan)
        if not issues:
            return "OK"
        return "\n".join(issues)

    return validate_workflow


class WorkflowAgent:
    """工作流生成专家（基于 deepagent + skills，支持 validate_workflow 自检迭代）"""

    def __init__(
        self,
        llm: BaseChatModel,
        prompts_dir: Optional[str] = None,
    ):
        self.llm = llm
        self._prompts_dir = prompts_dir
        self._usage_callback = UsageMetadataCallbackHandler()

    async def generate_workflow(
        self,
        intent: EnhancedIntent,
        tool_plan: ToolPlan,
        knowledge_match: KnowledgeMatch,
    ) -> Dict[str, Any]:
        """
        生成毕昇工作流

        Args:
            intent: 用户意图
            tool_plan: 工具计划
            knowledge_match: 知识库匹配结果

        Returns:
            毕昇工作流 JSON 字典
        """
        tools_info = self._format_tools_info(tool_plan)
        knowledge_info = self._format_knowledge_info(knowledge_match)

        user_analysis = f"""需求描述：{intent.rewritten_input}
            工作流类型：{intent.get_workflow_type()}
            复杂度：{intent.complexity_hint}
            是否需要工具：{intent.needs_tool}
            是否需要知识库：{intent.needs_knowledge}
            是否多轮对话：{intent.multi_turn}
        """

        loader = get_prompt_loader(self._prompts_dir)
        system_tpl = loader.load("workflow/system.md")
        system_prompt = system_tpl.format(
            user_analysis=user_analysis,
            tools_info=tools_info,
            knowledge_info=knowledge_info,
        )

        user_msg_tpl = loader.load("workflow/user_message.txt")
        user_message = (
            user_msg_tpl.format(intent_rewritten_input=intent.rewritten_input)
        )

        validate_tool = _make_validate_workflow_tool(tool_plan)
        root_dir, skills_paths = _resolve_skills_paths()
        _log_skills_match_status(root_dir, skills_paths)
        logger.info(
            "调用 deepagent 生成工作流 JSON，root_dir=%s, skills=%s",
            root_dir,
            skills_paths,
        )
        backend = FilesystemBackend(root_dir=root_dir, virtual_mode=True)
        agent = create_deep_agent(
            model=self.llm,
            system_prompt=system_prompt,
            tools=[validate_tool],
            backend=backend,
            skills=skills_paths,
            debug=False,
        )

        result = await agent.ainvoke(
            input={"messages": [HumanMessage(content=user_message)]},
            config=RunnableConfig(
                callbacks=[self._usage_callback],
            ),
        )

        model_key = getattr(self.llm, "model_name", None) or getattr(
            self.llm, "model", None
        )
        if model_key:
            usage_metadata = self._usage_callback.usage_metadata.get(model_key)
            if usage_metadata:
                logger.info(
                    "LLM 调用完成，tokens: in=%s out=%s total=%s",
                    usage_metadata.get("input_tokens"),
                    usage_metadata.get("output_tokens"),
                    usage_metadata.get("total_tokens"),
                )

        # 取最后一条带 content 的 assistant 消息（可能中间有 tool 调用）
        content = _get_last_assistant_content(result.get("messages") or [])

        if not content:
            logger.warning("deepagent 未返回有效文本内容")
            return {"error": "工作流生成失败", "content": ""}

        workflow_json = extract_json(content)

        if not workflow_json:
            logger.warning("工作流 JSON 提取失败")
            # 如果生成失败，返回错误信息
            return {"error": "工作流生成失败", "content": content}

        # 规范化工作流，补全毕昇前端必需的 value 等字段，避免导入时报 "Cannot read properties of undefined (reading 'value')"
        workflow_json = self._normalize_workflow(workflow_json, tool_plan)

        logger.info("工作流生成成功，nodes=%s", len(workflow_json.get("nodes", [])))
        return workflow_json

    def _normalize_workflow(
        self, w: Dict[str, Any], tool_plan: Optional[ToolPlan] = None
    ) -> Dict[str, Any]:
        """
        规范化工作流 JSON，补全毕昇前端必需的字段，避免导入时报错
        （如 Cannot read properties of undefined (reading 'value')）

        包含：顶层字段、节点结构、param.value 补全、knowledge_retriever/llm 特殊参数、
        edges、viewport、tool_key 修复等。
        """
        from datetime import datetime

        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

        # 1. 顶层字段
        self._normalize_top_level(w, now)

        # 2. 节点结构与 param 补全
        for node in w.get("nodes", []):
            self._normalize_node(node)

        # 3. edges 结构
        self._normalize_edges(w)

        # 4. viewport
        if "viewport" not in w or not isinstance(w["viewport"], dict):
            w["viewport"] = {"x": 0, "y": 0, "zoom": 1}
        vp = w["viewport"]
        vp.setdefault("x", 0)
        vp.setdefault("y", 0)
        vp.setdefault("zoom", 1)

        # 5. 修复被 LLM 截断的 MCP 工具 tool_key
        if tool_plan:
            self._fix_tool_keys(w, tool_plan)

        return w

    def _normalize_top_level(self, w: Dict[str, Any], now: str) -> None:
        """补全顶层必需字段"""
        if "guide_word" not in w or w["guide_word"] == "":
            for node in w.get("nodes", []):
                d = node.get("data", {})
                if d.get("type") == "start":
                    for grp in d.get("group_params", []):
                        for p in grp.get("params", []):
                            if (
                                p.get("key") == "guide_word"
                                and "value" in p
                                and p["value"]
                            ):
                                w["guide_word"] = p["value"]
                                break
                    break
            if "guide_word" not in w:
                w["guide_word"] = ""
        w.setdefault("create_time", now)
        w.setdefault("update_time", now)
        w.setdefault("logo", "")

    def _normalize_node(self, node: Dict[str, Any]) -> None:
        """规范化单个节点：结构、param.value、特殊参数"""
        node_id = node.get("id", "")
        data = node.setdefault("data", {})
        node_type = data.get("type")

        # 节点必需结构
        data.setdefault("id", node_id)
        data.setdefault("description", "")
        node.setdefault("type", "flowNode")
        node.setdefault("position", {"x": 0, "y": 0})
        node.setdefault("measured", {"width": 334, "height": 500})

        # tab 节点需有 tab.value（input 默认 dialog_input，llm 默认 single）
        if "tab" in data and isinstance(data["tab"], dict):
            tab = data["tab"]
            if "value" not in tab or not tab["value"]:
                opts = tab.get("options", [])
                default = "single" if node_type == "llm" else "dialog_input"
                tab["value"] = opts[0].get("key", default) if opts else default

        for grp in data.get("group_params", []):
            params = grp.get("params", [])
            for p in params:
                self._ensure_param_value(p)

            # knowledge_retriever 特殊参数
            if (
                node_type == "knowledge_retriever"
                and grp.get("name") == "知识库检索设置"
            ):
                self._ensure_knowledge_retriever_params(params)

            # llm 模型设置
            if node_type == "llm" and grp.get("name") == "模型设置":
                self._ensure_llm_model_params(params)

    def _ensure_param_value(self, p: Dict[str, Any]) -> None:
        """确保 param 有 value，根据 type 设置合理默认值"""
        pt = p.get("type", "")
        if "value" not in p or p["value"] is None:
            pass  # 继续走下面的默认值逻辑
        else:
            v = p["value"]
            if pt == "output_form" and isinstance(v, dict):
                v.setdefault("type", "")
                v.setdefault("value", "")
            elif pt == "var_textarea_file" and isinstance(v, dict):
                v.setdefault("msg", "")
                v.setdefault("files", [])
            elif pt == "var_textarea":
                # 毕昇工具节点（如联网搜索）执行时期望 query 等为字符串，非 str 会导致 expected string or bytes-like object
                if isinstance(v, dict):
                    raw = v.get("msg") or v.get("value") or ""
                    p["value"] = (
                        raw
                        if isinstance(raw, str)
                        else (str(raw) if raw is not None else "")
                    )
                elif not isinstance(v, str):
                    p["value"] = str(v) if v is not None else ""
            return

        pt = p.get("type", "")
        g = p.get("global", "")
        key = p.get("key", "")

        if pt == "var":
            if g == "key":
                p["value"] = ""
            elif str(g).startswith("code:"):
                p["value"] = []
            else:
                p["value"] = []
        elif pt == "switch":
            p["value"] = True
        elif pt == "slide":
            p["value"] = 0.3
        elif pt == "output_form":
            p["value"] = {"type": "", "value": ""}
        elif pt == "var_textarea_file":
            p["value"] = {"msg": "", "files": []}
        elif pt == "metadata_filter":
            p["value"] = {"enabled": False}
        elif pt == "search_switch":
            p["value"] = {
                "keyword_weight": 0.4,
                "vector_weight": 0.6,
                "user_auth": False,
                "search_switch": True,
                "rerank_flag": False,
                "rerank_model": "",
                "max_chunk_size": 15000,
            }
        elif key == "condition" and pt == "condition":
            # condition 节点，value 由 LLM 生成，缺失时给空数组
            if "value" not in p:
                p["value"] = []
        else:
            p["value"] = "" if pt not in ("input_list", "user_question") else []

    def _ensure_knowledge_retriever_params(self, params: List[Dict[str, Any]]) -> None:
        """知识库检索节点必须包含 metadata_filter、advanced_retrieval_switch"""
        keys = [x.get("key") for x in params]
        if "metadata_filter" not in keys:
            params.append(
                {
                    "key": "metadata_filter",
                    "type": "metadata_filter",
                    "label": "true",
                    "value": {"enabled": False},
                }
            )
        if "advanced_retrieval_switch" not in keys:
            params.append(
                {
                    "key": "advanced_retrieval_switch",
                    "type": "search_switch",
                    "label": "true",
                    "value": {
                        "keyword_weight": 0.4,
                        "vector_weight": 0.6,
                        "user_auth": False,
                        "search_switch": True,
                        "rerank_flag": False,
                        "rerank_model": "",
                        "max_chunk_size": 15000,
                    },
                }
            )

    def _ensure_llm_model_params(self, params: List[Dict[str, Any]]) -> None:
        """LLM 模型设置必须包含 temperature"""
        keys = [x.get("key") for x in params]
        if "temperature" not in keys:
            params.append(
                {
                    "key": "temperature",
                    "step": 0.1,
                    "type": "slide",
                    "label": "true",
                    "scope": [0, 2],
                    "value": 0.3,
                }
            )

    def _normalize_edges(self, w: Dict[str, Any]) -> None:
        """确保 edges 每项有必需字段"""
        for e in w.get("edges", []):
            e.setdefault("type", "customEdge")
            e.setdefault("animated", True)
            e.setdefault("sourceHandle", "right_handle")
            e.setdefault("targetHandle", "left_handle")
            if "id" not in e and "source" in e and "target" in e:
                sh = e.get("sourceHandle", "right_handle")
                th = e.get("targetHandle", "left_handle")
                e["id"] = f"xy-edge__{e['source']}{sh}-{e['target']}{th}"

    def _fix_tool_keys(self, w: Dict[str, Any], tool_plan: ToolPlan) -> None:
        """修复被 LLM 截断的 MCP 工具 tool_key（兜底逻辑）

        MCP 工具的 tool_key 格式为 {name}_{id}（如 get-current-date_28785811），
        LLM 生成时可能丢掉 _id 后缀。此方法通过 base name 匹配自动修复。
        """
        if not tool_plan.selected_tools:
            return

        valid_keys = {t.tool_key for t in tool_plan.selected_tools}

        # base_name -> full_key 映射，用于修复截断的 key
        base_to_full: Dict[str, str] = {}
        for t in tool_plan.selected_tools:
            base_to_full[t.tool_key] = t.tool_key
            base = re.sub(r"_\d{4,}$", "", t.tool_key)
            if base != t.tool_key:
                base_to_full[base] = t.tool_key

        for node in w.get("nodes", []):
            data = node.get("data", {})
            if data.get("type") != "tool":
                continue
            current_key = data.get("tool_key", "")
            if not current_key or current_key in valid_keys:
                continue
            if current_key in base_to_full:
                fixed_key = base_to_full[current_key]
                logger.warning(
                    "修复 tool_key：%s -> %s (node=%s)",
                    current_key,
                    fixed_key,
                    node.get("id"),
                )
                data["tool_key"] = fixed_key

    def _format_tools_info(self, tool_plan: ToolPlan) -> str:
        """格式化工具信息，区分内置工具与 MCP 工具并强调 tool_key 不可修改"""
        if not tool_plan.selected_tools:
            return "无工具调用需求"

        lines = [
            "⚠️ 重要：以下每个工具的 tool_key 必须原样写入生成的 JSON，"
            "禁止省略、修改或截断任何部分（MCP 工具的 _数字ID 后缀不可删除）：",
        ]
        for tool in tool_plan.selected_tools:
            tool_type = "MCP工具" if self._is_mcp_tool(tool) else "内置工具"
            lines.append(f'- [{tool_type}] tool_key: "{tool.tool_key}"（必须完全一致）')
            lines.append(f"  名称：{tool.name}")
            lines.append(f"  描述：{tool.desc}")
            if tool.parameters:
                params_info = []
                for p in tool.parameters:
                    name = p.get("name", "")
                    desc = p.get("description", "")
                    required = "必填" if p.get("required") else "选填"
                    params_info.append(
                        f"{name}({required}): {desc}" if desc else f"{name}({required})"
                    )
                lines.append(f"  参数：{params_info}")

        return "\n".join(lines)

    @staticmethod
    def _is_mcp_tool(tool) -> bool:
        """判断是否为 MCP 工具（非内置）"""
        if tool.extra:
            ct = tool.extra.get("connection_type", "")
            if ct and ct != "builtin":
                return True
        return bool(re.search(r"_\d{4,}$", tool.tool_key))

    def _format_knowledge_info(self, knowledge_match: KnowledgeMatch) -> str:
        """格式化知识库信息"""
        if not knowledge_match.matched_knowledge_bases:
            return "无知识库检索需求"

        lines = []
        for kb in knowledge_match.matched_knowledge_bases:
            lines.append(f"- ID: {kb.id}")
            lines.append(f"  名称：{kb.name}")
            lines.append(f"  描述：{kb.desc}")
            if kb.extra:
                collection = kb.extra.get("collection_name", "")
                if collection:
                    lines.append(f"  collection: {collection}")

        return "\n".join(lines)
