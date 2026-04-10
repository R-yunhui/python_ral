import pytest
from fastapi.testclient import TestClient
from assistant.backend.config.settings import Settings
from assistant.backend.app import create_app


@pytest.fixture
def test_settings():
    """测试用配置，使用内存数据库"""
    return Settings(
        reply_api_key="test-key",
        sqlite_path="sqlite:///file:testdb?mode=memory&cache=shared",
        api_key="test-api-key",
    )


@pytest.fixture
def app(test_settings):
    """返回测试用 FastAPI 应用"""
    return create_app(test_settings, test_mode=True)


@pytest.fixture
def client(app):
    return TestClient(app)
