from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import text, Numeric


class Category(SQLModel, table=True):
    __tablename__ = "categories"
    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True)
    name: str
    direction: str  # expense | income
    level: int  # 1 | 2
    parent_id: int | None = Field(default=None, foreign_key="categories.id")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CategoryAlias(SQLModel, table=True):
    __tablename__ = "category_aliases"
    id: int | None = Field(default=None, primary_key=True)
    category_id: int = Field(foreign_key="categories.id")
    alias: str
    locale: str = "zh-CN"
    weight: float = Field(default=1.0)


class Expense(SQLModel, table=True):
    __tablename__ = "expenses"
    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    amount: float
    category_l1_id: int | None = Field(foreign_key="categories.id")
    category_l2_id: int | None = Field(foreign_key="categories.id")
    description: str
    date: datetime
    payment_method: str | None = None
    category_confidence: float | None = None
    needs_review: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Income(SQLModel, table=True):
    __tablename__ = "incomes"
    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    amount: float
    source: str
    category_l1_id: int | None = Field(foreign_key="categories.id")
    category_l2_id: int | None = Field(foreign_key="categories.id")
    description: str
    date: datetime
    category_confidence: float | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Budget(SQLModel, table=True):
    __tablename__ = "budgets"
    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    category_id: int = Field(foreign_key="categories.id")
    amount: float
    period_type: str  # daily | weekly | monthly | yearly
    period_start: datetime
    period_end: datetime
    alert_threshold_pct: float = Field(default=80.0)
    is_active: bool = Field(default=True)


class MonthlySummary(SQLModel, table=True):
    __tablename__ = "monthly_summaries"
    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    year: int
    month: int
    total_expense: float = Field(default=0.0)
    total_income: float = Field(default=0.0)
    top_category: str | None = None


def init_db(engine):
    """初始化数据库：建表 + 启用 WAL + 种子数据"""
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA busy_timeout=5000"))
    SQLModel.metadata.create_all(engine)
    seed_categories(engine)


def seed_categories(engine):
    """写入初始分类字典（需求文档 10.2 节）— 幂等"""
    from sqlmodel import Session, select
    with Session(engine) as session:
        existing = session.exec(select(Category).where(Category.level == 1)).first()
        if existing:
            return  # 已存在，跳过
        categories = [
            Category(code="餐饮", name="餐饮", direction="expense", level=1),
            Category(code="交通", name="交通", direction="expense", level=1),
            Category(code="居住", name="居住", direction="expense", level=1),
            Category(code="购物", name="购物", direction="expense", level=1),
            Category(code="娱乐", name="娱乐", direction="expense", level=1),
            Category(code="医疗", name="医疗", direction="expense", level=1),
            Category(code="教育", name="教育", direction="expense", level=1),
            Category(code="通讯", name="通讯", direction="expense", level=1),
            Category(code="其他支出", name="其他", direction="expense", level=1),
            Category(code="工资", name="工资", direction="income", level=1),
            Category(code="奖金", name="奖金", direction="income", level=1),
            Category(code="报销", name="报销", direction="income", level=1),
            Category(code="理财", name="理财", direction="income", level=1),
            Category(code="转账", name="转账", direction="income", level=1),
            Category(code="退款", name="退款", direction="income", level=1),
            Category(code="其他收入", name="其他", direction="income", level=1),
        ]
        session.add_all(categories)
        session.commit()
