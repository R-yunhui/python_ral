from assistant.backend.graph.chat_graph import GraphState


class ReplyService:
    """回复组装：结论 + 关键数字 + 建议动作，LLM 失败时走兜底模板"""

    FALLBACK_TEMPLATES = {
        "expense_record": "已记录：{amount}元 {category}，{description}。",
        "query_result": "本月 {category} 共支出 {total} 元。",
        "mixed": "已记录 {amount} 元 {category}。本月该类别共支出 {total} 元。",
    }

    def build_reply(self, state: GraphState) -> str:
        if state.get("answer"):
            return state["answer"]
        return self._build_fallback(state)

    def _build_fallback(self, state: GraphState) -> str:
        """兜底：模板拼接回复"""
        plan = state.get("plan")
        if plan and plan.query_intent and plan.store_intents:
            # 混合意图
            store = plan.store_intents[0]
            data = store.get("data", {})
            return self.FALLBACK_TEMPLATES["mixed"].format(
                amount=data.get("amount", "未知"),
                category=data.get("category", "未分类"),
                total=state.get("query_results", "暂无数据"),
            )
        elif plan and plan.store_intents:
            store = plan.store_intents[0]
            data = store.get("data", {})
            return self.FALLBACK_TEMPLATES["expense_record"].format(
                amount=data.get("amount", "未知"),
                category=data.get("category", "未分类"),
                description=data.get("description", ""),
            )
        return "好的，我已收到你的消息。"
