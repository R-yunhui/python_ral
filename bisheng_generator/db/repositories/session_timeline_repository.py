"""会话时间线表的数据访问"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from db.models import SessionTimeline

logger = logging.getLogger(__name__)


class SessionTimelineRepository:
    """会话时间线的增删查（当前仅需插入与查询）"""

    @staticmethod
    def create(
        session: Session,
        session_id: str,
        item_type: str,
        payload: Dict[str, Any],
        sort_key: Optional[datetime] = None,
    ) -> SessionTimeline:
        """插入一条时间线记录。调用方负责 commit。"""
        now = datetime.utcnow()
        row = SessionTimeline(
            session_id=session_id,
            item_type=item_type,
            sort_key=sort_key or now,
            payload=payload,
            created_at=now,
        )
        session.add(row)
        session.flush()
        return row

    @staticmethod
    def list_sessions(session: Session, limit: int = 100) -> List[Dict[str, Any]]:
        """按最后活动时间倒序返回会话列表。每会话一条：session_id, preview, last_at。"""
        subq = (
            session.query(
                SessionTimeline.session_id,
                func.max(SessionTimeline.sort_key).label("last_at"),
            )
            .group_by(SessionTimeline.session_id)
            .subquery()
        )
        list_rows = (
            session.query(subq.c.session_id, subq.c.last_at)
            .order_by(desc(subq.c.last_at))
            .limit(limit)
            .all()
        )
        result = []
        for r in list_rows:
            # 取该会话第一条 user message 作为 preview（第一条用户输入）
            first_msg_row = (
                session.query(SessionTimeline.payload)
                .filter(
                    SessionTimeline.session_id == r.session_id,
                    SessionTimeline.item_type == "message",
                )
                .order_by(SessionTimeline.sort_key)
                .first()
            )
            payload = first_msg_row[0] if first_msg_row else None
            preview = (payload or {}).get("content", "")[:80] if payload else ""
            if not preview:
                preview = (r.session_id or "")[:16]
            result.append({
                "session_id": r.session_id,
                "preview": preview,
                "last_at": r.last_at.isoformat() if r.last_at else None,
            })
        return result

    @staticmethod
    def get_timeline(
        session: Session, session_id: str, limit: int = 500
    ) -> List[Dict[str, Any]]:
        """返回某会话的完整时间线，按 sort_key 升序。"""
        rows = (
            session.query(SessionTimeline)
            .filter(SessionTimeline.session_id == session_id)
            .order_by(SessionTimeline.sort_key)
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "item_type": r.item_type,
                "sort_key": r.sort_key.isoformat() if r.sort_key else None,
                "payload": r.payload,
            }
            for r in rows
        ]
