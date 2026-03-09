"""数据库连接与表自动创建

支持两种后端：
- MySQL：配置了 MYSQL_HOST / MYSQL_USER / MYSQL_DATABASE 时使用
- SQLite：未配置 MySQL 时自动 fallback，零配置开箱即用
"""

import logging
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

from config.config import Config

Base = declarative_base()
logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DEFAULT_SQLITE_PATH = _DATA_DIR / "bisheng_generator.db"

_engine: Optional[object] = None
_session_factory: Optional[sessionmaker] = None


def _build_engine_url(config: Config) -> str:
    if config.is_mysql_configured():
        return (
            f"mysql+pymysql://{config.mysql_user}:{config.mysql_password}"
            f"@{config.mysql_host}:{config.mysql_port}/{config.mysql_database}"
            f"?charset=utf8mb4"
        )
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{_DEFAULT_SQLITE_PATH}"


def get_engine(config: Config):
    """根据 config 创建 SQLAlchemy engine。MySQL 优先，未配置则 fallback 到 SQLite。"""
    global _engine
    if _engine is not None:
        return _engine

    if not config.is_db_enabled():
        logger.info("数据库已禁用（DB_ENABLED=false）")
        return None

    url = _build_engine_url(config)
    is_sqlite = url.startswith("sqlite")

    _engine = create_engine(
        url,
        pool_pre_ping=not is_sqlite,
        echo=False,
    )

    if is_sqlite:
        @event.listens_for(_engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

        logger.info("SQLite engine 已创建, path=%s", _DEFAULT_SQLITE_PATH)
    else:
        logger.info(
            "MySQL engine 已创建, host=%s, database=%s",
            config.mysql_host, config.mysql_database,
        )

    return _engine


def get_session_factory(config: Config):
    """获取 Session 工厂。"""
    global _session_factory
    if _session_factory is not None:
        return _session_factory
    engine = get_engine(config)
    if engine is None:
        return None
    _session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _session_factory


def init_db(config: Config) -> bool:
    """
    根据配置创建表。在 FastAPI 启动时调用一次即可。
    Returns:
        True 表示已建表，False 表示未启用或失败
    """
    if not config.is_db_enabled():
        return False
    try:
        from db import models  # noqa: F401
        engine = get_engine(config)
        if engine is None:
            return False
        Base.metadata.create_all(bind=engine)
        backend = "MySQL" if config.is_mysql_configured() else "SQLite"
        logger.info("数据库表已检查/创建完成（%s）", backend)
        return True
    except Exception as e:
        logger.exception("初始化数据库表失败: %s", e)
        return False
