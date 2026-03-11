"""
工作流生成 Agent

标准 agent-skills 模式：
- SkillRegistry + LocalFileSystemSkillProvider 注册 bisheng-workflow-generator 技能
- create_agent 创建带工具循环的 agent（skill 工具 + validate_workflow 自定义工具）
- Agent 按需读取 SKILL.md / 参考文档 / 示例（渐进式加载，避免系统提示过长）
- 最终程序化校验 + 规范化作为安全兜底
"""

from datetime import timezone
import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain.agents import create_agent
from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.memory import InMemorySaver

from agentskills_core import SkillRegistry
from agentskills_fs import LocalFileSystemSkillProvider
from agentskills_langchain import get_tools, get_tools_usage_instructions

from agents.knowledge_agent import KnowledgeMatch
from agents.tool_agent import ToolPlan
from core.prompt_loader import get_prompt_loader
from core.utils import extract_json
from models.intent import EnhancedIntent

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SKILLS_DIR = _REPO_ROOT / "skills"
# 每轮工作流 JSON 调试输出目录（按本次请求 thread_id 分子目录）
_WORKFLOW_DEBUG_DIR = Path(__file__).resolve().parent.parent / "data" / "workflow_debug"

# 工具节点中表示「用户输入/查询条件/地域/时间/关键词」等的参数 key，不应写死为具体值
_USER_VARIABLE_TOOL_PARAM_KEYS = frozenset(
    {
        "province",
        "city",
        "district",
        "region",
        "date",
        "start_date",
        "end_date",
        "keyword",
        "query",
        "search_keyword",
        "company_status",
        "location",
        "status",
        "name",
        "q",
        "search",
        "location_name",
    }
)


# ─── 程序化校验辅助 ─────────────────────────────────────────────


def _collect_strings_from_value(val: Any) -> List[str]:
    """从可能嵌套的 value（str/dict/list）中收集所有字符串，用于正则扫描变量引用。"""
    if isinstance(val, str):
        return [val]
    if isinstance(val, dict):
        return [s for v in val.values() for s in _collect_strings_from_value(v)]
    if isinstance(val, list):
        return [s for item in val for s in _collect_strings_from_value(item)]
    return []


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


class WorkflowValidator:
    """
    毕升工作流图形与执行引擎双端规则验证器。
    该类将图形拓扑的校验从原本复杂的大函数中抽取出来，按职责分散为独立的私有方法，
    以便维护前端图形画布限定与后端执行引擎特征。
    """

    def __init__(
        self,
        workflow: Dict[str, Any],
        tool_plan: Optional[ToolPlan] = None,
        knowledge_match: Optional[KnowledgeMatch] = None,
    ):
        self.workflow = workflow
        self.tool_plan = tool_plan
        self.knowledge_match = knowledge_match
        self.issues: List[str] = []

        self.nodes = self.workflow.get("nodes") or []
        self.edges = self.workflow.get("edges") or []
        self.node_ids = {n.get("id") for n in self.nodes if n.get("id")}

        # 建立边映射，查出边和入边，避免高时间复杂度计算
        self.edges_from = {nid: [] for nid in self.node_ids}
        self.edges_to = {nid: [] for nid in self.node_ids}
        for e in self.edges:
            src, tgt = e.get("source"), e.get("target")
            if src in self.edges_from:
                self.edges_from[src].append(e)
            if tgt in self.edges_to:
                self.edges_to[tgt].append(e)

        # 缓存节点 ID 和类型的速查字典
        self.node_type_map = {
            n.get("id"): n.get("data", {}).get("type", "")
            for n in self.nodes
            if n.get("id")
        }

    def validate(self) -> List[str]:
        """运行所有验证规则，收集全部的缺陷并返回。空列表代表无缺陷。"""
        self.issues.clear()

        self._check_graph_integrity()
        self._check_tool_nodes()
        self._check_no_knowledge_when_empty()
        self._check_llm_nodes()
        self._check_condition_branches()
        self._check_knowledge_retriever()
        self._check_code_nodes()
        self._check_frontend_strict_rules()

        return self.issues

    def _check_graph_integrity(self):
        """规则 1 & 2: 校验图的基础节点合法性和边引用"""
        # 1. edges 引用的 node 必须存在
        for e in self.edges:
            src, tgt = e.get("source"), e.get("target")
            if src and src not in self.node_ids:
                self.issues.append(f"边引用了不存在的节点 source: {src}")
            if tgt and tgt not in self.node_ids:
                self.issues.append(f"边引用了不存在的节点 target: {tgt}")

        # 2. 基础节点类型校验
        types_seen = set(self.node_type_map.values())
        for required in ("start", "input"):
            if required not in types_seen:
                self.issues.append(f"缺少必需节点类型: {required}")

        has_output_user = any(
            p.get("key") == "output_user" and p.get("value") is True
            for n in self.nodes
            if n.get("data", {}).get("type") == "llm"
            for grp in n.get("data", {}).get("group_params", [])
            for p in grp.get("params", [])
        )
        if "output" not in types_seen and not has_output_user:
            self.issues.append("缺少 output 节点且没有 LLM 设置 output_user=true")

    def _check_tool_nodes(self):
        """规则 3, 4 & 9: 校验工具节点的限定、硬编码检查与死分支排查"""
        valid_tool_keys: set = set()
        if self.tool_plan and self.tool_plan.selected_tools:
            valid_tool_keys = {t.tool_key for t in self.tool_plan.selected_tools}

        tool_node_ids = [
            n.get("id", "")
            for n in self.nodes
            if n.get("data", {}).get("type") == "tool"
        ]
        # 无候选工具时不得包含任何 tool 节点（禁止编造工具）
        if not valid_tool_keys and tool_node_ids:
            self.issues.append(
                "无候选工具时不得包含任何 tool 节点（禁止编造工具）。"
                "请移除所有 type 为 tool 的节点，改为纯 LLM 流程（若需求涉及外部能力，请描述为「当前无可用工具，仅用 LLM 回答」）。"
            )
            return

        for node in self.nodes:
            data = node.get("data", {})
            if data.get("type") != "tool":
                continue
            nid = node.get("id", "")
            tk = data.get("tool_key", "")
            if valid_tool_keys and tk and tk not in valid_tool_keys:
                self.issues.append(
                    f"工具节点 {nid} 的 tool_key '{tk}' 不在候选列表中，"
                    "必须与候选工具的 tool_key 完全一致（含 MCP 后缀）"
                )

            # 检测工具节点中用户类参数是否被写死
            for grp in data.get("group_params", []):
                if grp.get("name") != "工具参数":
                    continue
                for p in grp.get("params", []):
                    key = p.get("key", "")
                    if key not in _USER_VARIABLE_TOOL_PARAM_KEYS:
                        continue
                    val = p.get("value")
                    if not isinstance(val, str) or not val.strip():
                        continue
                    if "{{#" in val:
                        continue
                    self.issues.append(
                        f"工具节点 {nid} 的参数 '{key}' 不应写死为具体值 \"{val[:30]}{'...' if len(val) > 30 else ''}\"，"
                        "此类参数应留空或绑定到输入/上游变量（如 {{#input_xxx.user_input#}}、{{#code_xxx.字段#}}）"
                    )

        # 每个 tool 节点的输出必须被至少一个下游节点引用（LLM、Code 等均可）
        # 匹配任意节点 id 的 .output 引用（不限定 tool_ 前缀），与图中实际 tool 节点 id 一致即可
        tool_node_id_set = set(tool_node_ids)
        tool_output_refs = set()
        for node in self.nodes:
            for grp in node.get("data", {}).get("group_params", []):
                for p in grp.get("params", []):
                    val = p.get("value")
                    for s in _collect_strings_from_value(val):
                        for m in re.finditer(r"#([a-zA-Z0-9_]+)\.output#", s):
                            ref_id = m.group(1)
                            if ref_id in tool_node_id_set:
                                tool_output_refs.add(ref_id)
        for tid in tool_node_ids:
            if tid and tid not in tool_output_refs:
                node_name = ""
                for n in self.nodes:
                    if n.get("id") == tid:
                        node_name = n.get("data", {}).get("name", "") or ""
                        break
                name_part = f"（名称：{node_name}）" if node_name else ""
                self.issues.append(
                    f"工具节点 {tid}{name_part} 的输出未被任何下游节点引用（禁止死分支）。"
                    f"请在至少一个下游节点（如 LLM、Code）的输入中使用 {{{{#{tid}.output#}}}}。"
                )

    def _check_no_knowledge_when_empty(self):
        """无匹配知识库时不得包含任何 knowledge_retriever 节点（禁止编造知识库）"""
        if self.knowledge_match is None:
            return
        if self.knowledge_match.matched_knowledge_bases:
            return
        kr_ids = [
            nid for nid, nt in self.node_type_map.items() if nt == "knowledge_retriever"
        ]
        if not kr_ids:
            return
        self.issues.append(
            "无匹配知识库时不得包含任何 knowledge_retriever 节点（禁止编造知识库）。"
            "请移除所有知识库检索节点，改为纯 LLM/工具 流程。"
        )

    def _check_llm_nodes(self):
        """规则 5: 检测非法的大模型输出子属性引用 {{#llm_x.output.y#}}"""
        llm_node_ids = {nid for nid, nt in self.node_type_map.items() if nt == "llm"}

        for node in self.nodes:
            for grp in node.get("data", {}).get("group_params", []):
                for p in grp.get("params", []):
                    val = p.get("value")
                    if not isinstance(val, str):
                        continue
                    for m in re.finditer(
                        r"\{\{#(llm_[a-zA-Z0-9_]+)\.output\.(\w+)#\}\}", val
                    ):
                        llm_id, field = m.group(1), m.group(2)
                        if llm_id in llm_node_ids:
                            self.issues.append(
                                f"节点 {node.get('id')} 非法引用了 LLM 子属性 "
                                f"{{{{#{llm_id}.output.{field}#}}}}，"
                                "毕昇不支持直接获取 LLM 输出 JSON 的内部字段。"
                                f"请插入 Code 代码节点解析 {llm_id}.output，"
                                f"然后通过 {{{{#code_xxx.{field}#}}}} 引用"
                            )

    def _check_condition_branches(self):
        """规则 6: 检测 Condition 互斥分支汇聚，防止后端图执行引擎死等卡死"""
        condition_node_ids = {
            nid for nid, nt in self.node_type_map.items() if nt == "condition"
        }

        for cond_id in condition_node_ids:
            cond_out_edges = self.edges_from.get(cond_id, [])
            if len(cond_out_edges) < 2:
                continue

            branch_sets: List[set] = []
            for e in cond_out_edges:
                target = e.get("target", "")
                if not target:
                    continue
                reachable = _get_branch_reachable(
                    target, self.edges, self.node_type_map
                )
                branch_sets.append(reachable)

            reported: set = set()
            for i in range(len(branch_sets)):
                for j in range(i + 1, len(branch_sets)):
                    common = branch_sets[i] & branch_sets[j]
                    for nid in common:
                        if nid not in reported:
                            reported.add(nid)
                            self.issues.append(
                                f"条件节点 {cond_id} 的多个互斥分支汇聚到了同一节点 {nid}，"
                                "条件分支互斥执行，未执行分支不会产生输出，"
                                "汇聚节点会因等待而卡死。"
                                "请让每个分支独立闭环（LLM output_user=true 连回 Input）"
                            )

    def _check_knowledge_retriever(self):
        """规则 7: 检测 knowledge_retriever 输出引用变量名拼写错误"""
        kr_node_ids = {
            nid for nid, nt in self.node_type_map.items() if nt == "knowledge_retriever"
        }

        for node in self.nodes:
            for grp in node.get("data", {}).get("group_params", []):
                for p in grp.get("params", []):
                    val = p.get("value")
                    if not isinstance(val, str):
                        if isinstance(val, dict):
                            val = val.get("msg", "")
                        else:
                            continue

                    for kr_id in kr_node_ids:
                        if f"{{{{#{kr_id}.retrieved_result#}}}}" in val:
                            self.issues.append(
                                f"节点 {node.get('id')} 错误引用了 "
                                f"{{{{#{kr_id}.retrieved_result#}}}}，"
                                f"retrieved_result 是输出组名，不是变量名。"
                                f"请改为 {{{{#{kr_id}.retrieved_output#}}}}"
                            )

    def _check_code_nodes(self):
        """规则 8: 检测 Code 节点 json 序列化的基本容错"""
        for node in self.nodes:
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
                self.issues.append(
                    f"代码节点 {nid} 使用了 json.loads 但缺少 try-except 容错。"
                    "JSON 解析失败时工作流将崩溃，请添加异常处理并返回安全默认值"
                )
            if "json.loads" in code_value and not has_parse_ok:
                self.issues.append(
                    f"代码节点 {nid} 执行 JSON 解析但未输出 parse_ok 决策标志。"
                    "请在 code_output 中添加 parse_ok 字段，"
                    "供下游 Condition 节点判断解析是否成功"
                )

    def _check_frontend_strict_rules(self):
        """
        对齐前端 Header.tsx 中 traverseTree 的遍历逻辑：
        - 从 start 节点出发 DFS
        - 遇到 end 节点 → 该分支合法结束
        - 遇到已访问过的节点（回环，如 LLM→Input 多轮对话）→ 该分支合法结束
        - 遇到没有出边的非 end 节点 → 断头路，报 missingEndNode 错误
        - 所有 flowNode 类型的节点必须从 start 可达，否则报 unconnectedNodes
        - Condition 节点所有触点（含 right_handle）必须有出边
        """

        # ── 1. 从 start 出发做 DFS，模拟 traverseTree ──
        start_node_id = None
        for nid, nt in self.node_type_map.items():
            if nt == "start":
                start_node_id = nid
                break

        if not start_node_id:
            return  # _check_graph_integrity 已经会报缺少 start

        # 找到 start 的第一条出边的 target 作为遍历起点（与前端一致）
        start_edges = self.edges_from.get(start_node_id, [])
        if not start_edges:
            self.issues.append(
                "开始节点(start)没有连接任何下游节点，前端会报「缺少结束节点」。请连接 start → input。"
            )
            return

        visited: set = set()  # 已经访问过的节点
        reachable: set = set()  # 从 start 可达的全部节点
        dead_ends: List[str] = []  # 断头路节点

        def dfs(node_id: str):
            """DFS 遍历，模拟前端 traverseTree 的终止判定"""
            if node_id in visited:
                return  # 回环 → 合法终止
            visited.add(node_id)
            reachable.add(node_id)

            ntype = self.node_type_map.get(node_id, "")
            if ntype == "end":
                return  # end 节点 → 合法终止

            out_edges = self.edges_from.get(node_id, [])
            if not out_edges:
                # 没有出边且不是 end → 断头路
                dead_ends.append(node_id)
                return

            for e in out_edges:
                target = e.get("target", "")
                if target:
                    dfs(target)

        # 从 start 节点开始遍历
        dfs(start_node_id)

        # ── 2. 断头路报错（对齐前端 missingEndNode）──
        for nid in dead_ends:
            ntype = self.node_type_map.get(nid, "")
            self.issues.append(
                f"节点 '{nid}'(类型: {ntype}) 是断头路（没有出边且不形成回环）。"
                "默认多轮对话模式要求每条分支必须回环到 Input 节点形成对话闭环。"
                "请让该节点通过 LLM(output_user=true) 连回 Input 节点。"
            )

        # ── 3. 孤立节点报错（对齐前端 unconnectedNodes）──
        all_flow_node_ids = {
            nid
            for nid, nt in self.node_type_map.items()
            if nt not in ("",)  # 排除无效节点
        }
        unreachable = all_flow_node_ids - reachable
        if unreachable:
            self.issues.append(
                f"以下节点无法从 start 节点到达（孤立飞地）：{', '.join(sorted(unreachable))}。"
                "前端要求所有节点必须可从 start 遍历到达，请补充连线或删除多余节点。"
            )

        # ── 4. Condition 触点全连校验（独立于 DFS，前端单独校验）──
        for node in self.nodes:
            data = node.get("data", {})
            if data.get("type") != "condition":
                continue
            nid = node.get("id", "")
            required_handles = ["right_handle"]  # 右侧兜底触点必须有连线

            for grp in data.get("group_params", []):
                if grp.get("name") == "条件分支":
                    for p in grp.get("params", []):
                        if p.get("key") == "condition":
                            cond_items = p.get("value") or []
                            for item in cond_items:
                                required_handles.append(item.get("id"))

            for handle in required_handles:
                has_edge = any(
                    e.get("source") == nid and e.get("sourceHandle") == handle
                    for e in self.edges
                )
                if not has_edge:
                    self.issues.append(
                        f"条件节点 '{nid}' 的触点 '{handle}' 没有连接下游节点。"
                        f"（前端强制校验：即使该条件分支什么都不做，也必须通过 LLM(output_user=true) 回环连回 Input 节点，不允许挂空）"
                    )


# ─── Agent 类 ──────────────────────────────────────────────────


class WorkflowAgent:
    """工作流生成专家（标准 agent-skills + validate_workflow 工具 + 程序化校验兜底）"""

    MAX_FIX_ROUNDS = 2

    # 多草图模式下的固定维度配置：id / 标题 / 提示词说明
    FLOW_SKETCH_DIMENSIONS: List[Dict[str, str]] = [
        {
            "id": "simple_exec_first",
            "title": "方案A：上线可执行优先",
            "goal_hint": (
                "在满足所有平台约束的前提下，优先保证「容易在毕昇平台直接上线、实现成本最低」。"
                "流程应尽量简单、节点数量少、分支不宜过多，避免不必要的 condition 和 code 节点，"
                "只保留完成需求所必需的知识库检索和工具调用链路，同时保留基础的多轮对话闭环。"
            ),
        },
        {
            "id": "robust_high_accuracy",
            "title": "方案B：准确性与鲁棒性优先",
            "goal_hint": (
                "在满足所有平台约束的前提下，优先保证「检索准确性和结果鲁棒性更高」。"
                "可以适当增加知识库检索 + LLM 解读/重写的链路，引入必要的 code 节点做 JSON 解析与异常兜底，"
                "在关键节点前后允许使用少量 condition 节点区分有结果/无结果/低置信度等分支，以提高整体回答质量。"
            ),
        },
        {
            "id": "extensible_future_proof",
            "title": "方案C：可扩展与可演进优先",
            "goal_hint": (
                "在满足所有平台约束的前提下，优先保证「结构清晰、便于未来扩展与演进」。"
                "使用 condition 对不同业务场景进行清晰拆分，每个分支内部预留 1–2 个通用的 LLM 或 code 汇总节点，"
                "方便后续插入监控、AB 实验或更多工具/知识库调用，同时避免过深的链路嵌套。"
            ),
        },
    ]

    def __init__(
        self,
        llm: BaseChatModel,
        prompts_dir: Optional[str] = None,
    ):
        self.llm = llm
        self._prompts_dir = prompts_dir
        self._registry: Optional[SkillRegistry] = None
        self._skill_tools: list = []
        self._catalog: str = ""
        self._instructions: str = ""

    async def _ensure_initialized(self) -> None:
        """懒初始化：注册 skill、生成工具、获取 catalog（仅首次调用）"""
        if self._registry is not None:
            return

        self._registry = SkillRegistry()
        provider = LocalFileSystemSkillProvider(_SKILLS_DIR)
        await self._registry.register("bisheng-workflow-generator", provider)

        self._skill_tools = get_tools(self._registry)
        self._catalog = await self._registry.get_skills_catalog(format="xml")
        self._instructions = get_tools_usage_instructions()

        logger.info(
            "agent-skills 初始化完成: tools=%s, catalog_len=%d",
            [t.name for t in self._skill_tools],
            len(self._catalog),
        )

    async def generate_workflow(
        self,
        intent: EnhancedIntent,
        tool_plan: ToolPlan,
        knowledge_match: KnowledgeMatch,
        flow_sketch: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        await self._ensure_initialized()

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
        system_tpl = loader.get("workflow", "system")
        task_prompt = system_tpl.format(
            user_analysis=user_analysis,
            tools_info=tools_info,
            knowledge_info=knowledge_info,
        )
        if flow_sketch and isinstance(flow_sketch.get("nodes"), list):
            import json as _json

            sketch_json = _json.dumps(flow_sketch, ensure_ascii=False, indent=2)
            task_prompt = (
                task_prompt + "\n\n【参考流程图草图】\n"
                "以下为已确定的流程图结构（nodes 与 edges），请以此作为完整毕昇工作流 JSON 的「主干结构」：\n"
                "- start / input / condition / llm / tool / knowledge_retriever 的分支走向应与草图保持一致（不要改变主要分支的语义和方向）；\n"
                "- 你可以在节点之间插入必要的 code 节点或校验节点，也可以将单个 llm 步骤拆分为多个更细的 llm 步骤；\n"
                "- 只要不改变草图中已有分支的大致路径，可以根据需要补充少量辅助节点，以提升可执行性和鲁棒性。\n\n"
                f"{sketch_json}\n"
            )

        system_prompt = (
            f"{task_prompt}\n\n" f"{self._catalog}\n\n" f"{self._instructions}"
        )

        # 仅使用 skill 工具（get_skill_body、get_skill_reference 等）；校验在生成后由程序化 _validate_workflow_impl + 修复轮完成，避免 agent 在对话中反复调用校验工具导致变慢
        all_tools = list(self._skill_tools)

        checkpointer = InMemorySaver()
        agent = create_agent(
            model=self.llm,
            tools=all_tools,
            system_prompt=system_prompt,
            checkpointer=checkpointer,
        )

        user_msg_tpl = loader.get("workflow", "user_message")
        user_message = user_msg_tpl.format(
            intent_rewritten_input=intent.rewritten_input
        )

        thread_id = uuid.uuid4().hex
        debug_dir = _WORKFLOW_DEBUG_DIR / thread_id
        usage_cb = UsageMetadataCallbackHandler()
        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": [usage_cb],
        }

        logger.info("开始生成工作流（agent-skills 模式，tools=%d）", len(all_tools))

        # ── 第一轮：用 astream_events 便于记录中间过程（skill/工具调用），并从同一流中取最终结果 ──
        final_content = None
        async for event in agent.astream_events(
            {"messages": [{"role": "user", "content": user_message}]},
            config=config,
            version="v2",
        ):
            kind = event.get("event")
            # 中间过程：工具/Skill 调用开始（如 get_skill_body、get_skill_reference、validate_workflow）
            if kind == "on_tool_start":
                data = event.get("data", {})
                tool_name = event.get("name", "")
                tool_input = data.get("input", data)
                logger.info(
                    "[workflow_agent] Skill/工具开始 name=%s input=%s",
                    tool_name,
                    str(tool_input)[:200]
                    + ("..." if len(str(tool_input)) > 200 else ""),
                )
            # 中间过程：工具/Skill 调用结束
            elif kind == "on_tool_end":
                out = event.get("data", {}).get("output", "")
                logger.info(
                    "[workflow_agent] Skill/工具结束 name=%s output_len=%d preview=%s",
                    event.get("name", ""),
                    len(str(out)),
                    str(out)[:150] + ("..." if len(str(out)) > 150 else ""),
                )
            # 最终结果：根 agent 结束时，output 为最终 state（含 messages）
            elif kind == "on_chain_end":
                if event.get("parent_ids") == []:
                    output = event.get("data", {}).get("output")
                    if output and isinstance(output, dict) and "messages" in output:
                        messages = output["messages"]
                        if messages:
                            last_msg = messages[-1]
                            if hasattr(last_msg, "content") and last_msg.content:
                                final_content = last_msg.content
                                break
        self._log_usage(usage_cb)

        content = final_content or ""
        workflow_json = extract_json(content)

        if not workflow_json:
            logger.warning("Agent 输出无法提取 JSON")
            return {"error": "工作流生成失败：无法提取 JSON", "content": content}

        workflow_json = self._normalize_workflow(workflow_json, tool_plan)
        self._write_debug_round(debug_dir, "round_1", workflow_json)

        # ── 安全兜底：程序化校验 + 修复循环 ──
        for fix_round in range(self.MAX_FIX_ROUNDS):
            try:
                validator = WorkflowValidator(workflow_json, tool_plan, knowledge_match)
                issues = validator.validate()
            except Exception as e:
                logger.warning("Agent 校验时发生错误：%s", e)
                issues = [f"JSON 结构异常导致校验抛出系统错误：{e}"]

            if not issues:
                logger.info("最终校验通过（第 %d 轮）", fix_round + 1)
                break

            logger.info(
                "最终校验发现 %d 个问题（第 %d 轮），通过 agent 修复",
                len(issues),
                fix_round + 1,
            )
            for idx, issue in enumerate(issues, 1):
                logger.info("  校验问题 %d: %s", idx, issue)
            fix_prompt = (
                "上一版工作流 JSON 存在以下问题，请修复后重新输出完整的 JSON：\n\n"
                + "\n".join(f"- {i}" for i in issues)
                + "\n\n请输出修复后的完整工作流 JSON（```json 代码块）。"
            )
            # 若有「工具节点输出未被引用」类问题，追加正确写法提示，便于一次改对
            if any("的输出未被任何下游节点引用" in i for i in issues):
                fix_prompt += (
                    "\n\n【正确写法】请在某个下游节点（如 LLM 或 Code）的 group_params 中，"
                    "在提示词/输入类参数的 value 里加入对应工具节点的引用，例如 {{#工具节点ID.output#}}，"
                    "且工具节点 ID 须与 nodes 中该工具节点的 id 完全一致。"
                )

            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": fix_prompt}]},
                config=config,
            )
            self._log_usage(usage_cb)

            content = result["messages"][-1].content
            fixed_json = extract_json(content)
            if not fixed_json:
                logger.warning("修复调用返回内容无法提取 JSON，使用上一版本")
                break

            workflow_json = self._normalize_workflow(fixed_json, tool_plan)
            self._write_debug_round(debug_dir, f"round_{fix_round + 2}", workflow_json)

        self._write_debug_round(debug_dir, "final", workflow_json)
        logger.info(
            "工作流生成完成，nodes=%d",
            len(workflow_json.get("nodes", [])),
        )
        return workflow_json

    # ─── 使用量日志 ─────────────────────────────────────────────

    def _log_usage(self, cb: UsageMetadataCallbackHandler) -> None:
        model_key = getattr(self.llm, "model_name", None) or getattr(
            self.llm, "model", None
        )
        if not model_key:
            return
        usage = cb.usage_metadata.get(model_key)
        if usage:
            logger.info(
                "LLM tokens: in=%s out=%s total=%s",
                usage.get("input_tokens"),
                usage.get("output_tokens"),
                usage.get("total_tokens"),
            )

    # ─── 流程图草图简化 ─────────────────────────────────────────

    def _simplify_flow_sketch(
        self, sketch: Dict[str, Any], max_nodes: int = 12
    ) -> Dict[str, Any]:
        """
        当前版本不对草图结构做任何修改，仅作为占位，后续若需要可以只用于前端展示层面的简化。
        为避免影响完整工作流生成，原始 nodes / edges 结构会原样返回。
        """
        return sketch

    # ─── 流程图草图（先于完整工作流生成）─────────────────────────

    async def _generate_flow_sketch_once(
        self,
        intent: EnhancedIntent,
        tool_plan: ToolPlan,
        knowledge_match: KnowledgeMatch,
        goal_hint: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        生成单个流程图草图（仅 nodes + edges）。
        goal_hint 用于引导本轮草图的取舍方向（可执行优先 / 准确率优先等）。
        """
        tools_info = self._format_tools_info(tool_plan)
        knowledge_info = self._format_knowledge_info(knowledge_match)
        user_analysis = (
            f"需求描述：{intent.rewritten_input}\n"
            f"工作流类型：{intent.get_workflow_type()}\n"
            f"是否需要工具：{intent.needs_tool}\n"
            f"是否需要知识库：{intent.needs_knowledge}\n"
        )
        loader = get_prompt_loader(self._prompts_dir)
        system_tpl = loader.get("flow_sketch", "system")
        user_tpl = loader.get("flow_sketch", "user_message")
        if not system_tpl or not user_tpl:
            logger.warning("flow_sketch 提示词未配置，跳过草图")
            return None

        # 在系统提示中追加本轮草图的目标说明，保持对现有提示词的兼容
        if goal_hint:
            user_analysis = user_analysis + f"\n【本轮草图目标】{goal_hint}"

        system_prompt = system_tpl.format(
            user_analysis=user_analysis,
            tools_info=tools_info,
            knowledge_info=knowledge_info,
        )
        user_message = user_tpl.format(
            intent_rewritten_input=intent.rewritten_input or intent.original_input
        )
        try:
            from langchain_core.messages import SystemMessage, HumanMessage

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message),
            ]
            response = await self.llm.ainvoke(messages)
            content = (
                response.content if hasattr(response, "content") else str(response)
            )
            sketch = extract_json(content)
            if not sketch or not isinstance(sketch, dict):
                logger.warning("流程图草图解析失败：未得到有效 JSON")
                return None
            nodes = sketch.get("nodes")
            edges = sketch.get("edges")
            if not isinstance(nodes, list) or not isinstance(edges, list):
                logger.warning("流程图草图格式错误：缺少 nodes 或 edges 数组")
                return None
            logger.info(
                "流程图草图生成完成，nodes=%d, edges=%d (goal=%s)",
                len(nodes),
                len(edges),
                goal_hint or "",
            )
            raw = {"nodes": nodes, "edges": edges}
            simplified = self._simplify_flow_sketch(raw, max_nodes=12)
            return simplified
        except Exception as e:
            logger.warning("流程图草图生成异常：%s，将无草图继续生成", e)
            return None

    async def generate_flow_sketch(
        self,
        intent: EnhancedIntent,
        tool_plan: ToolPlan,
        knowledge_match: KnowledgeMatch,
    ) -> Optional[Dict[str, Any]]:
        """
        根据需求与候选工具/知识库生成单个流程图草图（仅 nodes + edges）。
        向后兼容旧逻辑：不指定维度，使用默认取舍。
        """
        return await self._generate_flow_sketch_once(
            intent=intent,
            tool_plan=tool_plan,
            knowledge_match=knowledge_match,
            goal_hint=None,
        )

    async def generate_flow_sketch_variants(
        self,
        intent: EnhancedIntent,
        tool_plan: ToolPlan,
        knowledge_match: KnowledgeMatch,
    ) -> List[Dict[str, Any]]:
        """
        按不同取舍维度生成多份流程图草图备选项，供前端交互选择。

        返回的每个元素结构：
        {
            "id": 维度ID（如 simple_exec_first）,
            "title": 展示用标题,
            "description": 维度说明,
            "sketch": {"nodes": [...], "edges": [...]}
        }
        """
        variants: List[Dict[str, Any]] = []
        for dim in self.FLOW_SKETCH_DIMENSIONS:
            dim_id = dim.get("id") or ""
            goal_hint = dim.get("goal_hint") or ""
            title = dim.get("title") or dim_id
            sketch = await self._generate_flow_sketch_once(
                intent=intent,
                tool_plan=tool_plan,
                knowledge_match=knowledge_match,
                goal_hint=goal_hint or None,
            )
            if not sketch:
                continue
            variants.append(
                {
                    "id": dim_id,
                    "title": title,
                    "description": goal_hint,
                    "sketch": sketch,
                }
            )

        # 若全部失败，则返回空列表，由上游回退到单草图逻辑
        return variants

    def _write_debug_round(
        self, debug_dir: Path, round_name: str, workflow_json: Dict[str, Any]
    ) -> None:
        """将当前轮的工作流 JSON 写入调试目录，便于按请求分析各轮差异。写入失败不抛错。"""
        if not debug_dir or not workflow_json:
            return
        try:
            debug_dir.mkdir(parents=True, exist_ok=True)
            path = debug_dir / f"{round_name}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(workflow_json, f, ensure_ascii=False, indent=2)
            logger.info("[workflow_debug] 已写入 %s", path)
        except Exception as e:
            logger.warning("[workflow_debug] 写入 %s 失败: %s", round_name, e)

    # ─── 后处理：规范化 ─────────────────────────────────────────

    def _normalize_workflow(
        self, w: Dict[str, Any], tool_plan: Optional[ToolPlan] = None
    ) -> Dict[str, Any]:
        """规范化工作流 JSON，补全毕昇前端必需的字段。"""
        from datetime import datetime

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

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

        if node_type == "tool":
            self._clear_tool_param_hardcoded_values(data)

    def _clear_tool_param_hardcoded_values(self, data: Dict[str, Any]) -> None:
        """将工具节点中「用户/查询类」参数的非变量写死值清空，避免固定为某地/某日等。"""
        for grp in data.get("group_params", []):
            if grp.get("name") != "工具参数":
                continue
            for p in grp.get("params", []):
                if p.get("key") not in _USER_VARIABLE_TOOL_PARAM_KEYS:
                    continue
                val = p.get("value")
                if isinstance(val, str) and val.strip() and "{{#" not in val:
                    p["value"] = ""
                    logger.debug(
                        "清空工具参数写死值: key=%s, node=%s",
                        p.get("key"),
                        data.get("id"),
                    )

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
            elif (
                p.get("key") == "guide_question"
                and pt == "input_list"
                and isinstance(v, list)
                and v
                and isinstance(v[0], dict)
            ):
                # 平台 GuideQuestionData 要求 guide_question 为字符串数组，非 {key,value} 对象数组
                p["value"] = [
                    x.get("value", "") if isinstance(x, dict) else str(x)
                    for x in v
                ]
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

    def _normalize_code_node(self, data: Dict[str, Any]) -> None:
        data.setdefault("expand", True)
        if data.get("v") is None:
            data["v"] = "1"

        grps = data.get("group_params", [])
        grp_names = [g.get("name", "") for g in grps]

        if "入参" not in grp_names:
            grps.insert(
                0,
                {
                    "name": "入参",
                    "params": [
                        {
                            "key": "code_input",
                            "test": "input",
                            "type": "code_input",
                            "value": [],
                            "required": True,
                        }
                    ],
                },
            )
        if "执行代码" not in grp_names:
            grps.append(
                {
                    "name": "执行代码",
                    "params": [
                        {
                            "key": "code",
                            "type": "code",
                            "value": "def main() -> dict:\n    return {}",
                            "required": True,
                        }
                    ],
                }
            )
        if "出参" not in grp_names:
            grps.append(
                {
                    "name": "出参",
                    "params": [
                        {
                            "key": "code_output",
                            "type": "code_output",
                            "value": [],
                            "global": "code:value.map(el => ({ label: el.key, value: el.key }))",
                            "required": True,
                        }
                    ],
                }
            )

        for grp in grps:
            for p in grp.get("params", []):
                if p.get("key") == "code_output" and "global" not in p:
                    p["global"] = (
                        "code:value.map(el => ({ label: el.key, value: el.key }))"
                    )

    def _normalize_edges(self, w: Dict[str, Any]) -> None:
        nodes = w.get("nodes", [])
        source_node_type = {
            n.get("id"): (n.get("data") or {}).get("type") for n in nodes if n.get("id")
        }
        for e in w.get("edges", []):
            e.setdefault("type", "customEdge")
            e.setdefault("animated", True)
            e.setdefault("targetHandle", "left_handle")
            src = e.get("source")
            src_type = source_node_type.get(src) if src else None
            if src_type == "start":
                e.setdefault("sourceHandle", "start")
            elif src_type == "condition":
                e.setdefault("sourceHandle", "right_handle")
            else:
                # input / llm / tool / knowledge_retriever / code 等：毕昇画布出口为 right_handle，避免误用 start 导致导入后缺边
                e["sourceHandle"] = "right_handle" if e.get("sourceHandle") in (None, "start") else e["sourceHandle"]
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
                    current_key,
                    fixed_key,
                    node.get("id"),
                )
                data["tool_key"] = fixed_key

    # ─── 格式化辅助 ─────────────────────────────────────────────

    def _format_tools_info(self, tool_plan: ToolPlan) -> str:
        if not tool_plan.selected_tools:
            return "无工具调用需求"

        lines = [
            "⚠️ 重要：以下每个工具的 tool_key 必须原样写入生成的 JSON，"
            "禁止省略、修改或截断任何部分（MCP 工具的 _数字ID 后缀不可删除）：",
            "工具参数中，表示用户输入、查询条件、地域、时间、关键词等的参数（如 province/city/date/query 等）"
            "请将 value 留空或绑定到输入/上游变量，不要写死为具体地名、日期、关键词。",
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
    def _is_mcp_tool(tool_item) -> bool:
        if tool_item.extra:
            ct = tool_item.extra.get("connection_type", "")
            if ct and ct != "builtin":
                return True
        return bool(re.search(r"_\d{4,}$", tool_item.tool_key))

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

    # ─── 流程图草图（先于完整工作流生成）─────────────────────────
