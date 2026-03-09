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
    flow_sketch: NotRequired[Optional[Dict[str, Any]]]
    """流程图草图：nodes + edges，供工作流生成节点严格按结构展开"""
    workflow: Optional[Dict[str, Any]]
    error: Optional[str]
    warnings: NotRequired[Optional[List[str]]]
    session_id: NotRequired[Optional[str]]
    # 知识库惰性加载：匹配节点需要时从 state 取 base_url/token 再加载
    bisheng_base_url: NotRequired[Optional[str]]
    access_token: NotRequired[Optional[str]]
