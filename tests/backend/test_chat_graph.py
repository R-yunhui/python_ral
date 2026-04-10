"""LangGraph 端到端集成测试"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlmodel import create_engine
from assistant.backend.config.settings import Settings
from assistant.backend.app import create_app
from assistant.backend.graph.chat_graph import ChatGraph, GraphState
from assistant.backend.model.sql_models import init_db


@pytest.fixture()
def engine():
    eng = create_engine("sqlite:///:memory:")
    init_db(eng)
    return eng


def _make_graph(engine):
    """创建测试用 ChatGraph"""
    mock_intent = AsyncMock()
    mock_intent.invoke.return_value = '{"store_intents": [{"type": "structured", "data": {"amount": 30, "category": "餐饮", "description": "午餐"}}], "query_intent": null, "reply_strategy": "concise_cn"}'

    mock_reply = AsyncMock()
    return ChatGraph(
        settings=Settings(reply_api_key="test", sqlite_path=":memory:", api_key="test-key"),
        engine=engine,
        llm_client_intent=mock_intent,
        llm_client_reply=mock_reply,
    )


@pytest.mark.asyncio
async def test_process_store_only(engine):
    """纯记账消息"""
    graph = _make_graph(engine)
    result = await graph.process("u1", "今天午饭30块")
    assert "answer" in result
    assert "trace_id" in result


@pytest.mark.asyncio
async def test_process_mixed_intent(engine):
    """混合意图消息"""
    mock_intent = AsyncMock()
    mock_intent.invoke.return_value = '{"store_intents": [{"type": "structured", "data": {"amount": 30, "category": "餐饮"}}], "query_intent": {"type": "structured", "params": {"category": "餐饮", "date_range": "这个月"}}, "reply_strategy": "concise_cn"}'
    mock_reply = AsyncMock()

    from assistant.backend.config.settings import Settings
    graph = ChatGraph(
        settings=Settings(reply_api_key="test", sqlite_path=":memory:", api_key="test-key"),
        engine=engine,
        llm_client_intent=mock_intent,
        llm_client_reply=mock_reply,
    )
    result = await graph.process("u1", "午饭30块，帮我看看这个月餐饮花了多少")
    assert "answer" in result
    assert "trace_id" in result
    assert graph._short_memory["u1"] is not None
