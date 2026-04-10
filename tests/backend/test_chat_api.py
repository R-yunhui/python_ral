from fastapi.testclient import TestClient


def test_chat_contract_cn(client):
    resp = client.post(
        "/v1/chat",
        json={"user_id": "u1", "message": "我今天午饭30，顺便看下这周餐饮总额"},
        headers={"Authorization": "Bearer test-api-key"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "answer" in body
    assert "trace_id" in body
    assert body.get("lang") == "zh-CN"


def test_chat_rejects_without_auth(app):
    """无 API Key 应返回 401"""
    resp = TestClient(app).post("/v1/chat", json={"user_id": "u1", "message": "test"})
    assert resp.status_code == 401


def test_chat_rejects_with_wrong_auth(app):
    """错误 API Key 应返回 401"""
    resp = TestClient(app).post(
        "/v1/chat",
        json={"user_id": "u1", "message": "test"},
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert resp.status_code == 401
