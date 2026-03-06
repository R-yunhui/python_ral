"""SQLAlchemy 模型：表结构由代码定义，启动时自动创建"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON

from db.database import Base


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
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
