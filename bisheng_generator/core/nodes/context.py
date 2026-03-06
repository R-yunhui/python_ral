"""图节点执行上下文：供各节点共享的 config、agents、进度回调"""

from typing import Awaitable, Callable

from config.config import Config
from agents.user_agent import UserAgent
from agents.tool_agent import ToolAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.workflow_agent import WorkflowAgent
from models.progress import ProgressEvent


class NodeContext:
    """节点执行上下文，由编排器创建并注入到各节点"""

    __slots__ = (
        "config",
        "user_agent",
        "tool_agent",
        "knowledge_agent",
        "workflow_agent",
        "emit_progress",
    )

    def __init__(
        self,
        *,
        config: Config,
        user_agent: UserAgent,
        tool_agent: ToolAgent,
        knowledge_agent: KnowledgeAgent,
        workflow_agent: WorkflowAgent,
        emit_progress: Callable[[ProgressEvent], Awaitable[None]],
    ):
        self.config = config
        self.user_agent = user_agent
        self.tool_agent = tool_agent
        self.knowledge_agent = knowledge_agent
        self.workflow_agent = workflow_agent
        self.emit_progress = emit_progress
