from datetime import datetime
from typing import Any
from sqlmodel import Session, func, select
from assistant.backend.model.sql_models import Expense, Income, Category


class QueryService:
    """SQL 聚合与查询能力"""

    def __init__(self, engine):
        self._engine = engine

    def sum_by_category(self, user_id: str, category_code: str, start: datetime, end: datetime) -> float:
        """按分类和时间范围汇总金额"""
        with Session(self._engine) as session:
            stmt = (
                select(func.sum(Expense.amount))
                .join(Category, Expense.category_l1_id == Category.id)
                .where(
                    Expense.user_id == user_id,
                    Expense.date >= start,
                    Expense.date <= end,
                    Category.code == category_code,
                )
            )
            return session.exec(stmt).one() or 0.0

    def sum_by_date_range(self, user_id: str, start: datetime, end: datetime) -> float:
        """按时间范围汇总所有支出"""
        with Session(self._engine) as session:
            stmt = (
                select(func.sum(Expense.amount))
                .where(
                    Expense.user_id == user_id,
                    Expense.date >= start,
                    Expense.date <= end,
                )
            )
            return session.exec(stmt).one() or 0.0

    def get_budget_usage(self, user_id: str, category_id: int, period_start: datetime, period_end: datetime) -> dict[str, Any]:
        """预算使用率"""
        with Session(self._engine) as session:
            stmt = (
                select(func.sum(Expense.amount))
                .where(
                    Expense.user_id == user_id,
                    Expense.category_l1_id == category_id,
                    Expense.date >= period_start,
                    Expense.date <= period_end,
                )
            )
            spent = session.exec(stmt).one() or Decimal("0")
            return {"spent": float(spent)}


class CategoryResolver:
    """分类标准化：按 别名精确匹配 -> 语义相似度 -> 关键词兜底 顺序"""
    THRESHOLD_AUTO = 0.85
    THRESHOLD_REVIEW = 0.60

    def __init__(self, engine):
        self._engine = engine

    def resolve(self, raw_category: str) -> dict:
        """分类匹配，返回 matched_category_id, match_type, confidence"""
        with Session(self._engine) as session:
            # 步骤 1: 别名精确匹配
            from assistant.backend.model.sql_models import CategoryAlias
            stmt = (
                select(Category, CategoryAlias)
                .join(CategoryAlias, Category.id == CategoryAlias.category_id)
                .where(CategoryAlias.alias == raw_category)
            )
            result = session.exec(stmt).first()
            if result:
                cat, alias = result
                return {
                    "matched_category_id": cat.id,
                    "match_type": "alias_exact",
                    "confidence": 1.0,
                }

            # 步骤 2: 分类名称精确匹配
            stmt2 = select(Category).where(Category.code == raw_category)
            cat = session.exec(stmt2).first()
            if cat:
                return {
                    "matched_category_id": cat.id,
                    "match_type": "code_exact",
                    "confidence": 1.0,
                }

            # 步骤 3: 兜底 -> 待分类
            default = session.exec(select(Category).where(Category.code == "其他支出")).first()
            return {
                "matched_category_id": default.id if default else None,
                "match_type": "fallback",
                "confidence": 0.3,
            }
