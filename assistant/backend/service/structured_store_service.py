from datetime import datetime
from sqlmodel import Session, select
from assistant.backend.model.sql_models import Expense, Income


class StructuredStoreService:
    """SQLite 结构化数据存储"""

    def __init__(self, engine):
        self._engine = engine

    async def create_expense(
        self,
        user_id: str,
        amount: float,
        category_l1_id: int,
        description: str,
        date: datetime,
        category_l2_id: int | None = None,
        category_confidence: float | None = None,
        needs_review: bool = False,
    ) -> Expense:
        with Session(self._engine) as session:
            expense = Expense(
                user_id=user_id,
                amount=amount,
                category_l1_id=category_l1_id,
                category_l2_id=category_l2_id,
                description=description,
                date=date,
                category_confidence=category_confidence,
                needs_review=needs_review,
            )
            session.add(expense)
            session.commit()
            session.refresh(expense)
            return expense

    async def create_income(
        self,
        user_id: str,
        amount: float,
        category_l1_id: int,
        description: str,
        date: datetime,
        category_l2_id: int | None = None,
        category_confidence: float | None = None,
    ) -> Income:
        with Session(self._engine) as session:
            income = Income(
                user_id=user_id,
                amount=amount,
                category_l1_id=category_l1_id,
                category_l2_id=category_l2_id,
                description=description,
                date=date,
                category_confidence=category_confidence,
            )
            session.add(income)
            session.commit()
            session.refresh(income)
            return income
