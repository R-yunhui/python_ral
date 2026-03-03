"""
Qdrant 客户端单例
确保整个应用只使用一个 Qdrant 客户端实例

注意：Qdrant 本地存储模式不支持同步和异步客户端同时访问。
我们统一使用同步客户端，异步检索时会自动处理。
"""

from qdrant_client import QdrantClient
from rag.config import QDRANT_PATH
from rag.utils.logger import get_logger

logger = get_logger(__name__)

# 全局 Qdrant 同步客户端单例
_qdrant_client = None


def get_qdrant_client() -> QdrantClient:
    """获取 Qdrant 同步客户端单例"""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(path=QDRANT_PATH)
        logger.info("Qdrant 同步客户端初始化完成")
    return _qdrant_client


def get_qdrant_async_client() -> QdrantClient:
    """获取 Qdrant 客户端（兼容旧代码，实际返回同步客户端）"""
    # 注意：Qdrant 同步客户端也支持异步操作！
    # QdrantClient 的异步方法会在内部使用线程池执行
    return get_qdrant_client()
