"""LangGraph 编排模块 - 包含 BaseChatModel 初始化和工作流编排"""

from typing import Optional, Dict, Any, TypedDict, Callable, Awaitable
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from langgraph.graph import StateGraph, START, END
import logging
import time

from config.config import Config, config
from models.intent import EnhancedIntent
from agents.user_agent import UserAgent
from agents.tool_agent import ToolAgent, ToolPlan
from agents.knowledge_agent import KnowledgeAgent, KnowledgeMatch
from agents.workflow_agent import WorkflowAgent
from models.progress import (
    ProgressEvent,
    ProgressEventType,
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


class WorkflowOrchestrator:
    """工作流编排器 - 使用 LangGraph 编排多个 Agent"""

    def __init__(
        self,
        config_obj: Optional[Config] = None,
        progress_callback: Optional[ProgressCallback] = None
    ):
        """
        初始化编排器

        Args:
            config_obj: Config 配置对象，如果不传则使用全局配置
            progress_callback: 进度回调函数，用于实时推送事件
        """
        # 保存配置对象
        self.config = config_obj or config
        
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

    def _build_graph(self) -> StateGraph:
        """
        构建 LangGraph 工作流（支持条件路由）

        流程：
        START → intent_understanding → [条件路由]
            ├─ 需要工具 → tool_selection → knowledge_matching
            └─ 不需要工具 → knowledge_matching
        knowledge_matching → [条件路由]
            ├─ 需要知识库 → knowledge_matching (已在当前节点)
            └─ 不需要知识库 → workflow_generation
        workflow_generation → END

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

        # 条件边：根据意图决定是否需要工具选择
        builder.add_conditional_edges(
            "intent_understanding",
            self._route_after_intent,
            {
                "need_tool": "tool_selection",
                "no_tool": "knowledge_matching",  # 直接跳过工具选择
            },
        )

        # 工具选择后到知识库匹配
        builder.add_edge("tool_selection", "knowledge_matching")

        # 知识库匹配后到工作流生成
        builder.add_edge("knowledge_matching", "workflow_generation")

        # 工作流生成后结束
        builder.add_edge("workflow_generation", END)

        # 编译图
        graph = builder.compile()

        logger.info("LangGraph 构建完成（支持条件路由）")
        return graph

    def _route_after_intent(self, state: WorkflowState) -> str:
        """
        意图理解后的路由决策

        Returns:
            "need_tool" 或 "no_tool"
        """
        intent = state.get("intent")
        if not intent:
            logger.warning("意图为空，默认不选择工具")
            return "no_tool"

        if intent.needs_tool:
            logger.info(
                f"路由决策：需要工具 → tool_selection (工作流类型：{intent.get_workflow_type()})"
            )
            return "need_tool"
        else:
            logger.info(
                f"路由决策：不需要工具 → knowledge_matching (工作流类型：{intent.get_workflow_type()})"
            )
            return "no_tool"

    async def _run_intent_understanding(self, state: WorkflowState) -> WorkflowState:
        """运行意图理解 Agent"""
        logger.info(f"运行意图理解：{state['user_input']}")
        
        # 发送 Agent 开始事件
        start_time = time.time()
        await self._emit_progress(
            ProgressEvent.create_agent_start_event(AgentName.INTENT_UNDERSTANDING)
        )
        
        try:
            intent = await self.user_agent.understand(state["user_input"])
            duration_ms = (time.time() - start_time) * 1000
            
            logger.info(f"意图理解完成：{intent.get_workflow_type()}")
            
            # 检查意图对象是否有效（至少 rewritten_input 应该有值）
            if not intent.rewritten_input:
                error_msg = "意图理解返回空结果"
                logger.error(error_msg)
                await self._emit_progress(
                    ProgressEvent.create_agent_error_event(
                        AgentName.INTENT_UNDERSTANDING,
                        error_msg,
                        duration_ms
                    )
                )
                return {"error": error_msg}
            
            # 发送 Agent 完成事件
            event_data = {
                "workflow_type": intent.get_workflow_type(),
                "needs_tool": intent.needs_tool,
                "needs_knowledge": intent.needs_knowledge,
                "rewritten_input": intent.rewritten_input
            }
            await self._emit_progress(
                ProgressEvent.create_agent_complete_event(
                    AgentName.INTENT_UNDERSTANDING,
                    event_data,
                    duration_ms
                )
            )
            
            return {"intent": intent}
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"意图理解失败：{e}")
            await self._emit_progress(
                ProgressEvent.create_agent_error_event(
                    AgentName.INTENT_UNDERSTANDING,
                    str(e),
                    duration_ms
                )
            )
            return {"error": f"意图理解失败：{str(e)}"}

    async def _run_tool_selection(self, state: WorkflowState) -> WorkflowState:
        """运行工具选择 Agent"""
        logger.info("运行工具选择")
        
        # 发送 Agent 开始事件
        start_time = time.time()
        await self._emit_progress(
            ProgressEvent.create_agent_start_event(AgentName.TOOL_SELECTION)
        )
        
        try:
            intent = state.get("intent")
            if not intent:
                tool_plan = ToolPlan()
                duration_ms = (time.time() - start_time) * 1000
                await self._emit_progress(
                    ProgressEvent.create_agent_complete_event(
                        AgentName.TOOL_SELECTION,
                        {"tools_count": 0, "message": "意图为空，跳过工具选择"},
                        duration_ms
                    )
                )
                return {"tool_plan": tool_plan}

            tool_plan = await self.tool_agent.select_tools(intent)
            duration_ms = (time.time() - start_time) * 1000
            
            logger.info(f"工具选择完成：选中 {len(tool_plan.selected_tools)} 个工具")
            
            # 发送 Agent 完成事件
            event_data = {
                "tools_count": len(tool_plan.selected_tools),
                "selected_tools": [
                    {"name": t.name, "description": t.description}
                    for t in tool_plan.selected_tools
                ] if tool_plan.selected_tools else []
            }
            await self._emit_progress(
                ProgressEvent.create_agent_complete_event(
                    AgentName.TOOL_SELECTION,
                    event_data,
                    duration_ms
                )
            )
            return {"tool_plan": tool_plan}
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"工具选择失败：{e}")
            await self._emit_progress(
                ProgressEvent.create_agent_error_event(
                    AgentName.TOOL_SELECTION,
                    str(e),
                    duration_ms
                )
            )
            return {"error": f"工具选择失败：{str(e)}"}

    async def _run_knowledge_matching(self, state: WorkflowState) -> WorkflowState:
        """运行知识库匹配 Agent"""
        logger.info("运行知识库匹配")
        
        # 发送 Agent 开始事件
        start_time = time.time()
        await self._emit_progress(
            ProgressEvent.create_agent_start_event(AgentName.KNOWLEDGE_MATCHING)
        )
        
        try:
            intent = state.get("intent")
            if not intent:
                knowledge_match = KnowledgeMatch(required=False)
                duration_ms = (time.time() - start_time) * 1000
                await self._emit_progress(
                    ProgressEvent.create_agent_complete_event(
                        AgentName.KNOWLEDGE_MATCHING,
                        {"knowledge_count": 0, "message": "意图为空，跳过知识库匹配"},
                        duration_ms
                    )
                )
                return {"knowledge_match": knowledge_match}

            knowledge_match = await self.knowledge_agent.match_knowledge(intent)
            duration_ms = (time.time() - start_time) * 1000
            
            logger.info(
                f"知识库匹配完成：匹配到 {len(knowledge_match.matched_knowledge_bases)} 个知识库"
            )
            
            # 发送 Agent 完成事件
            event_data = {
                "knowledge_count": len(knowledge_match.matched_knowledge_bases),
                "matched_knowledge_bases": [
                    {"name": kb.name, "description": kb.description}
                    for kb in knowledge_match.matched_knowledge_bases
                ] if knowledge_match.matched_knowledge_bases else []
            }
            await self._emit_progress(
                ProgressEvent.create_agent_complete_event(
                    AgentName.KNOWLEDGE_MATCHING,
                    event_data,
                    duration_ms
                )
            )
            return {"knowledge_match": knowledge_match}
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"知识库匹配失败：{e}")
            await self._emit_progress(
                ProgressEvent.create_agent_error_event(
                    AgentName.KNOWLEDGE_MATCHING,
                    str(e),
                    duration_ms
                )
            )
            return {"error": f"知识库匹配失败：{str(e)}"}

    async def _run_workflow_generation(self, state: WorkflowState) -> WorkflowState:
        """运行工作流生成 Agent"""
        logger.info("运行工作流生成")
        
        # 发送 Agent 开始事件
        start_time = time.time()
        await self._emit_progress(
            ProgressEvent.create_agent_start_event(AgentName.WORKFLOW_GENERATION)
        )
        
        try:
            # 检查是否有错误
            if state.get("error"):
                duration_ms = (time.time() - start_time) * 1000
                await self._emit_progress(
                    ProgressEvent.create_agent_error_event(
                        AgentName.WORKFLOW_GENERATION,
                        f"前置步骤错误：{state.get('error')}",
                        duration_ms
                    )
                )
                return state

            intent = state.get("intent")
            tool_plan = state.get("tool_plan")
            knowledge_match = state.get("knowledge_match")

            # 详细检查每个状态字段
            missing_states = []
            if not intent:
                missing_states.append("intent")
            if not tool_plan:
                missing_states.append("tool_plan")
            if not knowledge_match:
                missing_states.append("knowledge_match")
            
            if missing_states:
                error_msg = f"缺少必要的状态信息：{', '.join(missing_states)}"
                logger.error(error_msg)
                logger.error(f"当前状态：intent={intent is not None}, tool_plan={tool_plan is not None}, knowledge_match={knowledge_match is not None}")
                duration_ms = (time.time() - start_time) * 1000
                await self._emit_progress(
                    ProgressEvent.create_agent_error_event(
                        AgentName.WORKFLOW_GENERATION,
                        error_msg,
                        duration_ms
                    )
                )
                return {"error": error_msg}

            # 生成工作流
            workflow = await self.workflow_agent.generate_workflow(
                intent=intent, tool_plan=tool_plan, knowledge_match=knowledge_match
            )
            duration_ms = (time.time() - start_time) * 1000

            logger.info("工作流生成完成")
            
            # 发送 Agent 完成事件
            await self._emit_progress(
                ProgressEvent.create_agent_complete_event(
                    AgentName.WORKFLOW_GENERATION,
                    {"workflow_generated": True},
                    duration_ms
                )
            )
            
            return {"workflow": workflow}
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"工作流生成失败：{e}")
            await self._emit_progress(
                ProgressEvent.create_agent_error_event(
                    AgentName.WORKFLOW_GENERATION,
                    str(e),
                    duration_ms
                )
            )
            return {"error": f"工作流生成失败：{str(e)}"}

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
            return {
                "status": "success",
                "message": "工作流生成成功",
                "workflow": result.get("workflow"),
                "metadata": {
                    "intent": (
                        result.get("intent").model_dump(mode="json")
                        if result.get("intent")
                        else None
                    ),
                    "tools_count": len(
                        result.get("tool_plan", ToolPlan()).selected_tools
                    ),
                    "knowledge_count": len(
                        result.get(
                            "knowledge_match", KnowledgeMatch(required=False)
                        ).matched_knowledge_bases
                    ),
                },
            }
        except Exception as e:
            logger.error(f"工作流生成失败：{e}")
            return {"status": "error", "message": f"工作流生成失败：{str(e)}"}
    
    async def generate_with_progress(
        self,
        user_input: str,
        progress_callback: ProgressCallback
    ) -> Dict[str, Any]:
        """
        生成工作流并实时推送进度（流式版本）

        Args:
            user_input: 用户输入
            progress_callback: 进度回调函数

        Returns:
            生成的工作流
        """
        logger.info(f"收到用户输入（流式模式）：{user_input}")
        
        # 设置进度回调
        self.progress_callback = progress_callback
        
        # 发送开始事件
        await self._emit_progress(
            ProgressEvent.create_start_event(user_input)
        )
        
        # 调用普通生成方法（内部会触发进度回调）
        result = await self.generate(user_input)
        
        # 发送完成或错误事件
        if result.get("status") == "success":
            await self._emit_progress(
                ProgressEvent.create_complete_event(
                    result.get("workflow", {}),
                    result.get("metadata", {})
                )
            )
        else:
            await self._emit_progress(
                ProgressEvent.create_error_event(result.get("message", "未知错误"))
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
