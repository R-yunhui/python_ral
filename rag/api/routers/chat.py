"""
问答 API 路由
仅支持流式问答
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from rag.models.database import get_session
from rag.api.schemas import ChatRequest, RAGChatRequest
from rag.service.kb_service import kb_service
from rag.service.chat_service import chat_service
from rag.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["问答"])


@router.post("", summary="流式普通问答")
async def chat(request: ChatRequest):
    """普通问答（流式）"""
    logger.info(f"API: 流式普通问答")
    try:
        return StreamingResponse(
            chat_service.chat_astream(request.question),
            media_type="text/event-stream",
        )
    except Exception as e:
        logger.error(f"API: 流式问答失败 - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"问答失败：{str(e)}")


@router.post("/rag", summary="流式知识库问答")
async def rag_chat(
    request: RAGChatRequest,
    session: Session = Depends(get_session),
):
    """RAG 知识库问答（流式）"""
    logger.info(f"API: RAG 流式问答 - kb_ids={request.kb_ids}")
    try:
        # 获取知识库集合名称
        collection_names = []
        for kb_id in request.kb_ids:
            kb = kb_service.get_knowledge_base(session, kb_id)
            if kb:
                collection_names.append(kb.collection_name)
            else:
                logger.warning(f"API: 知识库不存在 - ID={kb_id}")

        if not collection_names:
            logger.warning("API: 未找到有效的知识库")
            raise HTTPException(status_code=400, detail="未找到有效的知识库")

        logger.debug(f"API: 使用集合 - {collection_names}")

        return StreamingResponse(
            chat_service.rag_chat_astream(
                question=request.question,
                collection_names=collection_names,
                top_k=request.top_k,
            ),
            media_type="text/event-stream",
        )
    except Exception as e:
        logger.error(f"API: RAG 流式问答失败 - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"问答失败：{str(e)}")
