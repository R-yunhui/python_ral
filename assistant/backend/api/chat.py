from uuid import uuid4
from fastapi import APIRouter, Depends
from assistant.backend.model.schemas import ChatRequest, ChatResponse
from assistant.backend.middleware.auth import check_auth

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, _auth: str = Depends(check_auth)) -> ChatResponse:
    return ChatResponse(answer="已收到，我正在处理你的财务问题。", trace_id=str(uuid4()))
