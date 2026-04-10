import pytest
from assistant.backend.service.long_memory_service import LongMemoryService


def test_long_memory_without_mem0():
    """mem0 不可用时返回空列表，不抛异常"""
    svc = LongMemoryService(api_key="invalid")
    assert svc._available is False

    import asyncio
    result = asyncio.get_event_loop().run_until_complete(svc.search("u1", "test"))
    assert result == []

    add_result = asyncio.get_event_loop().run_until_complete(svc.add("u1", {"test": "data"}))
    assert add_result is False
