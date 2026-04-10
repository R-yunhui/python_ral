import asyncio
import logging
from typing import TypedDict, Optional, Any
from uuid import uuid4

from assistant.backend.model.schemas import LLMPlan
from assistant.backend.service.background_jobs import StoreJob, enqueue_store, store_worker
from assistant.backend.service.llm_orchestrator_service import plan_from_message
from assistant.backend.service.long_memory_service import LongMemoryService
from assistant.backend.service.query_service import QueryService, CategoryResolver
from assistant.backend.service.reply_service import ReplyService
from assistant.backend.service.short_memory_service import ShortMemoryService
from assistant.backend.service.structured_store_service import StructuredStoreService
from assistant.backend.utils.logging import trace_id_var


class GraphState(TypedDict):
    user_id: str
    message: str
    trace_id: str
    plan: Optional[LLMPlan]
    query_results: list[dict]
    long_memory_results: list[dict]
    answer: str
    errors: list[str]

logger = logging.getLogger(__name__)


class ChatGraph:
    """LangGraph 主流程编排"""

    def __init__(self, settings, engine, llm_client_intent, llm_client_reply):
        self._engine = engine
        self._store_service = StructuredStoreService(engine)
        self._query_service = QueryService(engine)
        self._category_resolver = CategoryResolver(engine)
        self._mem0_service = LongMemoryService(settings.mem0_api_key)
        self._reply_service = ReplyService()
        self._short_memory: dict[str, ShortMemoryService] = {}
        self._llm_intent = llm_client_intent
        self._llm_reply = llm_client_reply
        self._background_task: asyncio.Task | None = None

    def start_background_worker(self):
        """启动后台存储消费协程"""
        if self._background_task is None:
            self._background_task = asyncio.create_task(
                store_worker(self._store_service, self._mem0_service)
            )

    def _get_short_memory(self, user_id: str) -> ShortMemoryService:
        if user_id not in self._short_memory:
            self._short_memory[user_id] = ShortMemoryService()
        return self._short_memory[user_id]

    async def process(self, user_id: str, message: str) -> dict:
        """处理单条消息，返回回复字典"""
        trace_id = str(uuid4())
        trace_id_var.set(trace_id)

        state: GraphState = {
            "user_id": user_id,
            "message": message,
            "trace_id": trace_id,
            "plan": None,
            "query_results": [],
            "long_memory_results": [],
            "answer": "",
            "errors": [],
        }

        # Node 1: 意图识别
        state = await self._plan_node(state)

        # Node 2: 查询执行
        state = await self._query_node(state)

        # Node 3: 长期记忆检索
        state = await self._long_memory_node(state)

        # Node 4: 回复生成
        state = await self._reply_node(state)

        # Node 5: 异步存储派发（不阻塞）
        await self._dispatch_store_node(state)

        # 更新短期记忆
        sm = self._get_short_memory(user_id)
        sm.add_turn(message, state["answer"])
        if sm.needs_compression:
            sm.compress()

        return {
            "answer": state["answer"],
            "trace_id": state["trace_id"],
        }

    async def _plan_node(self, state: GraphState) -> GraphState:
        """意图识别节点"""
        try:
            plan = await plan_from_message(state["message"], self._llm_intent)
            state["plan"] = plan
        except Exception as e:
            logger.error(f"plan_node error: {e}")
            state["errors"].append(f"plan_node: {e}")
            state["plan"] = LLMPlan()
        return state

    async def _query_node(self, state: GraphState) -> GraphState:
        """查询执行节点"""
        plan = state.get("plan")
        if not plan or not plan.query_intent:
            return state
        try:
            query = plan.query_intent
            params = query.get("params", {})
            # 简单查询：按类别+时间范围汇总
            if "category" in params:
                from assistant.backend.utils.time_range import parse_date_range
                date_range = params.get("date_range", "今天")
                start, end = parse_date_range(date_range)
                total = self._query_service.sum_by_category(
                    state["user_id"], params["category"], start, end
                )
                state["query_results"] = [{"category": params["category"], "total": total, "date_range": date_range}]
        except Exception as e:
            logger.error(f"query_node error: {e}")
            state["errors"].append(f"query_node: {e}")
        return state

    async def _long_memory_node(self, state: GraphState) -> GraphState:
        """长期记忆检索节点"""
        try:
            results = await self._mem0_service.search(state["user_id"], state["message"])
            state["long_memory_results"] = results
        except Exception as e:
            logger.warning(f"long_memory_node error (non-fatal): {e}")
            state["long_memory_results"] = []
        return state

    async def _reply_node(self, state: GraphState) -> GraphState:
        """回复生成节点"""
        try:
            answer = self._reply_service.build_reply(state)
            state["answer"] = answer
        except Exception as e:
            logger.error(f"reply_node error: {e}")
            state["answer"] = "抱歉，处理你的请求时出现了问题。"
            state["errors"].append(f"reply_node: {e}")
        return state

    async def _dispatch_store_node(self, state: GraphState) -> None:
        """异步存储派发节点"""
        plan = state.get("plan")
        if not plan or not plan.store_intents:
            return
        try:
            for intent in plan.store_intents:
                job = StoreJob(
                    user_id=state["user_id"],
                    data=intent,
                    trace_id=state["trace_id"],
                )
                await enqueue_store(job)
        except Exception as e:
            logger.error(f"dispatch_store_node error: {e}")
            state["errors"].append(f"dispatch_store_node: {e}")
