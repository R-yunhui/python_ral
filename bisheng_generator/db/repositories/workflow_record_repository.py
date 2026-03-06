"""工作流生成记录表的数据访问"""

import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from db.models import WorkflowGenerationRecord

logger = logging.getLogger(__name__)


class WorkflowRecordRepository:
    """工作流生成记录的增删改查（当前仅需插入）"""

    @staticmethod
    def create(session: Session, data: Dict[str, Any]) -> WorkflowGenerationRecord:
        """插入一条记录。调用方负责 commit。"""
        record = WorkflowGenerationRecord(
            session_id=data.get("session_id", ""),
            user_input=data.get("user_input"),
            intent_result=data.get("intent_result"),
            tools_used=data.get("tools_used"),
            knowledge_bases_used=data.get("knowledge_bases_used"),
            workflow_json=data.get("workflow_json"),
            status=data.get("status", "success"),
            error_message=data.get("error_message"),
        )
        session.add(record)
        session.flush()
        return record
