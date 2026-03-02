"""
知识库管理 API 路由
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from rag.models.database import get_session
from rag.api.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseListResponse,
    MessageResponse,
)
from rag.service.kb_service import kb_service
from rag.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/kb", tags=["知识库管理"])


@router.post("", response_model=KnowledgeBaseResponse, summary="创建知识库")
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    session: Session = Depends(get_session),
):
    """创建新的知识库"""
    logger.info(f"API: 创建知识库 - {data.name}")
    try:
        kb = kb_service.create_knowledge_base(session, data)
        logger.info(f"API: 知识库创建成功 - {kb.name} (ID: {kb.id})")
        return kb_service.get_kb_with_document_count(session, kb)
    except Exception as e:
        logger.error(f"API: 创建知识库失败 - {e}")
        raise HTTPException(status_code=500, detail=f"创建知识库失败：{str(e)}")


@router.get("", response_model=KnowledgeBaseListResponse, summary="获取知识库列表")
async def list_knowledge_bases(session: Session = Depends(get_session)):
    """获取所有知识库列表"""
    logger.debug("API: 获取知识库列表")
    kbs = kb_service.list_knowledge_bases(session)
    items = [kb_service.get_kb_with_document_count(session, kb) for kb in kbs]
    logger.info(f"API: 获取到 {len(items)} 个知识库")
    return KnowledgeBaseListResponse(total=len(items), items=items)


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse, summary="获取知识库详情")
async def get_knowledge_base(kb_id: int, session: Session = Depends(get_session)):
    """获取单个知识库详情"""
    logger.debug(f"API: 获取知识库详情 - ID={kb_id}")
    kb = kb_service.get_knowledge_base(session, kb_id)
    if not kb:
        logger.warning(f"API: 知识库不存在 - ID={kb_id}")
        raise HTTPException(status_code=404, detail="知识库不存在")
    return kb_service.get_kb_with_document_count(session, kb)


@router.delete("/{kb_id}", response_model=MessageResponse, summary="删除知识库")
async def delete_knowledge_base(kb_id: int, session: Session = Depends(get_session)):
    """删除知识库及其所有文档"""
    logger.info(f"API: 删除知识库 - ID={kb_id}")
    success = kb_service.delete_knowledge_base(session, kb_id)
    if not success:
        logger.warning(f"API: 知识库不存在，无法删除 - ID={kb_id}")
        raise HTTPException(status_code=404, detail="知识库不存在")
    logger.info(f"API: 知识库删除成功 - ID={kb_id}")
    return MessageResponse(success=True, message="知识库删除成功")