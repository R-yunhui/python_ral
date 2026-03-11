"""会话元信息表的数据访问：软删除标识"""

import logging
from typing import Set

from sqlalchemy.orm import Session

from db.models import SessionMeta, _now_cn

logger = logging.getLogger(__name__)


class SessionMetaRepository:
    """会话元信息：软删除标记，删除的会话不展示且不可续轮"""

    @staticmethod
    def mark_deleted(session: Session, session_id: str) -> None:
        """将会话标记为已删除（软删除）。若记录不存在则插入，存在则更新。调用方负责 commit。"""
        row = session.query(SessionMeta).filter(SessionMeta.session_id == session_id).first()
        now = _now_cn()
        if row:
            row.is_deleted = True
            row.deleted_at = now
        else:
            session.add(
                SessionMeta(
                    session_id=session_id,
                    is_deleted=True,
                    deleted_at=now,
                )
            )
        session.flush()

    @staticmethod
    def is_session_deleted(session: Session, session_id: str) -> bool:
        """查询该会话是否已软删除。"""
        row = session.query(SessionMeta).filter(SessionMeta.session_id == session_id).first()
        return row is not None and bool(row.is_deleted)

    @staticmethod
    def get_deleted_session_ids(session: Session) -> Set[str]:
        """返回所有已软删除的 session_id 集合，用于列表过滤。"""
        rows = (
            session.query(SessionMeta.session_id)
            .filter(SessionMeta.is_deleted == True)  # noqa: E712
            .all()
        )
        return {r[0] for r in rows if r[0]}
