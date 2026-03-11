"""SQLAlchemy 模型：表结构由代码定义，启动时自动创建"""

from datetime import datetime, timezone, timedelta
from sqlalchemy import Boolean, Column, Integer, String, Text, DateTime, JSON

from db.database import Base

# 中国时区 UTC+8，用于 created_at / deleted_at 等默认时间
CHINA_TZ = timezone(timedelta(hours=8))


def _now_cn():
    """当前时间（中国时区），供 Column default 使用"""
    return datetime.now(CHINA_TZ)


class WorkflowGenerationRecord(Base):
    """工作流生成记录表（表名由 __tablename__ 指定，无需额外配置）"""

    __tablename__ = "workflow_generation_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(128), index=True, nullable=False, default="")
    user_input = Column(Text, nullable=True)
    intent_result = Column(JSON, nullable=True, comment="意图识别结果 JSON")
    tools_used = Column(JSON, nullable=True, comment="本次使用的工具列表")
    knowledge_bases_used = Column(JSON, nullable=True, comment="本次使用的知识库列表")
    workflow_json = Column(Text, nullable=True, comment="最终工作流 JSON")
    status = Column(String(32), nullable=False, default="success", comment="success / needs_clarification / error")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=_now_cn)


class SessionTimeline(Base):
    """会话时间线表：按 session 存储对话消息与推送的进度事件，便于查看历史"""

    __tablename__ = "session_timeline"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(128), nullable=False, index=True, comment="会话 ID")
    item_type = Column(String(32), nullable=False, comment="message | progress_event")
    sort_key = Column(DateTime, nullable=False, comment="发生时间，用于排序")
    payload = Column(JSON, nullable=False, comment="message: {role,content}; progress_event: 完整事件")
    created_at = Column(DateTime, nullable=False, default=_now_cn)


class SessionMeta(Base):
    """会话元信息：软删除标识，删除的会话不再出现在列表且不可续轮"""

    __tablename__ = "session_meta"

    session_id = Column(String(128), primary_key=True, comment="会话 ID")
    is_deleted = Column(Boolean, nullable=False, default=False, comment="是否已软删除")
    deleted_at = Column(DateTime, nullable=True, comment="删除时间")
    created_at = Column(DateTime, nullable=False, default=_now_cn)
