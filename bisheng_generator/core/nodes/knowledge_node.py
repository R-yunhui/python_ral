"""知识库匹配节点：运行 KnowledgeAgent，支持重试与降级"""

import logging
import time
from typing import Any, Dict, Optional

from core.state import WorkflowState
from core.nodes.context import NodeContext
from core.utils import is_retryable
from agents.knowledge_agent import KnowledgeMatch
from models.progress import AgentName, ProgressEvent

logger = logging.getLogger(__name__)


async def run_knowledge_matching(
    state: WorkflowState, ctx: NodeContext
) -> Dict[str, Any]:
    """运行知识库匹配 Agent（含重试与降级）"""
    intent = state.get("intent")
    needs_knowledge = bool(intent and intent.needs_knowledge)
    logger.info("知识库匹配开始", extra={"needs_knowledge": needs_knowledge})

    start_time = time.time()
    await ctx.emit_progress(
        ProgressEvent.create_agent_start_event(AgentName.KNOWLEDGE_MATCHING)
    )

    cfg = ctx.config
    if not intent or not intent.needs_knowledge:
        knowledge_match = KnowledgeMatch(required=False)
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "知识库匹配跳过(不需要知识库)", extra={"needs_knowledge": False}
        )
        await ctx.emit_progress(
            ProgressEvent.create_agent_complete_event(
                AgentName.KNOWLEDGE_MATCHING,
                {
                    "knowledge_count": 0,
                    "message": "不需要知识库，跳过知识库匹配",
                },
                duration_ms,
            )
        )
        return {"knowledge_match": knowledge_match}

    last_error: Optional[Exception] = None
    for attempt in range(cfg.max_retries_knowledge + 1):
        try:
            knowledge_match = await ctx.knowledge_agent.match_knowledge(intent)
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "知识库匹配完成",
                extra={
                    "matched_count": len(
                        knowledge_match.matched_knowledge_bases
                    ),
                    "kb_ids": [
                        kb.id for kb in knowledge_match.matched_knowledge_bases
                    ],
                },
            )
            event_data = {
                "knowledge_count": len(
                    knowledge_match.matched_knowledge_bases
                ),
                "matched_knowledge_bases": (
                    [
                        {"name": kb.name, "description": kb.desc}
                        for kb in knowledge_match.matched_knowledge_bases
                    ]
                    if knowledge_match.matched_knowledge_bases
                    else []
                ),
            }
            await ctx.emit_progress(
                ProgressEvent.create_agent_complete_event(
                    AgentName.KNOWLEDGE_MATCHING, event_data, duration_ms
                )
            )
            return {"knowledge_match": knowledge_match}
        except Exception as e:
            last_error = e
            if not is_retryable(e):
                duration_ms = (time.time() - start_time) * 1000
                logger.exception("知识库匹配失败(不可重试)：%s", e)
                await ctx.emit_progress(
                    ProgressEvent.create_agent_error_event(
                        AgentName.KNOWLEDGE_MATCHING, str(e), duration_ms
                    )
                )
                return {"error": f"知识库匹配失败：{str(e)}"}
            if attempt == cfg.max_retries_knowledge:
                break
            logger.warning(
                "知识库匹配重试",
                extra={"attempt": attempt + 1, "reason": str(e)},
            )

    duration_ms = (time.time() - start_time) * 1000
    logger.warning(
        "知识库匹配降级：返回空知识库列表",
        extra={"reason": str(last_error) if last_error else "unknown"},
    )
    await ctx.emit_progress(
        ProgressEvent.create_agent_complete_event(
            AgentName.KNOWLEDGE_MATCHING,
            {
                "knowledge_count": 0,
                "message": "知识库匹配失败，已降级为空列表",
                "degraded": True,
            },
            duration_ms,
        )
    )
    warnings = list(state.get("warnings") or [])
    warnings.append("知识库匹配失败，已使用空知识库列表")
    return {
        "knowledge_match": KnowledgeMatch(required=False),
        "warnings": warnings,
    }
