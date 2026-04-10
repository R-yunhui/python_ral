from fastapi import APIRouter, Depends
from assistant.backend.model.schemas import ChatRequest, ChatResponse
from assistant.backend.middleware.auth import check_auth

router = APIRouter()

_graph = None


def init_graph(graph):
    global _graph
    _graph = graph


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, _auth: str = Depends(check_auth)) -> ChatResponse:
    if _graph is None:
        return ChatResponse(answer="服务初始化中，请稍后再试。", trace_id="init_pending")
    result = await _graph.process(req.user_id, req.message)
    return ChatResponse(answer=result["answer"], trace_id=result["trace_id"])
