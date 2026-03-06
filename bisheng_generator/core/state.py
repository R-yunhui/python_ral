"""工作流编排状态定义"""

from typing import Any, Dict, List, NotRequired, Optional, TypedDict

from models.intent import EnhancedIntent
from agents.tool_agent import ToolPlan
from agents.knowledge_agent import KnowledgeMatch


class WorkflowState(TypedDict):
    """工作流编排状态"""

    user_input: str
    intent: Optional[EnhancedIntent]
    tool_plan: Optional[ToolPlan]
    knowledge_match: Optional[KnowledgeMatch]
    workflow: Optional[Dict[str, Any]]
    error: Optional[str]
    warnings: NotRequired[Optional[List[str]]]
    session_id: NotRequired[Optional[str]]
