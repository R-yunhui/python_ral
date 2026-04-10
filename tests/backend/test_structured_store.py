import pytest
from datetime import datetime, timedelta
from sqlmodel import SQLModel, create_engine, Session, select
from assistant.backend.model.sql_models import (
    Expense, Category, init_db, seed_categories
)
from assistant.backend.service.structured_store_service import StructuredStoreService
from assistant.backend.service.query_service import QueryService, CategoryResolver


@pytest.fixture()
def engine():
    eng = create_engine("sqlite:///:memory:")
    init_db(eng)
    return eng


@pytest.fixture()
def store_service(engine):
    return StructuredStoreService(engine)


@pytest.fixture()
def query_service(engine):
    return QueryService(engine)


@pytest.fixture()
def category_resolver(engine):
    return CategoryResolver(engine)


def _get_category_id(engine, code: str) -> int:
    with Session(engine) as session:
        cat = session.exec(select(Category).where(Category.code == code)).first()
        return cat.id


@pytest.mark.asyncio
async def test_record_expense(store_service, engine):
    """记录一笔支出并验证落库"""
    cat_id = _get_category_id(engine, "餐饮")
    expense = await store_service.create_expense(
        user_id="u1", amount=30.0, category_l1_id=cat_id,
        description="午餐", date=datetime(2026, 4, 10),
    )
    assert expense.id is not None
    assert expense.amount == 30.0


@pytest.mark.asyncio
async def test_sum_by_category(query_service, store_service, engine):
    """按分类和时间范围汇总"""
    cat_id = _get_category_id(engine, "交通")
    await store_service.create_expense(
        user_id="u1", amount=45.0, category_l1_id=cat_id,
        description="打车", date=datetime(2026, 4, 10),
    )
    await store_service.create_expense(
        user_id="u1", amount=30.0, category_l1_id=cat_id,
        description="地铁", date=datetime(2026, 4, 11),
    )
    total = query_service.sum_by_category("u1", "交通", datetime(2026, 4, 1), datetime(2026, 4, 30))
    assert total == 75.0


def test_sum_by_date_range(query_service, store_service, engine):
    """时间范围汇总"""
    cat_id = _get_category_id(engine, "餐饮")
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        store_service.create_expense(
            user_id="u1", amount=50.0, category_l1_id=cat_id,
            description="聚餐", date=datetime(2026, 4, 5),
        )
    )
    total = query_service.sum_by_date_range("u1", datetime(2026, 4, 1), datetime(2026, 4, 30))
    assert total == 50.0


def test_category_resolver_exact_match(category_resolver):
    """分类名称精确匹配"""
    result = category_resolver.resolve("餐饮")
    assert result["confidence"] == 1.0
    assert result["match_type"] == "code_exact"


def test_category_resolver_fallback(category_resolver):
    """未知分类走兜底"""
    result = category_resolver.resolve("完全不存在的东西")
    assert result["confidence"] == 0.3
    assert result["match_type"] == "fallback"
