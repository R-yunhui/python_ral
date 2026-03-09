"""
工作流生成 Agent

直接加载 bisheng-workflow-generator SKILL.md 到 system prompt，
单次 LLM 调用生成毕昇工作流 JSON，配合程序化校验与修复循环。
"""

import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.callbacks import UsageMetadataCallbackHandler

from models.intent import EnhancedIntent
from agents.tool_agent import ToolPlan
from agents.knowledge_agent import KnowledgeMatch
from core.utils import extract_json
from core.prompt_loader import get_prompt_loader

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BISHENG_SKILL_DIR = _REPO_ROOT / "skills" / "bisheng-workflow-generator"

_skill_cache: Optional[str] = None


def _load_skill_content() -> str:
    """读取 SKILL.md 内容（启动后只读一次，缓存到内存）。"""
    global _skill_cache
    if _skill_cache is not None:
        return _skill_cache

    skill_path = _BISHENG_SKILL_DIR / "SKILL.md"
    if not skill_path.exists():
        logger.warning("SKILL.md 不存在: %s", skill_path)
        _skill_cache = ""
        return _skill_cache

    _skill_cache = skill_path.read_text(encoding="utf-8")
    logger.info("SKILL.md 已加载（%d 字符）", len(_skill_cache))
    return _skill_cache


def _get_branch_reachable(
    start: str,
    edges: list,
    node_type_map: Dict[str, str],
    stop_types: set = frozenset({"input", "start", "condition"}),
) -> set:
    """BFS 获取从 start 出发可达的所有节点，遇到 stop_types 类型的节点时停止（不纳入结果）。"""
    visited: set = set()
    result: set = set()
    queue = [start]
    while queue:
        nid = queue.pop(0)
        if nid in visited:
            continue
        visited.add(nid)
        nt = node_type_map.get(nid, "")
        if nt in stop_types and nid != start:
            continue
        result.add(nid)
        for e in edges:
            if e.get("source") == nid:
                t = e.get("target")
                if t and t not in visited:
                    queue.append(t)
    return result


def _validate_workflow_impl(
    workflow: Dict[str, Any], tool_plan: Optional[ToolPlan] = None
) -> List[str]:
    """
    程序化校验毕昇工作流 JSON，返回问题列表（空表示通过）。
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

    # 2. 必须有 start、input 基础节点；output 在有 output_user=true 的 LLM 时可选
    types_seen = {n.get("data", {}).get("type") for n in nodes}
    for required in ("start", "input"):
        if required not in types_seen:
            issues.append(f"缺少必需节点类型: {required}")
    has_output_user = any(
        p.get("key") == "output_user" and p.get("value") is True
        for n in nodes if n.get("data", {}).get("type") == "llm"
        for grp in n.get("data", {}).get("group_params", [])
        for p in grp.get("params", [])
    )
    if "output" not in types_seen and not has_output_user:
        issues.append("缺少 output 节点且没有 LLM 设置 output_user=true")

    valid_tool_keys: set = set()
    if tool_plan and tool_plan.selected_tools:
        valid_tool_keys = {t.tool_key for t in tool_plan.selected_tools}

    # 3. 每个 tool 节点：tool_key 必须在候选内
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
                for m in re.finditer(r"#(tool_[a-zA-Z0-9_]+)\.output#", val):
                    llm_refs.add(m.group(1))
    for tid in tool_node_ids:
        if tid and tid not in llm_refs:
            issues.append(
                f"工具节点 {tid} 的输出未被任何 LLM 节点引用（禁止死分支），"
                "请在至少一个 LLM 节点的输入中使用 {{#" + tid + ".output#}}"
            )

    # 5. 检测非法的 LLM 输出子属性引用
    llm_node_ids = {
        n.get("id") for n in nodes
        if n.get("data", {}).get("type") == "llm" and n.get("id")
    }
    for node in nodes:
        data = node.get("data", {})
        for grp in data.get("group_params", []):
            for p in grp.get("params", []):
                val = p.get("value")
                if not isinstance(val, str):
                    continue
                for m in re.finditer(
                    r"\{\{#(llm_[a-zA-Z0-9_]+)\.output\.(\w+)#\}\}", val
                ):
                    llm_id, field = m.group(1), m.group(2)
                    if llm_id in llm_node_ids:
                        issues.append(
                            f"节点 {node.get('id')} 非法引用了 LLM 子属性 "
                            f"{{{{#{llm_id}.output.{field}#}}}}，"
                            "毕昇不支持直接获取 LLM 输出 JSON 的内部字段。"
                            f"请插入 Code 代码节点解析 {llm_id}.output，"
                            f"然后通过 {{{{#code_xxx.{field}#}}}} 引用"
                        )

    # 6. 检测 Condition 互斥分支汇聚到同一下游节点（会导致流程卡死）
    node_type_map = {
        n.get("id"): n.get("data", {}).get("type", "")
        for n in nodes if n.get("id")
    }
    condition_node_ids = {
        nid for nid, nt in node_type_map.items() if nt == "condition"
    }
    for cond_id in condition_node_ids:
        cond_out_edges = [
            e for e in edges if e.get("source") == cond_id
        ]
        if len(cond_out_edges) < 2:
            continue
        branch_sets: List[set] = []
        for e in cond_out_edges:
            target = e.get("target", "")
            if not target:
                continue
            reachable = _get_branch_reachable(target, edges, node_type_map)
            branch_sets.append(reachable)
        reported: set = set()
        for i in range(len(branch_sets)):
            for j in range(i + 1, len(branch_sets)):
                common = branch_sets[i] & branch_sets[j]
                for nid in common:
                    if nid not in reported:
                        reported.add(nid)
                        issues.append(
                            f"条件节点 {cond_id} 的多个互斥分支汇聚到了同一节点 {nid}，"
                            "条件分支互斥执行，未执行分支不会产生输出，"
                            "汇聚节点会因等待而卡死。"
                            "请让每个分支独立闭环（LLM output_user=true 连回 Input）"
                        )

    # 7. 检测 knowledge_retriever 输出引用错误（用了 retrieved_result 而非 retrieved_output）
    kr_node_ids = {
        n.get("id") for n in nodes
        if n.get("data", {}).get("type") == "knowledge_retriever" and n.get("id")
    }
    for node in nodes:
        data = node.get("data", {})
        for grp in data.get("group_params", []):
            for p in grp.get("params", []):
                val = p.get("value")
                if not isinstance(val, str):
                    if isinstance(val, dict):
                        val = val.get("msg", "")
                    else:
                        continue
                for kr_id in kr_node_ids:
                    if f"{{{{#{kr_id}.retrieved_result#}}}}" in val:
                        issues.append(
                            f"节点 {node.get('id')} 错误引用了 "
                            f"{{{{#{kr_id}.retrieved_result#}}}}，"
                            f"retrieved_result 是输出组名，不是变量名。"
                            f"请改为 {{{{#{kr_id}.retrieved_output#}}}}"
                        )

    # 8. 检测 Code 节点代码是否包含基本容错
    for node in nodes:
        data = node.get("data", {})
        if data.get("type") != "code":
            continue
        nid = node.get("id", "")
        code_value = ""
        has_parse_ok = False
        for grp in data.get("group_params", []):
            for p in grp.get("params", []):
                if p.get("key") == "code" and isinstance(p.get("value"), str):
                    code_value = p["value"]
                if p.get("key") == "code_output":
                    output_keys = [
                        item.get("key", "")
                        for item in (p.get("value") or [])
                        if isinstance(item, dict)
                    ]
                    if "parse_ok" in output_keys:
                        has_parse_ok = True
        if "json.loads" in code_value and "except" not in code_value:
            issues.append(
                f"代码节点 {nid} 使用了 json.loads 但缺少 try-except 容错。"
                "JSON 解析失败时工作流将崩溃，请添加异常处理并返回安全默认值"
            )
        if "json.loads" in code_value and not has_parse_ok:
            issues.append(
                f"代码节点 {nid} 执行 JSON 解析但未输出 parse_ok 决策标志。"
                "请在 code_output 中添加 parse_ok 字段，"
                "供下游 Condition 节点判断解析是否成功"
            )

    return issues


class WorkflowAgent:
    """工作流生成专家（直接加载 SKILL.md + 单次 LLM 调用 + 程序化校验修复）"""

    MAX_FIX_ROUNDS = 2

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
        tools_info = self._format_tools_info(tool_plan)
        knowledge_info = self._format_knowledge_info(knowledge_match)

        user_analysis = (
            f"需求描述：{intent.rewritten_input}\n"
            f"工作流类型：{intent.get_workflow_type()}\n"
            f"复杂度：{intent.complexity_hint}\n"
            f"是否需要工具：{intent.needs_tool}\n"
            f"是否需要知识库：{intent.needs_knowledge}\n"
            f"是否多轮对话：{intent.multi_turn}"
        )

        loader = get_prompt_loader(self._prompts_dir)
        system_tpl = loader.load("workflow/system.md")
        task_prompt = system_tpl.format(
            user_analysis=user_analysis,
            tools_info=tools_info,
            knowledge_info=knowledge_info,
        )

        skill_content = _load_skill_content()
        system_prompt = (
            f"{task_prompt}\n\n"
            f"【毕昇工作流 JSON 规范（SKILL.md）】\n{skill_content}"
        )

        user_msg_tpl = loader.load("workflow/user_message.txt")
        user_message = user_msg_tpl.format(
            intent_rewritten_input=intent.rewritten_input
        )

        logger.info("开始生成工作流（直接 LLM 调用，skill=%d 字符）", len(skill_content))

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        # --- 第一次调用：生成工作流 ---
        content = await self._call_llm(messages)
        if not content:
            return {"error": "工作流生成失败：LLM 未返回有效内容", "content": ""}

        workflow_json = extract_json(content)
        if not workflow_json:
            logger.warning("第一次生成的内容无法提取 JSON")
            return {"error": "工作流生成失败：无法提取 JSON", "content": content}

        workflow_json = self._normalize_workflow(workflow_json, tool_plan)

        # --- 程序化校验 + 修复循环 ---
        for fix_round in range(self.MAX_FIX_ROUNDS):
            issues = _validate_workflow_impl(workflow_json, tool_plan)
            if not issues:
                logger.info("工作流校验通过（第 %d 轮）", fix_round + 1)
                break

            logger.info(
                "工作流校验发现 %d 个问题（第 %d 轮），发起修复调用",
                len(issues), fix_round + 1,
            )
            fix_prompt = (
                "上一版工作流 JSON 存在以下问题，请修复后重新输出完整的 JSON：\n\n"
                + "\n".join(f"- {i}" for i in issues)
                + "\n\n请输出修复后的完整工作流 JSON（```json 代码块）。"
            )

            messages.append(AIMessage(content=content))
            messages.append(HumanMessage(content=fix_prompt))

            content = await self._call_llm(messages)
            if not content:
                logger.warning("修复调用未返回有效内容，使用上一版本")
                break

            fixed_json = extract_json(content)
            if not fixed_json:
                logger.warning("修复调用返回内容无法提取 JSON，使用上一版本")
                break

            workflow_json = self._normalize_workflow(fixed_json, tool_plan)

        logger.info(
            "工作流生成完成，nodes=%d",
            len(workflow_json.get("nodes", [])),
        )
        return workflow_json

    async def _call_llm(self, messages: list) -> str:
        """调用 LLM 并返回文本内容。"""
        try:
            result = await self.llm.ainvoke(
                messages,
                config=RunnableConfig(callbacks=[self._usage_callback]),
            )
        except Exception as e:
            logger.exception("LLM 调用异常: %s", e)
            return ""

        self._log_usage()

        content = getattr(result, "content", None)
        if isinstance(content, str) and content.strip():
            return content
        return ""

    def _log_usage(self) -> None:
        model_key = getattr(self.llm, "model_name", None) or getattr(
            self.llm, "model", None
        )
        if not model_key:
            return
        usage = self._usage_callback.usage_metadata.get(model_key)
        if usage:
            logger.info(
                "LLM tokens: in=%s out=%s total=%s",
                usage.get("input_tokens"),
                usage.get("output_tokens"),
                usage.get("total_tokens"),
            )

    # ─── 后处理：规范化 ───────────────────────────────────────────

    def _normalize_workflow(
        self, w: Dict[str, Any], tool_plan: Optional[ToolPlan] = None
    ) -> Dict[str, Any]:
        """
        规范化工作流 JSON，补全毕昇前端必需的字段，避免导入时报错。
        """
        from datetime import datetime

        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

        self._normalize_top_level(w, now)

        for node in w.get("nodes", []):
            self._normalize_node(node)

        self._normalize_edges(w)

        if "viewport" not in w or not isinstance(w["viewport"], dict):
            w["viewport"] = {"x": 0, "y": 0, "zoom": 1}
        vp = w["viewport"]
        vp.setdefault("x", 0)
        vp.setdefault("y", 0)
        vp.setdefault("zoom", 1)

        if tool_plan:
            self._fix_tool_keys(w, tool_plan)

        return w

    def _normalize_top_level(self, w: Dict[str, Any], now: str) -> None:
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
        node_id = node.get("id", "")
        data = node.setdefault("data", {})
        node_type = data.get("type")

        data.setdefault("id", node_id)
        data.setdefault("description", "")
        node.setdefault("type", "flowNode")
        node.setdefault("position", {"x": 0, "y": 0})
        node.setdefault("measured", {"width": 334, "height": 500})

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

            if (
                node_type == "knowledge_retriever"
                and grp.get("name") == "知识库检索设置"
            ):
                self._ensure_knowledge_retriever_params(params)

            if node_type == "llm" and grp.get("name") == "模型设置":
                self._ensure_llm_model_params(params)

        if node_type == "code":
            self._normalize_code_node(data)

    def _ensure_param_value(self, p: Dict[str, Any]) -> None:
        pt = p.get("type", "")
        if "value" not in p or p["value"] is None:
            pass
        else:
            v = p["value"]
            if pt == "output_form" and isinstance(v, dict):
                v.setdefault("type", "")
                v.setdefault("value", "")
            elif pt == "var_textarea_file" and isinstance(v, dict):
                v.setdefault("msg", "")
                v.setdefault("files", [])
            elif pt == "var_textarea":
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
            if "value" not in p:
                p["value"] = []
        else:
            p["value"] = "" if pt not in ("input_list", "user_question") else []

    def _ensure_knowledge_retriever_params(self, params: List[Dict[str, Any]]) -> None:
        keys = [x.get("key") for x in params]
        if "metadata_filter" not in keys:
            params.append({
                "key": "metadata_filter",
                "type": "metadata_filter",
                "label": "true",
                "value": {"enabled": False},
            })
        if "advanced_retrieval_switch" not in keys:
            params.append({
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
            })

    def _ensure_llm_model_params(self, params: List[Dict[str, Any]]) -> None:
        keys = [x.get("key") for x in params]
        if "temperature" not in keys:
            params.append({
                "key": "temperature",
                "step": 0.1,
                "type": "slide",
                "label": "true",
                "scope": [0, 2],
                "value": 0.3,
            })

    def _normalize_code_node(self, data: Dict[str, Any]) -> None:
        data.setdefault("expand", True)
        if data.get("v") is None:
            data["v"] = "1"

        grps = data.get("group_params", [])
        grp_names = [g.get("name", "") for g in grps]

        if "入参" not in grp_names:
            grps.insert(0, {
                "name": "入参",
                "params": [{
                    "key": "code_input",
                    "test": "input",
                    "type": "code_input",
                    "value": [],
                    "required": True,
                }],
            })
        if "执行代码" not in grp_names:
            grps.append({
                "name": "执行代码",
                "params": [{
                    "key": "code",
                    "type": "code",
                    "value": "def main() -> dict:\n    return {}",
                    "required": True,
                }],
            })
        if "出参" not in grp_names:
            grps.append({
                "name": "出参",
                "params": [{
                    "key": "code_output",
                    "type": "code_output",
                    "value": [],
                    "global": "code:value.map(el => ({ label: el.key, value: el.key }))",
                    "required": True,
                }],
            })

        for grp in grps:
            for p in grp.get("params", []):
                if p.get("key") == "code_output" and "global" not in p:
                    p["global"] = (
                        "code:value.map(el => ({ label: el.key, value: el.key }))"
                    )

    def _normalize_edges(self, w: Dict[str, Any]) -> None:
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
        if not tool_plan.selected_tools:
            return

        valid_keys = {t.tool_key for t in tool_plan.selected_tools}

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
                    current_key, fixed_key, node.get("id"),
                )
                data["tool_key"] = fixed_key

    # ─── 格式化辅助 ──────────────────────────────────────────────

    def _format_tools_info(self, tool_plan: ToolPlan) -> str:
        if not tool_plan.selected_tools:
            return "无工具调用需求"

        lines = [
            "⚠️ 重要：以下每个工具的 tool_key 必须原样写入生成的 JSON，"
            "禁止省略、修改或截断任何部分（MCP 工具的 _数字ID 后缀不可删除）：",
        ]
        for t in tool_plan.selected_tools:
            tool_type = "MCP工具" if self._is_mcp_tool(t) else "内置工具"
            lines.append(f'- [{tool_type}] tool_key: "{t.tool_key}"（必须完全一致）')
            lines.append(f"  名称：{t.name}")
            lines.append(f"  描述：{t.desc}")
            if t.parameters:
                params_info = []
                for p in t.parameters:
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
        if tool.extra:
            ct = tool.extra.get("connection_type", "")
            if ct and ct != "builtin":
                return True
        return bool(re.search(r"_\d{4,}$", tool.tool_key))

    def _format_knowledge_info(self, knowledge_match: KnowledgeMatch) -> str:
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
