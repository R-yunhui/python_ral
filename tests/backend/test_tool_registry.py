import pytest
from assistant.backend.service.tool_registry_service import ToolRegistry, ToolNotFoundError


def test_unregistered_tool_is_rejected():
    with pytest.raises(ToolNotFoundError):
        ToolRegistry.validate_tool_call("delete_database", {})


def test_registered_tool_passes_validation():
    assert ToolRegistry.validate_tool_call("structured_query", {}) is True
    assert ToolRegistry.validate_tool_call("structured_store", {}) is True
    assert ToolRegistry.validate_tool_call("resolve_category", {}) is True
    assert ToolRegistry.validate_tool_call("long_memory", {}) is True


def test_get_tool_returns_definition():
    tool = ToolRegistry.get_tool("structured_query")
    assert tool is not None
    assert tool.name == "structured_query"
    assert tool.is_write is False


def test_get_nonexistent_tool_returns_none():
    assert ToolRegistry.get_tool("nonexistent") is None
