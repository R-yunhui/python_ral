"""
意图识别专用对话历史存储（方案 B：按 session_id 单独存储，供 UserAgent 多轮澄清使用）

- 使用 LangChain BaseChatMessageHistory 接口，便于后续换持久化实现（如 Redis/Postgres）。
- 当前为进程内 InMemoryChatMessageHistory，重启后清空。
"""

import logging
from typing import Any, Dict

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# 进程内存储：session_id -> InMemoryChatMessageHistory（意图轮次专用）
_intent_history_store: Dict[str, "InMemoryIntentHistory"] = {}


class InMemoryIntentHistory(BaseChatMessageHistory, BaseModel):
    """意图澄清对话的进程内历史，实现 BaseChatMessageHistory 接口。"""

    messages: list[BaseMessage] = Field(default_factory=list, repr=False)

    def add_message(self, message: BaseMessage) -> None:
        self.messages.append(message)

    async def aget_messages(self) -> list[BaseMessage]:
        return self.messages

    def clear(self) -> None:
        self.messages.clear()


def get_intent_session_history(session_id: str) -> BaseChatMessageHistory:
    """
    按 session_id 获取意图澄清专用对话历史。
    同一 session 内：用户首轮、助理澄清、用户补充、…… 均写入此处，供意图节点续轮时加载。
    """
    if not session_id:
        session_id = "_default"
    if session_id not in _intent_history_store:
        _intent_history_store[session_id] = InMemoryIntentHistory()
    return _intent_history_store[session_id]


def add_intent_user_message(session_id: str, content: str) -> None:
    """写入一条用户消息（首轮或补充）。应在 API 收到请求时调用。"""
    if not session_id:
        return
    hist = get_intent_session_history(session_id)
    hist.add_user_message(content)
    logger.debug("意图历史写入 user message, session_id=%s, len=%s", session_id, len(hist.messages))


def add_intent_assistant_message(session_id: str, content: str) -> None:
    """写入一条助理消息（澄清问题等）。应在返回 needs_clarification 时调用。"""
    if not session_id:
        return
    hist = get_intent_session_history(session_id)
    hist.add_ai_message(content)
    logger.debug("意图历史写入 assistant message, session_id=%s, len=%s", session_id, len(hist.messages))


def add_intent_assistant_message_from_pending(session_id: str, pending: Dict[str, Any]) -> None:
    """将 needs_clarification 的 pending 序列化为一条助理消息并写入。"""
    text = pending.get("message", "") or "请补充以下信息，以便更准确生成工作流。"
    questions = pending.get("questions") or []
    if questions:
        text += "\n" + "\n".join(f"- {q}" for q in questions)
    add_intent_assistant_message(session_id, text)
