"""LangGraph 编排模块 - 包含 BaseChatModel 初始化和工作流编排"""

from typing import Optional, Dict, Any, TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from langgraph.graph import StateGraph, START, END
import logging

from config.config import Config, config
from models.intent import EnhancedIntent
from agents.user_agent import UserAgent
from agents.tool_agent import ToolAgent, ToolPlan
from agents.knowledge_agent import KnowledgeAgent, KnowledgeMatch
from agents.workflow_agent import WorkflowAgent

logger = logging.getLogger(__name__)


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

    def __init__(self, config_obj: Optional[Config] = None):
        """
        初始化编排器

        Args:
            config_obj: Config 配置对象，如果不传则使用全局配置
        """
        # 保存配置对象
        self.config = config_obj or config

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
        try:
            intent = await self.user_agent.understand(state["user_input"])
            logger.info(f"意图理解完成：{intent.get_workflow_type()}")
            return {"intent": intent}
        except Exception as e:
            logger.error(f"意图理解失败：{e}")
            return {"error": f"意图理解失败：{str(e)}"}

    async def _run_tool_selection(self, state: WorkflowState) -> WorkflowState:
        """运行工具选择 Agent"""
        logger.info("运行工具选择")
        try:
            intent = state.get("intent")
            if not intent:
                return {"tool_plan": ToolPlan()}

            tool_plan = await self.tool_agent.select_tools(intent)
            logger.info(f"工具选择完成：选中 {len(tool_plan.selected_tools)} 个工具")
            return {"tool_plan": tool_plan}
        except Exception as e:
            logger.error(f"工具选择失败：{e}")
            return {"error": f"工具选择失败：{str(e)}"}

    async def _run_knowledge_matching(self, state: WorkflowState) -> WorkflowState:
        """运行知识库匹配 Agent"""
        logger.info("运行知识库匹配")
        try:
            intent = state.get("intent")
            if not intent:
                return {"knowledge_match": KnowledgeMatch(required=False)}

            knowledge_match = await self.knowledge_agent.match_knowledge(intent)
            logger.info(
                f"知识库匹配完成：匹配到 {len(knowledge_match.matched_knowledge_bases)} 个知识库"
            )
            return {"knowledge_match": knowledge_match}
        except Exception as e:
            logger.error(f"知识库匹配失败：{e}")
            return {"error": f"知识库匹配失败：{str(e)}"}

    async def _run_workflow_generation(self, state: WorkflowState) -> WorkflowState:
        """运行工作流生成 Agent"""
        logger.info("运行工作流生成")
        try:
            # 检查是否有错误
            if state.get("error"):
                return state

            intent = state.get("intent")
            tool_plan = state.get("tool_plan")
            knowledge_match = state.get("knowledge_match")

            if not all([intent, tool_plan, knowledge_match]):
                return {"error": "缺少必要的状态信息"}

            # 生成工作流
            workflow = await self.workflow_agent.generate_workflow(
                intent=intent, tool_plan=tool_plan, knowledge_match=knowledge_match
            )

            logger.info("工作流生成完成")
            return {"workflow": workflow}
        except Exception as e:
            logger.error(f"工作流生成失败：{e}")
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
