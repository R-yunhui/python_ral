"""
SQLite 数据库配置
使用 SQLModel 作为 ORM
"""

from sqlmodel import SQLModel, create_engine, Session
from rag.config import DB_PATH, DB_URL

# 创建引擎
engine = create_engine(DB_URL, echo=False)


def get_engine():
    """获取数据库引擎"""
    return engine


def get_session():
    """获取数据库会话"""
    with Session(engine) as session:
        yield session


def init_db():
    """初始化数据库，创建所有表"""
    from .models import KnowledgeBase, Document
    from rag.config import print_storage_info

    SQLModel.metadata.create_all(engine)
    print_storage_info()