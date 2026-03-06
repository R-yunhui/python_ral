"""意图理解节点：运行 UserAgent，支持重试、降级与 interrupt 澄清"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

from langgraph.types import interrupt

from models.workflow_state import WorkflowState
from core.nodes.context import NodeContext
from core.utils import is_retryable
from models.intent import EnhancedIntent
from models.progress import AgentName, ProgressEvent

logger = logging.getLogger(__name__)


async def understand_with_retry(
    ctx: NodeContext,
    user_input: str,
    state: WorkflowState,
    start_time: float,
    chat_history: Optional[List[Dict[str, Any]]] = None,
) -> Optional[EnhancedIntent]:
    """带重试与降级的 understand 调用，返回 None 表示已写入 state error/降级。"""
    last_error: Optional[Exception] = None
    cfg = ctx.config
    for attempt in range(cfg.max_retries_intent + 1):
        try:
            intent = await ctx.user_agent.understand(
                user_input, chat_history=chat_history
            )
            if intent.rewritten_input:
                return intent
            last_error = ValueError("意图理解返回空结果")
        except Exception as e:
            last_error = e
            if not is_retryable(e):
                duration_ms = (time.time() - start_time) * 1000
                logger.exception("意图理解失败(不可重试)：%s", e)
                await ctx.emit_progress(
                    ProgressEvent.create_agent_error_event(
                        AgentName.INTENT_UNDERSTANDING, str(e), duration_ms
                    )
                )
                state["error"] = f"意图理解失败：{str(e)}"
                return None
            if attempt == cfg.max_retries_intent:
                break
            logger.warning(
                "意图理解重试",
                extra={"attempt": attempt + 1, "reason": str(e)},
            )

    duration_ms = (time.time() - start_time) * 1000
    fallback_intent = EnhancedIntent(
        original_input=user_input,
        rewritten_input=user_input,
        needs_tool=False,
        needs_knowledge=False,
        multi_turn=True,
    )
    logger.warning("意图理解降级：使用原始输入作为重写结果")
    await ctx.emit_progress(
        ProgressEvent.create_agent_complete_event(
            AgentName.INTENT_UNDERSTANDING,
            {
                "workflow_type": fallback_intent.get_workflow_type(),
                "needs_tool": False,
                "needs_knowledge": False,
                "rewritten_input": user_input,
                "degraded": True,
            },
            duration_ms,
        )
    )
    return fallback_intent


async def run_intent_understanding(
    state: WorkflowState, ctx: NodeContext
) -> Dict[str, Any]:
    """
    运行意图理解 Agent（含重试、降级、interrupt 澄清）。
    恢复时 LangGraph 会从节点开头重新执行整个节点，但 interrupt()
    在第二次执行时直接返回 resume 值而不再暂停。
    """
    user_input = state.get("user_input") or ""
    logger.info(
        "意图理解开始",
        extra={"user_input_preview": user_input[:100] if user_input else ""},
    )

    start_time = time.time()
    await ctx.emit_progress(
        ProgressEvent.create_agent_start_event(AgentName.INTENT_UNDERSTANDING)
    )

    intent = await understand_with_retry(ctx, user_input, state, start_time)
    if intent is None:
        return state

    if intent.needs_clarification and intent.clarification_questions:
        pending = {
            "questions": intent.clarification_questions,
            "message": "请补充以下信息，以便更准确生成工作流",
            "rewritten_input_preview": intent.rewritten_input,
            "original_user_input": user_input,
        }
        logger.info(
            "意图需要澄清，触发 interrupt，questions=%s",
            intent.clarification_questions,
        )
        user_reply = interrupt(pending)
        logger.info(
            "interrupt 恢复，user_reply=%s", (str(user_reply) or "")[:100]
        )

        chat_history = [
            {"role": "user", "content": user_input},
            {
                "role": "assistant",
                "content": json.dumps(pending, ensure_ascii=False),
            },
        ]
        merged = await understand_with_retry(
            ctx, str(user_reply), state, start_time, chat_history=chat_history
        )
        if merged is None:
            return state
        merged.needs_clarification = False
        merged.clarification_questions = []
        intent = merged

    duration_ms = (time.time() - start_time) * 1000
    event_data = {
        "workflow_type": intent.get_workflow_type(),
        "needs_tool": intent.needs_tool,
        "needs_knowledge": intent.needs_knowledge,
        "rewritten_input": intent.rewritten_input,
    }
    await ctx.emit_progress(
        ProgressEvent.create_agent_complete_event(
            AgentName.INTENT_UNDERSTANDING, event_data, duration_ms
        )
    )
    return {"intent": intent}
