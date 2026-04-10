import os
import pytest
from assistant.backend.config.settings import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("REPLY_API_KEY", "test-key")
    monkeypatch.setenv("SQLITE_PATH", ":memory:")
    s = Settings()
    assert s.reply_api_key == "test-key"


def test_settings_fails_without_required_keys(monkeypatch):
    # 清空 reply_api_key
    monkeypatch.setenv("REPLY_API_KEY", "")
    monkeypatch.setenv("SQLITE_PATH", "test.db")
    s = Settings()
    with pytest.raises(ValueError):
        s.validate()


def test_settings_defaults():
    s = Settings(reply_api_key="test", sqlite_path="test.db")
    assert s.log_level == "INFO"
    assert s.timezone == "Asia/Shanghai"
    assert s.intent_model == "qwen-turbo"
