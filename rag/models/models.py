"""
数据库模型定义
"""

from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel
from enum import Enum


class DocumentStatus(str, Enum):
    """文档处理状态"""
    PENDING = "pending"  # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


class KnowledgeBase(SQLModel, table=True):
    """知识库表"""
    __tablename__ = "knowledge_bases"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=100, description="知识库名称")
    description: Optional[str] = Field(default=None, max_length=500, description="知识库描述")
    collection_name: str = Field(max_length=100, description="Qdrant 集合名称")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


class Document(SQLModel, table=True):
    """文档表"""
    __tablename__ = "documents"

    id: Optional[int] = Field(default=None, primary_key=True)
    kb_id: int = Field(foreign_key="knowledge_bases.id", index=True, description="所属知识库ID")
    filename: str = Field(max_length=255, description="文件名")
    file_path: str = Field(max_length=500, description="文件存储路径")
    file_size: int = Field(default=0, description="文件大小(字节)")
    file_type: str = Field(max_length=50, description="文件类型")
    status: DocumentStatus = Field(default=DocumentStatus.PENDING, description="处理状态")
    error_message: Optional[str] = Field(default=None, max_length=500, description="错误信息")
    created_at: datetime = Field(default_factory=datetime.now, description="上传时间")