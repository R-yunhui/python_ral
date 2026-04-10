from assistant.backend.service.reply_service import ReplyService
from assistant.backend.model.schemas import LLMPlan


def test_reply_service_with_answer():
    svc = ReplyService()
    state = {"answer": "直接返回已有答案", "plan": None}
    assert svc.build_reply(state) == "直接返回已有答案"


def test_reply_service_fallback_mixed():
    svc = ReplyService()
    state = {
        "answer": "",
        "plan": LLMPlan(
            store_intents=[{"type": "structured", "data": {"amount": 30, "category": "餐饮", "description": "午餐"}}],
            query_intent={"type": "structured"},
            reply_strategy="concise_cn",
        ),
        "query_results": [{"total": 500}],
    }
    reply = svc.build_reply(state)
    assert "30" in reply
    assert "餐饮" in reply


def test_reply_service_fallback_expense():
    svc = ReplyService()
    state = {
        "answer": "",
        "plan": LLMPlan(
            store_intents=[{"type": "structured", "data": {"amount": 45, "category": "交通", "description": "打车"}}],
            query_intent=None,
            reply_strategy="concise_cn",
        ),
    }
    reply = svc.build_reply(state)
    assert "45" in reply
    assert "交通" in reply


def test_reply_service_default():
    svc = ReplyService()
    state = {"answer": "", "plan": LLMPlan()}
    reply = svc.build_reply(state)
    assert len(reply) > 0
