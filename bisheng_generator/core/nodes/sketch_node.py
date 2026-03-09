"""流程图草图节点：在完整工作流生成前产出 nodes+edges 简图"""

import logging
import time
from typing import Any, Dict

from models.workflow_state import WorkflowState
from core.nodes.context import NodeContext
from core.utils import sketch_to_mermaid
from agents.tool_agent import ToolPlan
from agents.knowledge_agent import KnowledgeMatch
from models.progress import AgentName, ProgressEvent

logger = logging.getLogger(__name__)


async def run_flow_sketch(
    state: WorkflowState, ctx: NodeContext
) -> Dict[str, Any]:
    """
    运行流程图草图生成：调用 WorkflowAgent.generate_flow_sketch，
    将结果写入 state.flow_sketch。失败时写入 None，下游仍可继续生成。
    """
    start_time = time.time()
    await ctx.emit_progress(
        ProgressEvent.create_agent_start_event(AgentName.FLOW_SKETCH)
    )

    if state.get("error"):
        duration_ms = (time.time() - start_time) * 1000
        await ctx.emit_progress(
            ProgressEvent.create_agent_error_event(
                AgentName.FLOW_SKETCH,
                f"前置步骤错误：{state.get('error')}",
                duration_ms,
            )
        )
        return state

    intent = state.get("intent")
    if not intent:
        error_msg = "意图理解失败，无法生成草图"
        logger.error(error_msg)
        duration_ms = (time.time() - start_time) * 1000
        await ctx.emit_progress(
            ProgressEvent.create_agent_error_event(
                AgentName.FLOW_SKETCH, error_msg, duration_ms
            )
        )
        return {"error": error_msg}

    tool_plan = state.get("tool_plan") or ToolPlan()
    knowledge_match = state.get("knowledge_match") or KnowledgeMatch(
        required=False
    )

    try:
        sketch = await ctx.workflow_agent.generate_flow_sketch(
            intent=intent,
            tool_plan=tool_plan,
            knowledge_match=knowledge_match,
        )
    except Exception as e:
        logger.exception("流程图草图节点异常：%s", e)
        duration_ms = (time.time() - start_time) * 1000
        await ctx.emit_progress(
            ProgressEvent.create_agent_error_event(
                AgentName.FLOW_SKETCH, str(e), duration_ms
            )
        )
        return {"flow_sketch": None}

    duration_ms = (time.time() - start_time) * 1000
    nodes_count = len(sketch.get("nodes", [])) if sketch else 0
    mermaid_str = sketch_to_mermaid(sketch) if sketch else ""
    await ctx.emit_progress(
        ProgressEvent.create_agent_complete_event(
            AgentName.FLOW_SKETCH,
            {"nodes_count": nodes_count, "flow_sketch_mermaid": mermaid_str},
            duration_ms,
        )
    )
    return {"flow_sketch": sketch}
