from datetime import datetime
from sqlmodel import Session, select
from assistant.backend.model.sql_models import Expense, Income, Category
from assistant.backend.service.query_service import CategoryResolver


class StructuredStoreService:
    """SQLite 结构化数据存储"""

    def __init__(self, engine):
        self._engine = engine
        self._category_resolver = CategoryResolver(engine)

    async def execute(self, intent: dict) -> object:
        """根据意图数据路由到正确的存储方法"""
        intent_type = intent.get("type", "structured")
        if intent_type == "structured":
            data = intent.get("data", intent)
            return await self._store_structured(data)
        raise ValueError(f"Unknown intent type: {intent_type}")

    async def _store_structured(self, data: dict):
        """存储结构化数据（收支记录）"""
        # 判断方向：如果有 source，可能是收入
        is_income = "source" in data or data.get("direction") == "income"
        raw_category = data.get("category", "其他支出" if not is_income else "其他收入")
        date_str = data.get("date")
        date = datetime.fromisoformat(date_str) if date_str else datetime.utcnow()

        # 分类标准化
        cat_result = self._category_resolver.resolve(raw_category)
        cat_id = cat_result.get("matched_category_id")
        confidence = cat_result.get("confidence", 0.0)
        needs_review = confidence < 0.85 if cat_id else True

        if is_income:
            return await self.create_income(
                user_id=data.get("user_id", "unknown"),
                amount=float(data.get("amount", 0)),
                category_l1_id=cat_id,
                description=data.get("description", ""),
                date=date,
                category_confidence=confidence,
            )
        else:
            return await self.create_expense(
                user_id=data.get("user_id", "unknown"),
                amount=float(data.get("amount", 0)),
                category_l1_id=cat_id,
                description=data.get("description", ""),
                date=date,
                category_confidence=confidence,
                needs_review=needs_review,
            )

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
