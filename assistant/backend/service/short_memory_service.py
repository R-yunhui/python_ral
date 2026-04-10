import logging

logger = logging.getLogger(__name__)


class ShortMemoryService:
    """短期记忆压缩：对话轮次计数 + 摘要压缩"""

    def __init__(self, max_turns: int = 20, summary_threshold: int = 30):
        self._max_turns = max_turns
        self._summary_threshold = summary_threshold
        self._history: list[dict] = []
        self._summary: str = ""

    def add_turn(self, user_msg: str, assistant_msg: str):
        self._history.append({"user": user_msg, "assistant": assistant_msg})

    @property
    def needs_compression(self) -> bool:
        return len(self._history) >= self._summary_threshold

    def compress(self, llm_client=None) -> str:
        """压缩对话历史，保留最近 max_turns 条"""
        if len(self._history) <= self._max_turns:
            return self._summary

        # 生成摘要
        old_messages = self._history[:-self._max_turns]
        summary_text = self._generate_summary(old_messages, llm_client)
        self._summary += summary_text
        self._history = self._history[-self._max_turns:]
        return self._summary

    def _generate_summary(self, messages: list[dict], llm_client=None) -> str:
        """生成对话摘要"""
        if llm_client is None:
            # 简单拼接兜底
            return f"[{len(messages)} 轮对话摘要]\n"

        try:
            import asyncio
            prompt = f"请用中文总结以下对话的关键信息：\n{messages}"
            summary = asyncio.get_event_loop().run_until_complete(
                llm_client.invoke(prompt, max_tokens=200)
            )
            return f"[摘要] {summary}\n"
        except Exception as e:
            logger.warning(f"Memory compression failed: {e}")
            return f"[{len(messages)} 轮对话摘要]\n"

    def get_context(self) -> list[dict]:
        """获取当前上下文（摘要 + 最近对话）"""
        context = []
        if self._summary:
            context.append({"role": "system", "content": self._summary})
        for turn in self._history:
            context.append({"role": "user", "content": turn["user"]})
            context.append({"role": "assistant", "content": turn["assistant"]})
        return context
