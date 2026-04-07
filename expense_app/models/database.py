"""
数据库配置模块
提供 SQLAlchemy 数据库连接和会话管理
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging

# 配置日志
logger = logging.getLogger(__name__)

# SQLite 数据库路径
DATABASE_URL = "sqlite:///./expense_app.db"

# 创建数据库引擎
# check_same_thread=False 允许在多线程环境中使用 SQLite
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False  # 设置为 True 可打印 SQL 语句
)

# 创建会话工厂
# autocommit=False: 不自动提交事务
# autoflush=False: 不自动刷新
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明模型基类
# 所有 ORM 模型都应继承此类
Base = declarative_base()


def get_db():
    """
    数据库会话依赖注入函数

    Yields:
        Session: SQLAlchemy 数据库会话

    Note:
        使用 try/finally 确保会话在使用后正确关闭
        用于 FastAPI 的 Depends() 依赖注入
    """
    db = SessionLocal()
    try:
        logger.debug("Database session opened")
        yield db
    finally:
        db.close()
        logger.debug("Database session closed")


def init_db():
    """
    初始化数据库，创建所有表

    Note:
        调用此函数会创建所有继承自 Base 的模型对应的表
    """
    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialization complete")
