"""LangGraph 编排模块 - 包含 BaseChatModel 初始化和工作流编排"""

from typing import Optional, Dict, Any, TypedDict, Callable, Awaitable, List, NotRequired
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from langgraph.graph import StateGraph, START, END
import logging
import time

from config.config import Config, config
from core.utils import is_retryable
from models.intent import EnhancedIntent
from agents.user_agent import UserAgent
from agents.tool_agent import ToolAgent, ToolPlan
from agents.knowledge_agent import KnowledgeAgent, KnowledgeMatch
from agents.workflow_agent import WorkflowAgent
from models.progress import (
    ProgressEvent,
    AgentName,
)

logger = logging.getLogger(__name__)

# 定义事件回调类型
ProgressCallback = Callable[[ProgressEvent], Awaitable[None]]


class ModelInitializer:
    """模型初始化器"""

    _llm_instance: Optional[BaseChatModel] = None
    _embedding_instance: Optional[Embeddings] = None

    @classmethod
    def get_llm(cls, config_obj: Optional[Config] = None) -> BaseChatModel:
        """
        获取 LLM 实例（单例模式）

        Args:
            config_obj: Config 配置对象，如果不传则使用全局配置

        Returns:
            BaseChatModel 实例
        """
        if cls._llm_instance is not None:
            return cls._llm_instance

        # 使用传入的 config 对象或全局配置
        cfg = config_obj or config

        logger.info(f"初始化 LLM: provider={cfg.llm_provider}, model={cfg.llm_model}")

        # 使用 OpenAI 兼容接口（DashScope 也使用此格式）
        cls._llm_instance = ChatOpenAI(
            model=cfg.llm_model,
            api_key=cfg.llm_api_key,
            base_url=cfg.llm_base_url,
            temperature=cfg.llm_temperature,
            streaming=True,  # 启用流式输出
            max_tokens=None,  # 不限制最大 token 数
            model_kwargs={
                "stream_options": {
                    "include_usage": True,
                }
            },
        )

        logger.info("LLM 初始化成功")
        return cls._llm_instance

    @classmethod
    def get_embedding(cls, config_obj: Optional[Config] = None) -> Optional[Embeddings]:
        """
        获取 Embedding 实例（预留）

        Args:
            config_obj: Config 配置对象

        Returns:
            Embeddings 实例
        """
        if cls._embedding_instance is not None:
            return cls._embedding_instance

        cfg = config_obj or config

        logger.info(f"初始化 Embedding: model={cfg.embedding_model}")

        # TODO: 实现 Embedding 初始化
        # 可以使用 DashScope 的 embedding 模型
        # from langchain_community.embeddings import DashScopeEmbeddings
        # cls._embedding_instance = DashScopeEmbeddings(
        #     model=cfg.embedding_model,
        #     api_key=cfg.llm_api_key,
        #     dashscope_api_base=cfg.llm_base_url
        # )

        logger.warning("Embedding 暂未实现")
        return None

    @classmethod
    def reset(cls):
        """重置模型实例（用于测试）"""
        cls._llm_instance = None
        cls._embedding_instance = None


class WorkflowState(TypedDict):
    """工作流编排状态"""

    user_input: str
    intent: Optional[EnhancedIntent]
    tool_plan: Optional[ToolPlan]
    knowledge_match: Optional[KnowledgeMatch]
    workflow: Optional[Dict[str, Any]]
    error: Optional[str]
    warnings: NotRequired[Optional[List[str]]]  # 降级时追加说明，便于前端展示


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
        self.embedding = ModelInitializer.get_embedding(self.config)

        # ========== 初始化 Agent ==========
        self.user_agent = UserAgent(self.llm, self.embedding)
        self.tool_agent = ToolAgent(self.llm, self.embedding)
        self.knowledge_agent = KnowledgeAgent(self.llm, self.embedding)
        self.workflow_agent = WorkflowAgent(self.llm)

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
            │                    ├─→ workflow_generation → END
            └─→ knowledge_matching ┘
        注：tool 和 knowledge 节点可并行触发，workflow_generation 节点会自动等待。

        Returns:
            编译后的 StateGraph
        """
        # 创建 StateGraph
        builder = StateGraph(WorkflowState)

        # 添加节点
        builder.add_node("intent_understanding", self._run_intent_understanding)
        builder.add_node("tool_selection", self._run_tool_selection)
        builder.add_node("knowledge_matching", self._run_knowledge_matching)
        builder.add_node("workflow_generation", self._run_workflow_generation)

        # 添加边
        builder.add_edge(START, "intent_understanding")

        # 条件边：根据意图决定并行分发
        builder.add_conditional_edges(
            "intent_understanding",
            self._route_after_intent,
            {
                "tool": "tool_selection",
                "knowledge": "knowledge_matching",
                "direct": "workflow_generation",
            },
        )

        # 工具选择和知识库匹配均指向生成，生成节点作为汇合点 (Fan-in)
        builder.add_edge("tool_selection", "workflow_generation")
        builder.add_edge("knowledge_matching", "workflow_generation")

        # 工作流生成后结束
        builder.add_edge("workflow_generation", END)

        # 编译图
        graph = builder.compile()

        logger.info("LangGraph 构建完成（支持条件路由）")
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

    async def _run_intent_understanding(self, state: WorkflowState) -> WorkflowState:
        """运行意图理解 Agent（含重试与降级）"""
        user_input = state["user_input"]
        logger.info(
            "意图理解开始",
            extra={"user_input_preview": user_input[:100] if user_input else ""},
        )

        start_time = time.time()
        await self._emit_progress(
            ProgressEvent.create_agent_start_event(AgentName.INTENT_UNDERSTANDING)
        )

        last_error: Optional[Exception] = None
        for attempt in range(config.max_retries_intent + 1):
            try:
                intent = await self.user_agent.understand(user_input)
                if intent.rewritten_input:
                    duration_ms = (time.time() - start_time) * 1000
                    logger.info(
                        "意图理解完成",
                        extra={
                            "rewritten_input_preview": intent.rewritten_input[:80],
                            "needs_tool": intent.needs_tool,
                            "needs_knowledge": intent.needs_knowledge,
                        },
                    )
                    event_data = {
                        "workflow_type": intent.get_workflow_type(),
                        "needs_tool": intent.needs_tool,
                        "needs_knowledge": intent.needs_knowledge,
                        "rewritten_input": intent.rewritten_input,
                    }
                    await self._emit_progress(
                        ProgressEvent.create_agent_complete_event(
                            AgentName.INTENT_UNDERSTANDING, event_data, duration_ms
                        )
                    )
                    return {"intent": intent}
                # 空结果视作可重试，最后一次则降级
                last_error = ValueError("意图理解返回空结果")
            except Exception as e:
                last_error = e
                if not is_retryable(e):
                    duration_ms = (time.time() - start_time) * 1000
                    logger.exception("意图理解失败(不可重试)：%s", e)
                    await self._emit_progress(
                        ProgressEvent.create_agent_error_event(
                            AgentName.INTENT_UNDERSTANDING, str(e), duration_ms
                        )
                    )
                    return {"error": f"意图理解失败：{str(e)}"}
                if attempt == config.max_retries_intent:
                    break
                logger.warning(
                    "意图理解重试",
                    extra={"attempt": attempt + 1, "reason": str(e)},
                )

        # 降级：使用原始输入作为重写结果，不写 state["error"]
        duration_ms = (time.time() - start_time) * 1000
        fallback_intent = EnhancedIntent(
            original_input=user_input,
            rewritten_input=user_input,
            needs_tool=False,
            needs_knowledge=False,
            multi_turn=True,
        )
        logger.warning(
            "意图理解降级：使用原始输入作为重写结果",
            extra={"original_input": (user_input or "")[:100]},
        )
        await self._emit_progress(
            ProgressEvent.create_agent_complete_event(
                AgentName.INTENT_UNDERSTANDING,
                {
                    "workflow_type": fallback_intent.get_workflow_type(),
                    "needs_tool": False,
                    "needs_knowledge": False,
                    "rewritten_input": user_input,
                    "degraded": True,
                },
                duration_ms,
            )
        )
        warnings = list(state.get("warnings") or [])
        warnings.append("意图理解失败，已使用原始输入")
        return {"intent": fallback_intent, "warnings": warnings}

    async def _run_tool_selection(self, state: WorkflowState) -> WorkflowState:
        """运行工具选择 Agent（含重试与降级）"""
        intent = state.get("intent")
        needs_tool = bool(intent and intent.needs_tool)
        logger.info(
            "工具选择开始",
            extra={"needs_tool": needs_tool},
        )

        start_time = time.time()
        await self._emit_progress(
            ProgressEvent.create_agent_start_event(AgentName.TOOL_SELECTION)
        )

        if not intent or not intent.needs_tool:
            tool_plan = ToolPlan()
            duration_ms = (time.time() - start_time) * 1000
            logger.info("工具选择跳过(不需要工具)", extra={"needs_tool": False})
            await self._emit_progress(
                ProgressEvent.create_agent_complete_event(
                    AgentName.TOOL_SELECTION,
                    {"tools_count": 0, "message": "不需要调用工具，跳过工具选择"},
                    duration_ms,
                )
            )
            return {"tool_plan": tool_plan}

        last_error: Optional[Exception] = None
        for attempt in range(config.max_retries_tool + 1):
            try:
                tool_plan = await self.tool_agent.select_tools(intent)
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    "工具选择完成",
                    extra={
                        "selected_count": len(tool_plan.selected_tools),
                        "tool_keys": [t.tool_key for t in tool_plan.selected_tools],
                    },
                )
                event_data = {
                    "tools_count": len(tool_plan.selected_tools),
                    "selected_tools": (
                        [
                            {"name": t.name, "description": t.desc}
                            for t in tool_plan.selected_tools
                        ]
                        if tool_plan.selected_tools
                        else []
                    ),
                }
                await self._emit_progress(
                    ProgressEvent.create_agent_complete_event(
                        AgentName.TOOL_SELECTION, event_data, duration_ms
                    )
                )
                return {"tool_plan": tool_plan}
            except Exception as e:
                last_error = e
                if not is_retryable(e):
                    duration_ms = (time.time() - start_time) * 1000
                    logger.exception("工具选择失败(不可重试)：%s", e)
                    await self._emit_progress(
                        ProgressEvent.create_agent_error_event(
                            AgentName.TOOL_SELECTION, str(e), duration_ms
                        )
                    )
                    return {"error": f"工具选择失败：{str(e)}"}
                if attempt == config.max_retries_tool:
                    break
                logger.warning(
                    "工具选择重试",
                    extra={"attempt": attempt + 1, "reason": str(e)},
                )

        # 降级：返回空工具列表
        duration_ms = (time.time() - start_time) * 1000
        logger.warning(
            "工具选择降级：返回空工具列表",
            extra={"reason": str(last_error) if last_error else "unknown"},
        )
        await self._emit_progress(
            ProgressEvent.create_agent_complete_event(
                AgentName.TOOL_SELECTION,
                {"tools_count": 0, "message": "工具选择失败，已降级为空列表", "degraded": True},
                duration_ms,
            )
        )
        warnings = list(state.get("warnings") or [])
        warnings.append("工具选择失败，已使用空工具列表")
        return {"tool_plan": ToolPlan(), "warnings": warnings}

    async def _run_knowledge_matching(self, state: WorkflowState) -> WorkflowState:
        """运行知识库匹配 Agent（含重试与降级）"""
        intent = state.get("intent")
        needs_knowledge = bool(intent and intent.needs_knowledge)
        logger.info(
            "知识库匹配开始",
            extra={"needs_knowledge": needs_knowledge},
        )

        start_time = time.time()
        await self._emit_progress(
            ProgressEvent.create_agent_start_event(AgentName.KNOWLEDGE_MATCHING)
        )

        if not intent or not intent.needs_knowledge:
            knowledge_match = KnowledgeMatch(required=False)
            duration_ms = (time.time() - start_time) * 1000
            logger.info("知识库匹配跳过(不需要知识库)", extra={"needs_knowledge": False})
            await self._emit_progress(
                ProgressEvent.create_agent_complete_event(
                    AgentName.KNOWLEDGE_MATCHING,
                    {
                        "knowledge_count": 0,
                        "message": "不需要知识库，跳过知识库匹配",
                    },
                    duration_ms,
                )
            )
            return {"knowledge_match": knowledge_match}

        last_error: Optional[Exception] = None
        for attempt in range(config.max_retries_knowledge + 1):
            try:
                knowledge_match = await self.knowledge_agent.match_knowledge(intent)
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    "知识库匹配完成",
                    extra={
                        "matched_count": len(knowledge_match.matched_knowledge_bases),
                        "kb_ids": [kb.id for kb in knowledge_match.matched_knowledge_bases],
                    },
                )
                event_data = {
                    "knowledge_count": len(knowledge_match.matched_knowledge_bases),
                    "matched_knowledge_bases": (
                        [
                            {"name": kb.name, "description": kb.desc}
                            for kb in knowledge_match.matched_knowledge_bases
                        ]
                        if knowledge_match.matched_knowledge_bases
                        else []
                    ),
                }
                await self._emit_progress(
                    ProgressEvent.create_agent_complete_event(
                        AgentName.KNOWLEDGE_MATCHING, event_data, duration_ms
                    )
                )
                return {"knowledge_match": knowledge_match}
            except Exception as e:
                last_error = e
                if not is_retryable(e):
                    duration_ms = (time.time() - start_time) * 1000
                    logger.exception("知识库匹配失败(不可重试)：%s", e)
                    await self._emit_progress(
                        ProgressEvent.create_agent_error_event(
                            AgentName.KNOWLEDGE_MATCHING, str(e), duration_ms
                        )
                    )
                    return {"error": f"知识库匹配失败：{str(e)}"}
                if attempt == config.max_retries_knowledge:
                    break
                logger.warning(
                    "知识库匹配重试",
                    extra={"attempt": attempt + 1, "reason": str(e)},
                )

        # 降级：返回空知识库列表
        duration_ms = (time.time() - start_time) * 1000
        logger.warning(
            "知识库匹配降级：返回空知识库列表",
            extra={"reason": str(last_error) if last_error else "unknown"},
        )
        await self._emit_progress(
            ProgressEvent.create_agent_complete_event(
                AgentName.KNOWLEDGE_MATCHING,
                {
                    "knowledge_count": 0,
                    "message": "知识库匹配失败，已降级为空列表",
                    "degraded": True,
                },
                duration_ms,
            )
        )
        warnings = list(state.get("warnings") or [])
        warnings.append("知识库匹配失败，已使用空知识库列表")
        return {
            "knowledge_match": KnowledgeMatch(required=False),
            "warnings": warnings,
        }

    async def _run_workflow_generation(self, state: WorkflowState) -> WorkflowState:
        """运行工作流生成 Agent（含重试与详细日志）"""
        start_time = time.time()
        await self._emit_progress(
            ProgressEvent.create_agent_start_event(AgentName.WORKFLOW_GENERATION)
        )

        if state.get("error"):
            duration_ms = (time.time() - start_time) * 1000
            await self._emit_progress(
                ProgressEvent.create_agent_error_event(
                    AgentName.WORKFLOW_GENERATION,
                    f"前置步骤错误：{state.get('error')}",
                    duration_ms,
                )
            )
            return state

        intent = state.get("intent")
        if not intent:
            error_msg = "意图理解失败，无法生成工作流"
            logger.error(error_msg)
            duration_ms = (time.time() - start_time) * 1000
            await self._emit_progress(
                ProgressEvent.create_agent_error_event(
                    AgentName.WORKFLOW_GENERATION, error_msg, duration_ms
                )
            )
            return {"error": error_msg}

        tool_plan = state.get("tool_plan") or ToolPlan()
        knowledge_match = state.get("knowledge_match") or KnowledgeMatch(
            required=False
        )

        last_error: Optional[str] = None
        workflow_result: Optional[Dict[str, Any]] = None
        for attempt in range(config.max_retries_workflow + 1):
            try:
                workflow_result = await self.workflow_agent.generate_workflow(
                    intent=intent,
                    tool_plan=tool_plan,
                    knowledge_match=knowledge_match,
                )
                if isinstance(workflow_result, dict) and "error" in workflow_result:
                    last_error = workflow_result.get("error", "工作流生成内容无效")
                    content_preview = (workflow_result.get("content") or "")[:200]
                    if attempt < config.max_retries_workflow:
                        logger.warning(
                            "工作流生成重试",
                            extra={
                                "attempt": attempt + 1,
                                "reason": last_error,
                                "content_preview": content_preview,
                            },
                        )
                        continue
                    break
                # 成功：无 error 键
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    "工作流生成完成",
                    extra={"nodes_count": len(workflow_result.get("nodes", []))},
                )
                await self._emit_progress(
                    ProgressEvent.create_agent_complete_event(
                        AgentName.WORKFLOW_GENERATION,
                        {"workflow_generated": True},
                        duration_ms,
                    )
                )
                return {"workflow": workflow_result}
            except Exception as e:
                last_error = str(e)
                if not is_retryable(e):
                    duration_ms = (time.time() - start_time) * 1000
                    logger.exception("工作流生成失败(不可重试)：%s", e)
                    await self._emit_progress(
                        ProgressEvent.create_agent_error_event(
                            AgentName.WORKFLOW_GENERATION, str(e), duration_ms
                        )
                    )
                    return {"error": f"工作流生成失败：{str(e)}"}
                if attempt < config.max_retries_workflow:
                    logger.warning(
                        "工作流生成重试",
                        extra={"attempt": attempt + 1, "reason": str(e)},
                    )
                else:
                    logger.error(
                        "工作流生成失败(已用尽重试)",
                        extra={
                            "reason": str(e),
                            "intent_preview": (intent.rewritten_input or "")[:80],
                        },
                    )

        # 重试用尽
        duration_ms = (time.time() - start_time) * 1000
        error_msg = last_error or "工作流生成失败"
        await self._emit_progress(
            ProgressEvent.create_agent_error_event(
                AgentName.WORKFLOW_GENERATION, error_msg, duration_ms
            )
        )
        return {"error": f"工作流生成失败：{error_msg}"}

    async def generate(self, user_input: str) -> Dict[str, Any]:
        """
        生成工作流（完整版本 - 使用 LangGraph 编排）

        Args:
            user_input: 用户输入

        Returns:
            生成的工作流
        """
        logger.info(f"收到用户输入：{user_input}")

        # 初始状态
        initial_state = WorkflowState(
            user_input=user_input,
            intent=None,
            tool_plan=None,
            knowledge_match=None,
            workflow=None,
            error=None,
        )

        # 运行图
        try:
            result = await self.graph.ainvoke(initial_state)

            # 检查是否有错误
            if result.get("error"):
                return {"status": "error", "message": result["error"]}

            # 返回成功结果
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
                    len(knowledge_match.matched_knowledge_bases)
                    if knowledge_match
                    else 0
                ),
            }
            if result.get("warnings"):
                metadata["warnings"] = result["warnings"]

            return {
                "status": "success",
                "message": "工作流生成成功",
                "workflow": result.get("workflow"),
                "metadata": metadata,
            }
        except Exception as e:
            logger.exception(f"工作流生成失败：{e}")
            return {"status": "error", "message": f"工作流生成失败：{str(e)}"}

    async def generate_with_progress(
        self, user_input: str, progress_callback: ProgressCallback
    ) -> Dict[str, Any]:
        """
        生成工作流并实时推送进度（流式版本）

        Args:
            user_input: 用户输入
            progress_callback: 进度回调函数

        Returns:
            生成的工作流
        """
        logger.info("流式生成开始，user_input=%s", (user_input or "")[:80])
        self.progress_callback = progress_callback
        await self._emit_progress(ProgressEvent.create_start_event(user_input))

        result = await self.generate(user_input)
        status = result.get("status")

        if status == "success":
            await self._emit_progress(
                ProgressEvent.create_complete_event(
                    result.get("workflow", {}), result.get("metadata", {})
                )
            )
            logger.info("流式生成完成，status=success")
        else:
            await self._emit_progress(
                ProgressEvent.create_error_event(result.get("message", "未知错误"))
            )
            logger.warning("流式生成失败，status=error, message=%s", result.get("message", ""))
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


# ========== 便捷函数 ==========


def create_llm(config_obj: Optional[Config] = None) -> BaseChatModel:
    """
    创建 LLM 实例的便捷函数

    Args:
        config_obj: Config 配置对象

    Returns:
        BaseChatModel 实例
    """
    return ModelInitializer.get_llm(config_obj)


def create_embedding(config_obj: Optional[Config] = None) -> Optional[Embeddings]:
    """
    创建 Embedding 实例的便捷函数

    Args:
        config_obj: Config 配置对象

    Returns:
        Embeddings 实例
    """
    return ModelInitializer.get_embedding(config_obj)
