"""
Qdrant 客户端单例
确保整个应用只使用一个 Qdrant 客户端实例
"""

from qdrant_client import QdrantClient
from rag.config import QDRANT_PATH

# 全局 Qdrant 客户端单例
_qdrant_client = None


def get_qdrant_client() -> QdrantClient:
    """获取 Qdrant 客户端单例"""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(path=QDRANT_PATH)
    return _qdrant_client
