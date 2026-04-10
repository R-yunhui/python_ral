from fastapi import FastAPI


def register_health(app: FastAPI):
    """注册健康检查端点"""
    @app.get("/health")
    def health():
        return {"status": "ok"}
