import json
import pytest
from unittest.mock import AsyncMock, patch
from assistant.backend.service.llm_orchestrator_service import plan_from_message
from assistant.backend.model.schemas import LLMPlan


@pytest.mark.asyncio
async def test_plan_contains_store_and_query():
    mock_client = AsyncMock()
    mock_client.invoke.return_value = json.dumps({
        "store_intents": [{"type": "structured", "data": {"amount": 45, "category": "交通"}}],
        "query_intent": {"type": "structured", "params": {"category": "交通", "period": "month"}},
        "reply_strategy": "concise_cn",
    })

    plan = await plan_from_message("今天打车45，另外帮我看本月交通超预算没有", mock_client)
    assert plan.query_intent is not None
    assert len(plan.store_intents) >= 1


@pytest.mark.asyncio
async def test_plan_empty_message_returns_no_store():
    """纯查询无存储意图"""
    mock_client = AsyncMock()
    mock_client.invoke.return_value = json.dumps({
        "store_intents": [],
        "query_intent": {"type": "structured", "params": {"date_range": "last_month"}},
        "reply_strategy": "concise_cn",
    })
    plan = await plan_from_message("帮我看看上个月总支出", mock_client)
    assert len(plan.store_intents) == 0
    assert plan.query_intent is not None


@pytest.mark.asyncio
async def test_plan_fallback_on_invalid_json():
    """LLM 返回非法 JSON 时降级到规则判断"""
    mock_client = AsyncMock()
    mock_client.invoke.return_value = "not valid json {{{"

    # 有查询关键词 -> 降级到查询
    plan = await plan_from_message("帮我看本月支出", mock_client)
    assert plan.query_intent is not None

    # 纯记账 -> 降级到存储
    plan2 = await plan_from_message("今天午餐30", mock_client)
    assert len(plan2.store_intents) >= 1
    assert plan2.query_intent is None
