"""
用户意图理解 Agent（简化版）

职责：
1. 理解用户需求
2. 判断需要哪些功能（工具/知识库/条件/报告）
3. 生成 EnhancedIntent
4. 判断是否需要向用户澄清（保守原则）

使用普通 LLM 调用 + 从返回文本解析 JSON，兼容不支持结构化输出的模型。
"""

import logging
from typing import Dict, List, Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from pydantic import ValidationError
from models.intent import EnhancedIntent, IntentParseResult
from core.prompt_loader import get_prompt_loader
from core.intent_history import get_intent_session_history
from core.utils import extract_json

logger = logging.getLogger(__name__)


class UserAgent:
    """用户意图理解专家"""

    def __init__(
        self,
        llm: BaseChatModel,
        prompts_dir: Optional[str] = None,
    ):
        self.llm = llm
        loader = get_prompt_loader(prompts_dir)
        system = loader.get("intent", "system")
        human_single = loader.get("intent", "human_single")
        human_resume = loader.get("intent", "human_resume")

        self.prompt_single = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                ("human", human_single),
            ]
        )

        self.prompt_with_history = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                MessagesPlaceholder("chat_history"),
                ("human", human_resume),
            ]
        )

    async def understand(
        self,
        user_input: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None,
    ) -> EnhancedIntent:
        """
        理解用户意图

        Args:
            user_input: 用户输入
            chat_history: 多轮对话历史，格式 [{"role": "user"|"assistant", "content": "..."}]（可选，与 session_id 二选一）
            session_id: 会话 ID；提供时从意图历史存储加载 chat_history（方案 B），优先于 chat_history 参数

        Returns:
            EnhancedIntent: 结构化的意图描述
        """
        logger.info("意图理解开始，user_input=%s", (user_input or "")[:80])

        messages: Optional[List] = None
        if session_id:
            hist = get_intent_session_history(session_id)
            try:
                msgs = await hist.aget_messages()
            except Exception:
                msgs = getattr(hist, "messages", []) or []
            if msgs:
                messages = list(msgs)
        if messages is None and chat_history:
            messages = []
            for m in chat_history:
                if m.get("role") == "user":
                    messages.append(HumanMessage(content=m.get("content", "")))
                else:
                    messages.append(AIMessage(content=m.get("content", "")))

        if messages:
            chain = self.prompt_with_history | self.llm | StrOutputParser()
            content = await chain.ainvoke(
                {
                    "chat_history": messages,
                    "user_input": user_input,
                }
            )
        else:
            chain = self.prompt_single | self.llm | StrOutputParser()
            content = await chain.ainvoke({"user_input": user_input})

        raw = (content or "").strip()
        data = extract_json(raw)
        if not data:
            raise ValueError(
                "意图理解返回内容无法解析为 JSON，请确保模型按 prompt 要求输出 JSON。"
                f" 返回预览: {raw[:200]!r}"
            )
        try:
            parsed = IntentParseResult.model_validate(data)
        except ValidationError as ve:
            raise ValueError(
                f"意图理解 JSON 字段校验失败: {ve}. 返回预览: {raw[:200]!r}"
            ) from ve
        logger.info("意图理解完成，parsed=%s", parsed)

        # 从解析结果构建 EnhancedIntent（注入 original_input）
        intent = EnhancedIntent(
            original_input=user_input or "",
            rewritten_input=parsed.rewritten_input or user_input or "",
            needs_tool=parsed.needs_tool,
            needs_knowledge=parsed.needs_knowledge,
            needs_clarification=parsed.needs_clarification,
            clarification_questions=parsed.clarification_questions or [],
            complexity_hint=parsed.complexity_hint,
            multi_turn=parsed.multi_turn,
        )

        # 有 chat_history（含从 session_id 加载的历史）时强制不再澄清
        if messages:
            intent.needs_clarification = False
            intent.clarification_questions = []
        # 续轮合并输入（含「【用户补充】」）视为已澄清，不再追问（兼容未用历史时的合并逻辑）
        if "【用户补充】" in (user_input or ""):
            intent.needs_clarification = False
            intent.clarification_questions = []

        features = []
        if intent.needs_tool:
            features.append("工具调用")
        if intent.needs_knowledge:
            features.append("知识库检索")
        logger.info(
            "意图理解完成，workflow_type=%s, features=%s, needs_clarification=%s, rewritten_input=%s",
            intent.get_workflow_type(),
            features,
            intent.needs_clarification,
            intent.rewritten_input,
        )
        return intent
