from typing import TypedDict, Optional
from assistant.backend.model.schemas import LLMPlan


class GraphState(TypedDict):
    user_id: str
    message: str
    trace_id: str
    plan: Optional[LLMPlan]
    query_results: list[dict]
    long_memory_results: list[dict]
    answer: str
    errors: list[str]
