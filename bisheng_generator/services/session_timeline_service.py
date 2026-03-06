"""会话时间线服务：写入与查询时间线（仅当 MySQL 已配置时生效）"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from config.config import Config
from db.database import get_session_factory
from db.repositories.session_timeline_repository import SessionTimelineRepository

logger = logging.getLogger(__name__)


def save_timeline_message(
    config: Config,
    session_id: str,
    role: str,
    content: str,
    sort_key: Optional[datetime] = None,
) -> None:
    """写入一条对话消息。role: user | assistant。"""
    session_factory = get_session_factory(config)
    if session_factory is None:
        return
    session = session_factory()
    try:
        SessionTimelineRepository.create(
            session,
            session_id=session_id,
            item_type="message",
            payload={"role": role, "content": content},
            sort_key=sort_key or datetime.utcnow(),
        )
        session.commit()
    except Exception as e:
        logger.exception("写入会话消息失败: %s", e)
        session.rollback()
    finally:
        session.close()


def save_timeline_progress_event(
    config: Config,
    session_id: str,
    event_dict: Dict[str, Any],
    sort_key: Optional[datetime] = None,
) -> None:
    """写入一条进度事件（ProgressEvent.model_dump 的 dict）。"""
    session_factory = get_session_factory(config)
    if session_factory is None:
        return
    session = session_factory()
    try:
        sk = sort_key or datetime.utcnow()
        SessionTimelineRepository.create(
            session,
            session_id=session_id,
            item_type="progress_event",
            payload=event_dict,
            sort_key=sk,
        )
        session.commit()
    except Exception as e:
        logger.exception("写入会话进度事件失败: %s", e)
        session.rollback()
    finally:
        session.close()


def list_sessions(config: Config, limit: int = 100) -> List[Dict[str, Any]]:
    """返回会话列表，按最后活动时间倒序。"""
    session_factory = get_session_factory(config)
    if session_factory is None:
        return []
    session = session_factory()
    try:
        return SessionTimelineRepository.list_sessions(session, limit=limit)
    except Exception as e:
        logger.exception("列出会话失败: %s", e)
        return []
    finally:
        session.close()


def get_session_timeline(
    config: Config, session_id: str, limit: int = 500
) -> List[Dict[str, Any]]:
    """返回某会话的完整时间线。"""
    session_factory = get_session_factory(config)
    if session_factory is None:
        return []
    session = session_factory()
    try:
        return SessionTimelineRepository.get_timeline(session, session_id, limit=limit)
    except Exception as e:
        logger.exception("获取会话时间线失败: %s", e)
        return []
    finally:
        session.close()
