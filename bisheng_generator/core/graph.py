"""LangGraph 编排模块 - 工作流图构建与对外入口"""

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.checkpoint.memory import InMemorySaver

from config.config import Config, config
from models.workflow_state import WorkflowState
from infrastructure.model_factory import ModelInitializer, create_llm
from core.nodes import (
    NodeContext,
    run_intent_understanding,
    run_tool_selection,
    run_knowledge_matching,
    run_flow_sketch,
    run_workflow_generation,
)
from agents.user_agent import UserAgent
from agents.tool_agent import ToolAgent, ToolPlan
from agents.knowledge_agent import KnowledgeAgent, KnowledgeMatch
from agents.workflow_agent import WorkflowAgent
from models.progress import ProgressEvent
from core.utils import sketch_to_mermaid
from services.workflow_record_service import save_workflow_record
from core.intent_history import (
    add_intent_assistant_message_from_pending,
    add_intent_user_message,
)

logger = logging.getLogger(__name__)

# 定义事件回调类型
ProgressCallback = Callable[[ProgressEvent], Awaitable[None]]


class WorkflowOrchestrator:
    """工作流编排器 - 使用 LangGraph 编排多个 Agent"""

    def __init__(
        self,
        config_obj: Optional[Config] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ):
        """
        初始化编排器

        Args:
            config_obj: Config 配置对象，如果不传则使用全局配置
            progress_callback: 进度回调函数，用于实时推送事件
        """
        # 仅接受 Config 实例，请求体中的 dict 不用于 LLM/编排，统一用全局 config
        self.config = config_obj if isinstance(config_obj, Config) else config

        # 保存进度回调函数
        self.progress_callback = progress_callback

        # ========== 初始化模型 ==========
        self.llm = ModelInitializer.get_llm(self.config)
        llm_intent = ModelInitializer.get_llm_for_intent(self.config)
        llm_workflow = ModelInitializer.get_llm_for_workflow(self.config)

        # ========== 初始化 Agent ==========
        self.user_agent = UserAgent(
            llm_intent,
            prompts_dir=self.config.prompts_dir or None,
        )
        self.tool_agent = ToolAgent(
            mcp_search_url=self.config.mcp_search_url,
            mcp_search_top_k=self.config.mcp_search_top_k,
        )
        self.knowledge_agent = KnowledgeAgent(
            self.llm,
            prompts_dir=self.config.prompts_dir or None,
        )
        self.workflow_agent = WorkflowAgent(
            llm_workflow,
            prompts_dir=self.config.prompts_dir or None,
        )

        self._node_ctx = NodeContext(
            config=self.config,
            user_agent=self.user_agent,
            tool_agent=self.tool_agent,
            knowledge_agent=self.knowledge_agent,
            workflow_agent=self.workflow_agent,
            emit_progress=self._emit_progress,
        )

        # ========== 构建 LangGraph ==========
        self.graph = self._build_graph()

        logger.info("WorkflowOrchestrator 初始化完成")

    async def initialize(self) -> None:
        """
        异步初始化：在项目启动时调用一次，从毕昇接口加载知识库列表。
        使用协程方式请求，不阻塞主流程。
        """
        await self.knowledge_agent.load_knowledge_catalog(
            base_url=self.config.bisheng_base_url,
            access_token="",
        )

    def _build_graph(self) -> StateGraph:
        """
        构建 LangGraph 工作流（支持条件流转）

        流程：
        START → intent_understanding → [条件分发]
            ├─→ tool_selection ──┐
            │                    ├─→ flow_sketch → workflow_generation → END
            └─→ knowledge_matching ┘
            direct ──────────────┘
        注：tool 与 knowledge 可并行，均汇入 flow_sketch；direct 直连 flow_sketch；草图后再生成完整工作流。

        Returns:
            编译后的 StateGraph
        """
        # 创建 StateGraph
        builder = StateGraph(WorkflowState)

        # 添加节点
        builder.add_node("intent_understanding", self._run_intent_understanding)
        builder.add_node("tool_selection", self._run_tool_selection)
        builder.add_node("knowledge_matching", self._run_knowledge_matching)
        builder.add_node("flow_sketch", self._run_flow_sketch)
        builder.add_node("workflow_generation", self._run_workflow_generation)

        # 添加边
        builder.add_edge(START, "intent_understanding")

        # 条件边：根据意图决定并行分发（direct 也进草图，再进生成）
        builder.add_conditional_edges(
            "intent_understanding",
            self._route_after_intent,
            {
                "tool": "tool_selection",
                "knowledge": "knowledge_matching",
                "direct": "flow_sketch",
            },
        )

        # 工具选择、知识库匹配均汇入流程图草图，草图后再生成完整工作流
        builder.add_edge("tool_selection", "flow_sketch")
        builder.add_edge("knowledge_matching", "flow_sketch")
        builder.add_edge("flow_sketch", "workflow_generation")

        # 工作流生成后结束
        builder.add_edge("workflow_generation", END)

        # 编译图（带 checkpointer 以支持 interrupt / resume）
        graph = builder.compile(checkpointer=InMemorySaver())

        logger.info("LangGraph 构建完成（支持条件路由 + interrupt/resume）")
        return graph

    def _route_after_intent(self, state: WorkflowState) -> List[str]:
        """
        意图理解后的路由决策：支持并行触发
        """
        intent = state.get("intent")
        if not intent:
            return ["direct"]

        targets = []
        if intent.needs_tool:
            targets.append("tool")
        if intent.needs_knowledge:
            targets.append("knowledge")

        # 如果都没有，直接去生成
        if not targets:
            return ["direct"]

        logger.info(f"并行路由触发：激活节点 {targets}")
        return targets

    async def _run_intent_understanding(
        self, state: WorkflowState
    ) -> Dict[str, Any]:
        """运行意图理解节点（委托到 core.nodes.intent_node）。"""
        return await run_intent_understanding(state, self._node_ctx)

    async def _run_tool_selection(
        self, state: WorkflowState
    ) -> Dict[str, Any]:
        """运行工具选择节点（委托到 core.nodes.tool_node）。"""
        return await run_tool_selection(state, self._node_ctx)

    async def _run_knowledge_matching(
        self, state: WorkflowState
    ) -> Dict[str, Any]:
        """运行知识库匹配节点（委托到 core.nodes.knowledge_node）。"""
        return await run_knowledge_matching(state, self._node_ctx)

    async def _run_flow_sketch(
        self, state: WorkflowState
    ) -> Dict[str, Any]:
        """运行流程图草图节点（委托到 core.nodes.sketch_node）。"""
        return await run_flow_sketch(state, self._node_ctx)

    async def _run_workflow_generation(
        self, state: WorkflowState
    ) -> Dict[str, Any]:
        """运行工作流生成节点（委托到 core.nodes.workflow_node）。"""
        return await run_workflow_generation(state, self._node_ctx)

    async def generate(
        self,
        user_input: str,
        session_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        *,
        bisheng_base_url: Optional[str] = None,
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        生成工作流（首轮）

        Args:
            user_input: 用户输入
            session_id: 会话 ID（用于 checkpointer thread_id）
            config: LangGraph config（含 configurable.thread_id）
            bisheng_base_url: 毕昇 API 地址，供知识库匹配节点惰性加载 catalog
            access_token: 毕昇鉴权 token

        Returns:
            生成结果（可能含 needs_clarification）
        """
        logger.info("收到用户输入：%s, session_id=%s", user_input[:80], session_id)

        initial_state = WorkflowState(
            user_input=user_input,
            intent=None,
            tool_plan=None,
            knowledge_match=None,
            workflow=None,
            error=None,
            session_id=session_id,
            bisheng_base_url=bisheng_base_url or self.config.bisheng_base_url,
            access_token=access_token or "",
        )

        graph_config = config or {}
        if session_id and "configurable" not in graph_config:
            graph_config["configurable"] = {"thread_id": session_id}

        try:
            result = await self.graph.ainvoke(initial_state, config=graph_config)
            return self._process_result(result, session_id)
        except Exception as e:
            logger.exception("工作流生成失败：%s", e)
            return {"status": "error", "message": f"工作流生成失败：{str(e)}"}

    async def generate_resume(
        self,
        resume_value: str,
        session_id: str,
        config: Optional[Dict[str, Any]] = None,
        original_user_input: Optional[str] = None,
        *,
        bisheng_base_url: Optional[str] = None,
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        续轮：恢复被 interrupt 暂停的图

        Args:
            resume_value: 用户澄清回复
            session_id: 会话 ID（与首轮同一个）
            config: LangGraph config
            original_user_input: 首轮用户输入（续轮时须传入以恢复 state，否则可能 KeyError）
            bisheng_base_url: 毕昇 API 地址，供知识库匹配节点惰性加载 catalog
            access_token: 毕昇鉴权 token

        Returns:
            生成结果
        """
        logger.info(
            "续轮恢复，resume_value=%s, session_id=%s", resume_value[:80], session_id
        )

        graph_config = config or {}
        if "configurable" not in graph_config:
            graph_config["configurable"] = {"thread_id": session_id}

        # 续轮时传入当前用户回复与 session_id，以及毕昇地址/token 供知识库匹配节点惰性加载
        update: Dict[str, Any] = {
            "user_input": (resume_value or "").strip(),
            "session_id": session_id,
        }
        if bisheng_base_url is not None:
            update["bisheng_base_url"] = bisheng_base_url
        if access_token is not None:
            update["access_token"] = access_token

        try:
            result = await self.graph.ainvoke(
                Command(resume=resume_value, update=update), config=graph_config
            )
            return self._process_result(result, session_id)
        except Exception as e:
            logger.exception("续轮恢复失败：%s", e)
            return {"status": "error", "message": f"续轮恢复失败：{str(e)}"}

    def _process_result(
        self, result: Dict[str, Any], session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """统一处理 ainvoke 返回值（含 __interrupt__ 检测），并落库记录"""
        # 检测 interrupt（需要澄清）
        interrupts = result.get("__interrupt__")
        if interrupts:
            pending = (
                interrupts[0].value
                if hasattr(interrupts[0], "value")
                else interrupts[0]
            )
            logger.info("检测到 __interrupt__，需要澄清, pending=%s", pending)
            if session_id and isinstance(pending, dict):
                try:
                    add_intent_user_message(
                        session_id, (result.get("user_input") or "").strip()
                    )
                    add_intent_assistant_message_from_pending(session_id, pending)
                except Exception as e:
                    logger.warning("写入意图历史失败: %s", e)
            save_workflow_record(
                self.config,
                result,
                session_id,
                status="needs_clarification",
                error_message=None,
            )
            return {
                "status": "success",
                "needs_clarification": True,
                "pending_clarification": pending,
                "session_id": session_id,
                "message": "需要用户补充信息",
            }

        if result.get("error"):
            save_workflow_record(
                self.config,
                result,
                session_id,
                status="error",
                error_message=result["error"],
            )
            return {"status": "error", "message": result["error"]}

        tool_plan = result.get("tool_plan") or ToolPlan()
        knowledge_match = result.get("knowledge_match") or KnowledgeMatch(
            required=False
        )
        metadata: Dict[str, Any] = {
            "intent": (
                result.get("intent").model_dump(mode="json")
                if result.get("intent")
                else None
            ),
            "tools_count": len(tool_plan.selected_tools),
            "knowledge_count": (
                len(knowledge_match.matched_knowledge_bases) if knowledge_match else 0
            ),
        }
        if result.get("warnings"):
            metadata["warnings"] = result["warnings"]

        flow_sketch_mermaid = ""
        flow_sketch = result.get("flow_sketch")
        if flow_sketch and isinstance(flow_sketch, dict):
            flow_sketch_mermaid = sketch_to_mermaid(flow_sketch) or ""
        if flow_sketch_mermaid:
            metadata["flow_sketch_mermaid"] = flow_sketch_mermaid

        save_workflow_record(
            self.config,
            result,
            session_id,
            status="success",
            error_message=None,
        )
        out: Dict[str, Any] = {
            "status": "success",
            "message": "工作流生成成功",
            "workflow": result.get("workflow"),
            "metadata": metadata,
            "session_id": session_id,
        }
        if flow_sketch_mermaid:
            out["flow_sketch_mermaid"] = flow_sketch_mermaid
        return out

    async def generate_with_progress(
        self,
        user_input: str,
        progress_callback: ProgressCallback,
        session_id: Optional[str] = None,
        graph_config: Optional[Dict[str, Any]] = None,
        is_resume: bool = False,
        original_user_input: Optional[str] = None,
        *,
        bisheng_base_url: Optional[str] = None,
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        生成工作流并实时推送进度（流式版本）

        Args:
            user_input: 用户输入（续轮时为用户澄清回复）
            progress_callback: 进度回调函数
            session_id: 会话 ID
            graph_config: LangGraph config
            is_resume: 是否为续轮
            original_user_input: 首轮用户输入（续轮时必传，用于恢复 state）
            bisheng_base_url: 毕昇 API 地址，供知识库匹配节点惰性加载
            access_token: 毕昇鉴权 token

        Returns:
            生成的工作流
        """
        logger.info(
            "流式生成开始，user_input=%s, session_id=%s, is_resume=%s",
            (user_input or "")[:80],
            session_id,
            is_resume,
        )
        self.progress_callback = progress_callback

        if is_resume and session_id:
            result = await self.generate_resume(
                user_input,
                session_id,
                config=graph_config,
                original_user_input=original_user_input,
                bisheng_base_url=bisheng_base_url,
                access_token=access_token,
            )
        else:
            result = await self.generate(
                user_input,
                session_id=session_id,
                config=graph_config,
                bisheng_base_url=bisheng_base_url,
                access_token=access_token,
            )

        status = result.get("status")

        if result.get("needs_clarification"):
            await self._emit_progress(
                ProgressEvent.create_needs_clarification_event(
                    result.get("pending_clarification", {}),
                    result.get("session_id", session_id or ""),
                )
            )
            logger.info("流式生成暂停（需要澄清），session_id=%s", session_id)
        elif status == "success":
            # 不在此处发送 complete：由 api 层在 task 完成后统一发送一次带完整 result 的 final_event，避免前端收到两次 complete 出现重复结果卡
            logger.info("流式生成完成，status=success")
        else:
            await self._emit_progress(
                ProgressEvent.create_error_event(result.get("message", "未知错误"))
            )
            logger.warning(
                "流式生成失败，status=error, message=%s", result.get("message", "")
            )
        return result

    async def _emit_progress(self, event: ProgressEvent) -> None:
        """
        发送进度事件

        Args:
            event: 进度事件
        """
        if self.progress_callback:
            try:
                await self.progress_callback(event)
            except Exception as e:
                logger.error(f"发送进度事件失败：{e}")
