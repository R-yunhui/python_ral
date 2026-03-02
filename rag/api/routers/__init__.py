"""
路由模块
"""

from .knowledge_base import router as kb_router
from .document import router as doc_router
from .chat import router as chat_router

__all__ = ["kb_router", "doc_router", "chat_router"]