"""工具选择节点：运行 ToolAgent，支持重试与降级"""

import logging
import time
from typing import Any, Dict, Optional

from core.state import WorkflowState
from core.nodes.context import NodeContext
from core.utils import is_retryable
from agents.tool_agent import ToolPlan
from models.progress import AgentName, ProgressEvent

logger = logging.getLogger(__name__)


async def run_tool_selection(
    state: WorkflowState, ctx: NodeContext
) -> Dict[str, Any]:
    """运行工具选择 Agent（含重试与降级）"""
    intent = state.get("intent")
    needs_tool = bool(intent and intent.needs_tool)
    logger.info("工具选择开始", extra={"needs_tool": needs_tool})

    start_time = time.time()
    await ctx.emit_progress(
        ProgressEvent.create_agent_start_event(AgentName.TOOL_SELECTION)
    )

    cfg = ctx.config
    if not intent or not intent.needs_tool:
        tool_plan = ToolPlan()
        duration_ms = (time.time() - start_time) * 1000
        logger.info("工具选择跳过(不需要工具)", extra={"needs_tool": False})
        await ctx.emit_progress(
            ProgressEvent.create_agent_complete_event(
                AgentName.TOOL_SELECTION,
                {"tools_count": 0, "message": "不需要调用工具，跳过工具选择"},
                duration_ms,
            )
        )
        return {"tool_plan": tool_plan}

    last_error: Optional[Exception] = None
    for attempt in range(cfg.max_retries_tool + 1):
        try:
            tool_plan = await ctx.tool_agent.select_tools(intent)
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "工具选择完成",
                extra={
                    "selected_count": len(tool_plan.selected_tools),
                    "tool_keys": [t.tool_key for t in tool_plan.selected_tools],
                },
            )
            event_data = {
                "tools_count": len(tool_plan.selected_tools),
                "selected_tools": (
                    [
                        {"name": t.name, "description": t.desc}
                        for t in tool_plan.selected_tools
                    ]
                    if tool_plan.selected_tools
                    else []
                ),
            }
            await ctx.emit_progress(
                ProgressEvent.create_agent_complete_event(
                    AgentName.TOOL_SELECTION, event_data, duration_ms
                )
            )
            return {"tool_plan": tool_plan}
        except Exception as e:
            last_error = e
            if not is_retryable(e):
                duration_ms = (time.time() - start_time) * 1000
                logger.exception("工具选择失败(不可重试)：%s", e)
                await ctx.emit_progress(
                    ProgressEvent.create_agent_error_event(
                        AgentName.TOOL_SELECTION, str(e), duration_ms
                    )
                )
                return {"error": f"工具选择失败：{str(e)}"}
            if attempt == cfg.max_retries_tool:
                break
            logger.warning(
                "工具选择重试",
                extra={"attempt": attempt + 1, "reason": str(e)},
            )

    duration_ms = (time.time() - start_time) * 1000
    logger.warning(
        "工具选择降级：返回空工具列表",
        extra={"reason": str(last_error) if last_error else "unknown"},
    )
    await ctx.emit_progress(
        ProgressEvent.create_agent_complete_event(
            AgentName.TOOL_SELECTION,
            {
                "tools_count": 0,
                "message": "工具选择失败，已降级为空列表",
                "degraded": True,
            },
            duration_ms,
        )
    )
    warnings = list(state.get("warnings") or [])
    warnings.append("工具选择失败，已使用空工具列表")
    return {"tool_plan": ToolPlan(), "warnings": warnings}
