"""数据库连接与表自动创建"""

import logging
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.orm import declarative_base

from config.config import Config

Base = declarative_base()
logger = logging.getLogger(__name__)

_engine: Optional[object] = None
_session_factory: Optional[sessionmaker] = None


def get_engine(config: Config):
    """根据 config 创建 SQLAlchemy engine（仅当 MySQL 已配置时有效）。"""
    global _engine
    if _engine is not None:
        return _engine
    if not config.is_mysql_configured():
        return None
    url = (
        f"mysql+pymysql://{config.mysql_user}:{config.mysql_password}"
        f"@{config.mysql_host}:{config.mysql_port}/{config.mysql_database}?charset=utf8mb4"
    )
    _engine = create_engine(url, pool_pre_ping=True, echo=False)
    logger.info("MySQL engine 已创建, host=%s, database=%s", config.mysql_host, config.mysql_database)
    return _engine


def get_session_factory(config: Config):
    """获取 Session 工厂；未配置 MySQL 时返回 None。"""
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
    根据配置创建表（若 MySQL 已配置）。在 FastAPI 启动时调用一次即可。
    Returns:
        True 表示已建表，False 表示未配置或失败
    """
    if not config.is_mysql_configured():
        return False
    try:
        from db import models  # noqa: F401 - 注册模型到 Base.metadata
        engine = get_engine(config)
        if engine is None:
            return False
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表已检查/创建完成")
        return True
    except Exception as e:
        logger.exception("初始化数据库表失败: %s", e)
        return False
