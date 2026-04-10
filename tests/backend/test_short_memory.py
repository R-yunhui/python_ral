import pytest
from assistant.backend.service.short_memory_service import ShortMemoryService


def test_needs_compression_below_threshold():
    svc = ShortMemoryService(max_turns=20, summary_threshold=30)
    for i in range(10):
        svc.add_turn(f"用户消息{i}", f"助手回复{i}")
    assert svc.needs_compression is False


def test_needs_compression_above_threshold():
    svc = ShortMemoryService(max_turns=20, summary_threshold=30)
    for i in range(30):
        svc.add_turn(f"用户消息{i}", f"助手回复{i}")
    assert svc.needs_compression is True


def test_compression_preserves_recent_turns():
    svc = ShortMemoryService(max_turns=20, summary_threshold=30)
    for i in range(35):
        svc.add_turn(f"用户消息{i}", f"助手回复{i}")
    svc.compress()
    assert len(svc._history) == 20  # 保留最近 20 条


def test_context_includes_summary_and_history():
    svc = ShortMemoryService(max_turns=5, summary_threshold=10)
    svc._summary = "[摘要] 用户讨论了餐饮预算"
    svc.add_turn("用户消息1", "助手回复1")
    context = svc.get_context()
    assert len(context) == 3  # system + user + assistant


def test_short_memory_creation():
    svc = ShortMemoryService()
    assert svc._max_turns == 20
    assert svc._summary_threshold == 30
    assert svc._summary == ""
    assert svc._history == []
