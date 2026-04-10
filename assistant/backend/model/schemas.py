from pydantic import BaseModel


class ChatRequest(BaseModel):
    user_id: str
    message: str


class ChatResponse(BaseModel):
    answer: str
    trace_id: str
    lang: str = "zh-CN"


class LLMPlan(BaseModel):
    store_intents: list[dict] = []
    query_intent: dict | None = None
    reply_strategy: str = "concise_cn"
