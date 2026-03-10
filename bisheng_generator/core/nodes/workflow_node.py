"""工作流生成节点：运行 WorkflowAgent，支持重试"""

import logging
import time
from typing import Any, Dict, Optional

from models.workflow_state import WorkflowState
from core.nodes.context import NodeContext
from core.utils import is_retryable
from agents.tool_agent import ToolPlan
from agents.knowledge_agent import KnowledgeMatch
from models.progress import AgentName, ProgressEvent

logger = logging.getLogger(__name__)


async def run_workflow_generation(
    state: WorkflowState, ctx: NodeContext
) -> Dict[str, Any]:
    """运行工作流生成 Agent（含重试与详细日志）"""
    start_time = time.time()
    await ctx.emit_progress(
        ProgressEvent.create_agent_start_event(AgentName.WORKFLOW_GENERATION)
    )

    if state.get("error"):
        duration_ms = (time.time() - start_time) * 1000
        await ctx.emit_progress(
            ProgressEvent.create_agent_error_event(
                AgentName.WORKFLOW_GENERATION,
                f"前置步骤错误：{state.get('error')}",
                duration_ms,
            )
        )
        return state

    intent = state.get("intent")
    if not intent:
        error_msg = "意图理解失败，无法生成工作流"
        logger.error(error_msg)
        duration_ms = (time.time() - start_time) * 1000
        await ctx.emit_progress(
            ProgressEvent.create_agent_error_event(
                AgentName.WORKFLOW_GENERATION, error_msg, duration_ms
            )
        )
        return {"error": error_msg}

    tool_plan = state.get("tool_plan") or ToolPlan()
    knowledge_match = state.get("knowledge_match") or KnowledgeMatch(
        required=False
    )
    flow_sketch = state.get("flow_sketch")

    cfg = ctx.config
    last_error: Optional[str] = None
    workflow_result: Optional[Dict[str, Any]] = None
    for attempt in range(cfg.max_retries_workflow + 1):
        try:
            workflow_result = await ctx.workflow_agent.generate_workflow(
                intent=intent,
                tool_plan=tool_plan,
                knowledge_match=knowledge_match,
                flow_sketch=flow_sketch,
            )
            if isinstance(workflow_result, dict) and "error" in workflow_result:
                last_error = workflow_result.get(
                    "error", "工作流生成内容无效"
                )
                content_preview = (
                    workflow_result.get("content") or ""
                )[:200]
                if attempt < cfg.max_retries_workflow:
                    logger.warning(
                        "工作流生成重试（第 %d 次），原因：%s",
                        attempt + 1,
                        last_error,
                    )
                    continue
                break
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "工作流生成完成",
                extra={
                    "nodes_count": len(workflow_result.get("nodes", []))
                },
            )
            await ctx.emit_progress(
                ProgressEvent.create_agent_complete_event(
                    AgentName.WORKFLOW_GENERATION,
                    {"workflow_generated": True},
                    duration_ms,
                )
            )
            return {"workflow": workflow_result}
        except Exception as e:
            last_error = str(e)
            if not is_retryable(e):
                duration_ms = (time.time() - start_time) * 1000
                logger.exception("工作流生成失败(不可重试)：%s", e)
                await ctx.emit_progress(
                    ProgressEvent.create_agent_error_event(
                        AgentName.WORKFLOW_GENERATION, str(e), duration_ms
                    )
                )
                return {"error": f"工作流生成失败：{str(e)}"}
            if attempt < cfg.max_retries_workflow:
                logger.warning(
                    "工作流生成重试（第 %d 次），原因：%s",
                    attempt + 1,
                    e,
                    exc_info=True,
                )
            else:
                logger.error(
                    "工作流生成失败(已用尽重试)，原因：%s",
                    e,
                    exc_info=True,
                )

    duration_ms = (time.time() - start_time) * 1000
    error_msg = last_error or "工作流生成失败"
    logger.error(
        "工作流生成节点失败：%s",
        error_msg,
        extra={"duration_ms": duration_ms},
    )
    await ctx.emit_progress(
        ProgressEvent.create_agent_error_event(
            AgentName.WORKFLOW_GENERATION, error_msg, duration_ms
        )
    )
    return {"error": f"工作流生成失败：{error_msg}"}
