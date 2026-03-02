"""
文档管理 API 路由
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlmodel import Session

from rag.models.database import get_session
from rag.models.models import KnowledgeBase
from rag.api.schemas import (
    DocumentResponse,
    DocumentListResponse,
    MessageResponse,
)
from rag.service.kb_service import kb_service
from rag.service.document_service import document_service
from rag.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/kb", tags=["文档管理"])


def process_document_task(doc_id: int, collection_name: str):
    """后台任务：处理文档"""
    logger.info(f"后台任务：开始处理文档 - ID={doc_id}")
    from rag.models.database import engine
    from sqlmodel import Session as DBSession
    
    with DBSession(engine) as session:
        doc = document_service.get_document(session, doc_id)
        if doc:
            success = document_service.process_document(session, doc, collection_name)
            if success:
                logger.info(f"后台任务：文档处理成功 - ID={doc_id}")
            else:
                logger.error(f"后台任务：文档处理失败 - ID={doc_id}")
        else:
            logger.error(f"后台任务：文档不存在 - ID={doc_id}")


@router.post(
    "/{kb_id}/documents",
    response_model=DocumentResponse,
    summary="上传文档到知识库",
)
async def upload_document(
    kb_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """上传文档到指定知识库"""
    logger.info(f"API: 上传文档 - kb_id={kb_id}, filename={file.filename}")
    try:
        # 检查知识库是否存在
        kb = kb_service.get_knowledge_base(session, kb_id)
        if not kb:
            logger.warning(f"API: 知识库不存在 - kb_id={kb_id}")
            raise HTTPException(status_code=404, detail="知识库不存在")

        # 验证文件类型
        if not document_service.validate_file(file.filename):
            logger.warning(f"API: 不支持的文件类型 - {file.filename}")
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型，支持：txt, md, pdf, docx",
            )

        # 读取文件内容（异步）
        content = await file.read()
        logger.debug(f"API: 文件读取完成 - size={len(content)} bytes")

        # 保存文件
        file_path = document_service.save_upload_file(kb_id, file.filename, content)

        # 创建文档记录
        doc = document_service.create_document_record(
            session=session,
            kb_id=kb_id,
            filename=file.filename,
            file_path=file_path,
            file_size=len(content),
        )

        # 后台处理文档
        background_tasks.add_task(
            process_document_task,
            doc.id,
            kb.collection_name,
        )
        logger.info(f"API: 文档上传成功 - {doc.filename} (ID: {doc.id})")

        return doc

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: 上传文档失败 - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"上传文档失败：{str(e)}")


@router.get(
    "/{kb_id}/documents",
    response_model=DocumentListResponse,
    summary="获取知识库文档列表",
)
async def list_documents(kb_id: int, session: Session = Depends(get_session)):
    """获取指定知识库的文档列表"""
    logger.debug(f"API: 获取文档列表 - kb_id={kb_id}")
    kb = kb_service.get_knowledge_base(session, kb_id)
    if not kb:
        logger.warning(f"API: 知识库不存在 - kb_id={kb_id}")
        raise HTTPException(status_code=404, detail="知识库不存在")

    documents = document_service.list_documents(session, kb_id)
    items = [DocumentResponse.model_validate(doc) for doc in documents]
    logger.info(f"API: 获取到 {len(items)} 个文档")
    return DocumentListResponse(total=len(items), items=items)


@router.delete(
    "/documents/{doc_id}",
    response_model=MessageResponse,
    summary="删除文档",
)
async def delete_document(doc_id: int, session: Session = Depends(get_session)):
    """删除指定文档"""
    logger.info(f"API: 删除文档 - ID={doc_id}")
    success = document_service.delete_document(session, doc_id)
    if not success:
        logger.warning(f"API: 文档不存在 - ID={doc_id}")
        raise HTTPException(status_code=404, detail="文档不存在")
    logger.info(f"API: 文档删除成功 - ID={doc_id}")
    return MessageResponse(success=True, message="文档删除成功")