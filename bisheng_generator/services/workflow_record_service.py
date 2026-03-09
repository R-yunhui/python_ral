"""工作流生成记录服务：将编排结果落库（供编排器调用，不依赖请求上下文）"""

import json
import logging
from typing import Any, Dict, List, Optional

from config.config import Config
from db.database import get_session_factory
from db.repositories.workflow_record_repository import WorkflowRecordRepository

logger = logging.getLogger(__name__)


def _serialize_intent(intent: Any) -> Optional[Dict[str, Any]]:
    if intent is None:
        return None
    if hasattr(intent, "model_dump"):
        return intent.model_dump(mode="json")
    if isinstance(intent, dict):
        return intent
    return None


def _serialize_tools(tool_plan: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if tool_plan is None:
        return out
    selected = getattr(tool_plan, "selected_tools", None) or []
    for t in selected:
        out.append({
            "tool_key": getattr(t, "tool_key", ""),
            "name": getattr(t, "name", getattr(t, "tool_key", "")),
            "desc": getattr(t, "desc", ""),
        })
    return out


def _serialize_knowledge(knowledge_match: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if knowledge_match is None:
        return out
    bases = getattr(knowledge_match, "matched_knowledge_bases", None) or []
    for kb in bases:
        out.append({
            "id": getattr(kb, "id", None),
            "name": getattr(kb, "name", ""),
            "desc": getattr(kb, "desc", ""),
        })
    return out


def save_workflow_record(
    config: Config,
    raw_state: Dict[str, Any],
    session_id: Optional[str],
    status: str,
    error_message: Optional[str] = None,
) -> None:
    """
    将本次生成结果写入数据库（MySQL 或 SQLite，由 config 决定）。
    数据库未启用时静默跳过。

    Args:
        config: 配置对象
        raw_state: 编排器 ainvoke 返回的原始 state
        session_id: 会话 ID
        status: success / needs_clarification / error
        error_message: 失败时的错误信息
    """
    intent = raw_state.get("intent")
    tool_plan = raw_state.get("tool_plan")
    knowledge_match = raw_state.get("knowledge_match")
    workflow = raw_state.get("workflow")

    intent_result = _serialize_intent(intent)
    tools_used = _serialize_tools(tool_plan)
    knowledge_bases_used = _serialize_knowledge(knowledge_match)

    workflow_json: Optional[str] = None
    if workflow is not None:
        workflow_json = json.dumps(workflow, ensure_ascii=False) if isinstance(workflow, dict) else str(workflow)

    user_input = (raw_state.get("user_input") or "")[:2000]

    data = {
        "session_id": session_id or "",
        "user_input": user_input,
        "intent_result": intent_result,
        "tools_used": tools_used,
        "knowledge_bases_used": knowledge_bases_used,
        "workflow_json": workflow_json,
        "status": status,
        "error_message": error_message,
    }

    session_factory = get_session_factory(config)
    if session_factory is None:
        return
    session = session_factory()
    try:
        WorkflowRecordRepository.create(session, data)
        session.commit()
        logger.info("工作流生成记录已写入 MySQL, session_id=%s, status=%s", session_id, status)
    except Exception as e:
        session.rollback()
        logger.exception("写入工作流生成记录失败: %s", e)
    finally:
        session.close()


class WorkflowRecordService:
    """可注入的服务类（若后续需要从 FastAPI 依赖注入）"""

    def __init__(self, config: Config):
        self.config = config

    def save(
        self,
        raw_state: Dict[str, Any],
        session_id: Optional[str],
        status: str,
        error_message: Optional[str] = None,
    ) -> None:
        save_workflow_record(
            self.config, raw_state, session_id, status, error_message
        )


# 模块级便捷调用（编排器直接传 config）
workflow_record_service = None  # 可选：在 app 中绑定 config 后使用实例
