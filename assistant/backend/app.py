from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import SQLModel, create_engine
from sqlalchemy import text
from assistant.backend.api.chat import router as chat_router, init_graph
from assistant.backend.api.health import register_health
from assistant.backend.middleware.auth import set_api_key

def create_app(settings=None, test_mode: bool = False) -> FastAPI:
    """FastAPI 工厂函数"""
    from assistant.backend.config.settings import Settings, settings as default_settings

    if settings is None:
        settings = default_settings

    # 设置 API Key
    set_api_key(settings.api_key)

    # 只在非测试模式下校验（需要真实配置）
    if not test_mode:
        settings.validate()

    # 数据库引擎
    if test_mode:
        db_url = settings.sqlite_path
    else:
        db_url = f"sqlite:///{settings.sqlite_path}"

    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )

    # 启用 WAL 模式 + 写入超时
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA busy_timeout=5000"))

    SQLModel.metadata.create_all(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 启动 LangGraph
        from assistant.backend.graph.chat_graph import ChatGraph
        from assistant.backend.service.llm_client import LLMClient

        graph = ChatGraph(
            settings=settings,
            engine=engine,
            llm_client_intent=LLMClient(settings.intent_model, settings.intent_api_key, settings.intent_base_url),
            llm_client_reply=LLMClient(settings.reply_model, settings.reply_api_key, settings.reply_base_url),
        )
        graph.start_background_worker()
        init_graph(graph)
        yield

    app = FastAPI(lifespan=lifespan)
    app.include_router(chat_router, prefix="/v1")
    register_health(app)
    return app


# 全局默认实例（用于 uvicorn 启动）
from assistant.backend.config.settings import settings as _default_settings
try:
    app = create_app(_default_settings)
except (ValueError, FileNotFoundError):
    app = None  # .env 缺少配置时设为 None，测试不受影响
