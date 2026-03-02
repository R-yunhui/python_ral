"""
问答 API 路由
支持普通问答和 RAG 知识库问答
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from rag.models.database import get_session
from rag.api.schemas import ChatRequest, RAGChatRequest, ChatResponse, MessageResponse
from rag.service.kb_service import kb_service
from rag.service.chat_service import chat_service
from rag.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["问答"])


@router.post("", response_model=ChatResponse, summary="普通问答")
async def chat(request: ChatRequest):
    """普通问答，直接调用 LLM"""
    logger.info(f"API: 普通问答 - stream={request.stream}")
    try:
        if request.stream:
            # 流式响应
            logger.debug("API: 使用流式响应")
            return StreamingResponse(
                chat_service.chat_stream(request.question),
                media_type="text/event-stream",
            )
        else:
            # 非流式响应
            logger.debug("API: 使用非流式响应")
            answer = chat_service.chat(request.question)
            logger.info("API: 普通问答完成")
            return ChatResponse(answer=answer)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: 普通问答失败 - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"问答失败：{str(e)}")


@router.post("/rag", summary="知识库问答")
async def rag_chat(
    request: RAGChatRequest,
    session: Session = Depends(get_session),
):
    """RAG 知识库问答"""
    logger.info(f"API: RAG 问答 - kb_ids={request.kb_ids}, stream={request.stream}")
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

        if request.stream:
            # 流式响应
            logger.debug("API: 使用流式响应")
            return StreamingResponse(
                chat_service.rag_chat_stream(
                    question=request.question,
                    collection_names=collection_names,
                    top_k=request.top_k,
                ),
                media_type="text/event-stream",
            )
        else:
            # 非流式响应
            logger.debug("API: 使用非流式响应")
            answer = chat_service.rag_chat(
                question=request.question,
                collection_names=collection_names,
                top_k=request.top_k,
            )
            logger.info("API: RAG 问答完成")
            return ChatResponse(answer=answer)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: RAG 问答失败 - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"问答失败：{str(e)}")


@router.post("/stream", summary="流式普通问答")
async def chat_stream(request: ChatRequest):
    """流式普通问答"""
    logger.info(f"API: 流式普通问答")
    try:
        return StreamingResponse(
            chat_service.chat_stream(request.question),
            media_type="text/event-stream",
        )
    except Exception as e:
        logger.error(f"API: 流式问答失败 - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"问答失败：{str(e)}")