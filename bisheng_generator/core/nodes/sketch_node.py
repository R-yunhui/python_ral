"""流程图草图节点：在完整工作流生成前产出 nodes+edges 简图"""

import logging
import time
from typing import Any, Dict, List, Optional

from langgraph.types import interrupt

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
    knowledge_match = state.get("knowledge_match") or KnowledgeMatch(required=False)

    # ── 1. 优先按多个维度生成草图备选方案 ─────────────────────────
    try:
        variants = await ctx.workflow_agent.generate_flow_sketch_variants(
            intent=intent,
            tool_plan=tool_plan,
            knowledge_match=knowledge_match,
        )
    except Exception as e:
        logger.exception("流程图草图多方案生成异常：%s，将回退到单方案模式", e)
        variants = []

    sketch: Optional[Dict[str, Any]] = None
    selected_variant_id: Optional[str] = None

    if variants:
        # 为每个方案预先计算 Mermaid，便于前端直接渲染
        options: List[Dict[str, Any]] = []
        for v in variants:
            vid = v.get("id") or ""
            title = v.get("title") or vid
            desc = v.get("description") or ""
            v_sketch = v.get("sketch") or {}
            mermaid = sketch_to_mermaid(v_sketch) or ""
            nodes_cnt = len(v_sketch.get("nodes") or [])
            options.append(
                {
                    "id": vid,
                    "title": title,
                    "description": desc,
                    "nodes_count": nodes_cnt,
                    "mermaid": mermaid,
                }
            )

        pending = {
            "type": "flow_sketch_selection",
            "stage": "flow_sketch",
            "message": "已为当前需求生成多个流程图草图方案，请选择一个用于后续完整工作流生成。",
            "options": options,
            "original_user_input": state.get("user_input") or "",
            "intent_rewritten_input": intent.rewritten_input,
        }

        logger.info(
            "流程图草图生成完成，进入多方案选择 interrupt，variants=%d", len(variants)
        )
        user_reply = interrupt(pending)
        logger.info("flow_sketch interrupt 恢复，user_reply=%s", str(user_reply)[:200])

        # 解析用户选择的方案 ID（支持直接传字符串或 {id: "..."}）
        choice_id: Optional[str] = None
        if isinstance(user_reply, dict):
            choice_id = str(user_reply.get("id") or "").strip() or None
        elif isinstance(user_reply, str):
            choice_id = user_reply.strip() or None

        # 若未匹配到合法 ID，则默认选择第一个方案
        chosen = None
        if choice_id:
            for v in variants:
                if str(v.get("id")) == choice_id:
                    chosen = v
                    break
        if not chosen and variants:
            chosen = variants[0]

        if chosen:
            sketch = chosen.get("sketch") or None
            selected_variant_id = str(chosen.get("id") or "")
        else:
            sketch = None
    else:
        # ── 2. 回退：仅生成单个草图（兼容旧逻辑） ─────────────────────
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
            return {"flow_sketch": None, "flow_sketch_variants": None}

    duration_ms = (time.time() - start_time) * 1000
    nodes_count = len(sketch.get("nodes", [])) if sketch else 0
    mermaid_str = sketch_to_mermaid(sketch) if sketch else ""
    event_data: Dict[str, Any] = {
        "nodes_count": nodes_count,
        "flow_sketch_mermaid": mermaid_str,
    }
    if selected_variant_id is not None:
        event_data["selected_variant_id"] = selected_variant_id
        event_data["variants_count"] = len(variants)

    await ctx.emit_progress(
        ProgressEvent.create_agent_complete_event(
            AgentName.FLOW_SKETCH,
            event_data,
            duration_ms,
        )
    )
    return {
        "flow_sketch": sketch,
        "flow_sketch_variants": variants or None,
    }
