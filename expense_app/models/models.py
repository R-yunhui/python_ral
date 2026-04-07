"""
数据库模型定义

包含三个核心模型：
- Expense: 开销记录
- Income: 收入记录
- Budget: 预算设置
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import logging

from .database import Base

logger = logging.getLogger(__name__)


class Expense(Base):
    """
    开销记录模型

    用于记录用户的日常开销，包括金额、分类、日期等信息

    Attributes:
        id: 主键 ID
        amount: 开销金额（必须大于 0）
        category: 开销分类（如：餐饮、交通、购物等）
        date: 开销发生日期
        description: 开销描述（可选）
        tags: 标签列表，JSON 字符串格式（可选）
        created_at: 记录创建时间
    """
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True, comment="主键 ID")
    amount = Column(Float, nullable=False, comment="开销金额")
    category = Column(String(50), nullable=False, index=True, comment="开销分类")
    date = Column(Date, nullable=False, index=True, comment="开销日期")
    description = Column(Text, nullable=True, comment="开销描述")
    tags = Column(String(200), nullable=True, comment="标签列表 (JSON 字符串)")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    def __repr__(self):
        return f"<Expense(id={self.id}, amount={self.amount}, category='{self.category}')>"


class Income(Base):
    """
    收入记录模型

    用于记录用户的收入，如工资、奖金、投资收益等

    Attributes:
        id: 主键 ID
        amount: 收入金额（必须大于 0）
        source: 收入来源（如：工资、奖金、兼职等）
        date: 收入日期
        note: 备注信息（可选）
        created_at: 记录创建时间
    """
    __tablename__ = "incomes"

    id = Column(Integer, primary_key=True, index=True, comment="主键 ID")
    amount = Column(Float, nullable=False, comment="收入金额")
    source = Column(String(100), nullable=False, index=True, comment="收入来源")
    date = Column(Date, nullable=False, index=True, comment="收入日期")
    note = Column(Text, nullable=True, comment="备注信息")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    def __repr__(self):
        return f"<Income(id={self.id}, amount={self.amount}, source='{self.source}')>"


class Budget(Base):
    """
    预算设置模型

    用于设置月度或年度预算，可按分类或总额设置

    Attributes:
        id: 主键 ID
        type: 预算类型（monthly: 月度，yearly: 年度）
        category: 预算分类（可选，为空时表示总预算）
        amount: 预算金额
        period: 预算周期（格式：YYYY-MM 或 YYYY）
        created_at: 记录创建时间
    """
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True, comment="主键 ID")
    type = Column(String(10), nullable=False, index=True, comment="预算类型 (monthly/yearly)")
    category = Column(String(50), nullable=True, index=True, comment="预算分类 (为空表示总预算)")
    amount = Column(Float, nullable=False, comment="预算金额")
    period = Column(String(7), nullable=False, index=True, comment="预算周期 (YYYY-MM 或 YYYY)")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    def __repr__(self):
        return f"<Budget(id={self.id}, type='{self.type}', period='{self.period}', amount={self.amount})>"
