"""
API 请求和响应模型 (Pydantic Schemas)
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from rag.models.models import DocumentStatus


# ==================== 知识库 Schemas ====================

class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求"""
    name: str = Field(..., max_length=100, description="知识库名称")
    description: Optional[str] = Field(None, max_length=500, description="知识库描述")


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求"""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class KnowledgeBaseResponse(BaseModel):
    """知识库响应"""
    id: int
    name: str
    description: Optional[str]
    collection_name: str
    created_at: datetime
    document_count: int = Field(default=0, description="文档数量")

    class Config:
        from_attributes = True


class KnowledgeBaseListResponse(BaseModel):
    """知识库列表响应"""
    total: int
    items: List[KnowledgeBaseResponse]


# ==================== 文档 Schemas ====================

class DocumentResponse(BaseModel):
    """文档响应"""
    id: int
    kb_id: int
    filename: str
    file_path: str
    file_size: int
    file_type: str
    status: DocumentStatus
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    total: int
    items: List[DocumentResponse]


# ==================== 问答 Schemas ====================

class ChatRequest(BaseModel):
    """普通问答请求"""
    question: str = Field(..., min_length=1, max_length=2000, description="问题内容")
    stream: bool = Field(default=True, description="是否流式输出")


class RAGChatRequest(BaseModel):
    """知识库问答请求"""
    question: str = Field(..., min_length=1, max_length=2000, description="问题内容")
    kb_ids: List[int] = Field(..., min_items=1, description="知识库ID列表")
    top_k: int = Field(default=3, ge=1, le=10, description="检索文档数量")
    stream: bool = Field(default=True, description="是否流式输出")


class ChatResponse(BaseModel):
    """问答响应"""
    answer: str
    sources: Optional[List[dict]] = Field(default=None, description="来源文档")


# ==================== 通用响应 ====================

class MessageResponse(BaseModel):
    """通用消息响应"""
    success: bool
    message: str