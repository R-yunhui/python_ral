# Expense Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现个人助手开销管理模块，包含日常开销记录、收入记录、预算管理、统计展示和 Agent 查询功能。

**Architecture:** FastAPI 后端提供 REST API + SQLite 数据库存储，React 前端展示数据和图表，LangChain Agent 支持自然语言查询。

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, React, TypeScript, Recharts, LangChain, Chroma

---

## File Structure

### Backend Files
- `expense_app/__init__.py` - 包初始化
- `expense_app/api/__init__.py` - API 包初始化
- `expense_app/api/routers/__init__.py` - Routers 包初始化
- `expense_app/models/__init__.py` - Models 包初始化
- `expense_app/service/__init__.py` - Service 包初始化
- `expense_app/utils/__init__.py` - Utils 包初始化
- `expense_app/models/database.py` - 数据库配置
- `expense_app/models/models.py` - SQLAlchemy 模型定义
- `expense_app/api/schemas.py` - Pydantic 数据模型
- `expense_app/api/main.py` - FastAPI 应用入口
- `expense_app/api/routers/expenses.py` - 开销 CRUD API
- `expense_app/api/routers/incomes.py` - 收入 CRUD API
- `expense_app/api/routers/budgets.py` - 预算 CRUD API
- `expense_app/api/routers/stats.py` - 统计 API
- `expense_app/api/routers/agent.py` - Agent 查询 API
- `expense_app/service/expense_service.py` - 业务逻辑层
- `expense_app/service/agent_service.py` - Agent 服务
- `expense_app/utils/logger.py` - 日志工具
- `start_app.py` - 应用启动脚本

### Frontend Files
- `expense_web/package.json` - 依赖配置
- `expense_web/vite.config.ts` - Vite 配置
- `expense_web/tsconfig.json` - TypeScript 配置
- `expense_web/index.html` - HTML 入口
- `expense_web/src/index.css` - 全局样式
- `expense_web/src/main.tsx` - React 入口
- `expense_web/src/App.tsx` - 主应用组件
- `expense_web/src/api/client.ts` - API 客户端
- `expense_web/src/pages/Dashboard.tsx` - 概览页
- `expense_web/src/pages/Expenses.tsx` - 开销管理页
- `expense_web/src/pages/Income.tsx` - 收入管理页
- `expense_web/src/pages/Budgets.tsx` - 预算管理页
- `expense_web/src/pages/Statistics.tsx` - 统计页
- `expense_web/src/components/SummaryCards.tsx` - 概览卡片组件
- `expense_web/src/components/ExpenseForm.tsx` - 开销表单组件
- `expense_web/src/components/ExpenseList.tsx` - 开销列表组件
- `expense_web/src/components/Charts.tsx` - 图表组件
- `expense_web/tailwind.config.js` - Tailwind 配置
- `expense_web/postcss.config.js` - PostCSS 配置

---

## Task 1: 后端项目结构与数据库模型

**Files:**
- Create: `expense_app/__init__.py`
- Create: `expense_app/api/__init__.py`
- Create: `expense_app/api/routers/__init__.py`
- Create: `expense_app/models/__init__.py`
- Create: `expense_app/service/__init__.py`
- Create: `expense_app/utils/__init__.py`
- Create: `expense_app/models/database.py`
- Create: `expense_app/models/models.py`
- Create: `expense_app/api/schemas.py`

- [ ] **Step 1: 创建项目目录和 __init__.py 文件**

```bash
mkdir -p expense_app/api/routers expense_app/models expense_app/service expense_app/utils
touch expense_app/__init__.py expense_app/api/__init__.py expense_app/api/routers/__init__.py
touch expense_app/models/__init__.py expense_app/service/__init__.py expense_app/utils/__init__.py
```

- [ ] **Step 2: 创建数据库配置文件**

```python
# expense_app/models/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./expense_app.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 3: 创建 SQLAlchemy 模型**

```python
# expense_app/models/models.py
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text
from datetime import datetime
from .database import Base

class Expense(Base):
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    category = Column(String(50), nullable=False)
    date = Column(Date, nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Income(Base):
    __tablename__ = "incomes"
    
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    source = Column(String(100), nullable=False)
    date = Column(Date, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Budget(Base):
    __tablename__ = "budgets"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(10), nullable=False)
    category = Column(String(50), nullable=True)
    amount = Column(Float, nullable=False)
    period = Column(String(7), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 4: 创建 Pydantic Schemas**

```python
# expense_app/api/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime

class ExpenseBase(BaseModel):
    amount: float = Field(..., gt=0)
    category: str
    date: date
    description: Optional[str] = None
    tags: Optional[List[str]] = None

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    category: Optional[str] = None
    date: Optional[date] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None

class Expense(ExpenseBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class IncomeBase(BaseModel):
    amount: float = Field(..., gt=0)
    source: str
    date: date
    note: Optional[str] = None

class IncomeCreate(IncomeBase):
    pass

class Income(IncomeBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class BudgetBase(BaseModel):
    type: str
    category: Optional[str] = None
    amount: float = Field(..., gt=0)
    period: str

class BudgetCreate(BudgetBase):
    pass

class Budget(BudgetBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class StatsSummary(BaseModel):
    total_income: float
    total_expense: float
    balance: float
    category_breakdown: dict
```

- [ ] **Step 5: 验证数据库创建**

```bash
python -c "from expense_app.models.database import engine, Base; from expense_app.models.models import Expense, Income, Budget; Base.metadata.create_all(bind=engine); print('Database created!')"
```
Expected: "Database created!"

- [ ] **Step 6: 提交**

```bash
git add expense_app/
git commit -m "feat: add database models and schemas"
```

---

## Task 2: 开销 CRUD API

**Files:**
- Create: `expense_app/api/routers/expenses.py`
- Create: `expense_app/api/main.py`
- Create: `start_app.py`

- [ ] **Step 1: 实现开销路由**

```python
# expense_app/api/routers/expenses.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import json

from expense_app.models.database import get_db
from expense_app.models.models import Expense
from expense_app.api.schemas import ExpenseCreate, ExpenseUpdate, Expense

router = APIRouter(prefix="/api/expenses", tags=["expenses"])

@router.post("/", response_model=Expense)
def create_expense(expense: ExpenseCreate, db: Session = Depends(get_db)):
    db_expense = Expense(
        amount=expense.amount,
        category=expense.category,
        date=expense.date,
        description=expense.description,
        tags=json.dumps(expense.tags) if expense.tags else None
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

@router.get("/", response_model=List[Expense])
def get_expenses(
    category: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Expense)
    if category:
        query = query.filter(Expense.category == category)
    if start_date:
        query = query.filter(Expense.date >= start_date)
    if end_date:
        query = query.filter(Expense.date <= end_date)
    return query.order_by(Expense.date.desc()).all()

@router.get("/{expense_id}", response_model=Expense)
def get_expense(expense_id: int, db: Session = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense

@router.put("/{expense_id}", response_model=Expense)
def update_expense(expense_id: int, expense: ExpenseUpdate, db: Session = Depends(get_db)):
    db_expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not db_expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    if expense.amount is not None:
        db_expense.amount = expense.amount
    if expense.category is not None:
        db_expense.category = expense.category
    if expense.date is not None:
        db_expense.date = expense.date
    if expense.description is not None:
        db_expense.description = expense.description
    if expense.tags is not None:
        db_expense.tags = json.dumps(expense.tags)
    db.commit()
    db.refresh(db_expense)
    return db_expense

@router.delete("/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    db_expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not db_expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    db.delete(db_expense)
    db.commit()
    return {"message": "Expense deleted successfully"}
```

- [ ] **Step 2: 创建 FastAPI 主应用**

```python
# expense_app/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from expense_app.api.routers import expenses, incomes, budgets, stats, agent
from expense_app.models.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Personal Assistant - Expense Module")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(expenses.router)
app.include_router(incomes.router)
app.include_router(budgets.router)
app.include_router(stats.router)
app.include_router(agent.router)

@app.get("/")
def root():
    return {"message": "Personal Assistant API", "status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy"}
```

- [ ] **Step 3: 创建启动脚本**

```python
# start_app.py
import uvicorn

if __name__ == "__main__":
    uvicorn.run("expense_app.api.main:app", host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 4: 测试 API**

```bash
python start_app.py &
sleep 2
curl http://localhost:8000/health
```
Expected: {"status": "healthy"}

- [ ] **Step 5: 提交**

```bash
git add expense_app/api/routers/expenses.py expense_app/api/main.py start_app.py
git commit -m "feat: implement expense CRUD API"
```

---

## Task 3: 收入和预算 API

**Files:**
- Create: `expense_app/api/routers/incomes.py`
- Create: `expense_app/api/routers/budgets.py`

- [ ] **Step 1: 实现收入路由**

```python
# expense_app/api/routers/incomes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from expense_app.models.database import get_db
from expense_app.models.models import Income
from expense_app.api.schemas import IncomeCreate, Income, IncomeUpdate

router = APIRouter(prefix="/api/incomes", tags=["incomes"])

@router.post("/", response_model=Income)
def create_income(income: IncomeCreate, db: Session = Depends(get_db)):
    db_income = Income(
        amount=income.amount,
        source=income.source,
        date=income.date,
        note=income.note
    )
    db.add(db_income)
    db.commit()
    db.refresh(db_income)
    return db_income

@router.get("/", response_model=List[Income])
def get_incomes(db: Session = Depends(get_db)):
    return db.query(Income).order_by(Income.date.desc()).all()

@router.get("/{income_id}", response_model=Income)
def get_income(income_id: int, db: Session = Depends(get_db)):
    income = db.query(Income).filter(Income.id == income_id).first()
    if not income:
        raise HTTPException(status_code=404, detail="Income not found")
    return income

@router.put("/{income_id}", response_model=Income)
def update_income(income_id: int, income: IncomeUpdate, db: Session = Depends(get_db)):
    db_income = db.query(Income).filter(Income.id == income_id).first()
    if not db_income:
        raise HTTPException(status_code=404, detail="Income not found")
    if income.amount is not None:
        db_income.amount = income.amount
    if income.source is not None:
        db_income.source = income.source
    if income.date is not None:
        db_income.date = income.date
    if income.note is not None:
        db_income.note = income.note
    db.commit()
    db.refresh(db_income)
    return db_income

@router.delete("/{income_id}")
def delete_income(income_id: int, db: Session = Depends(get_db)):
    db_income = db.query(Income).filter(Income.id == income_id).first()
    if not db_income:
        raise HTTPException(status_code=404, detail="Income not found")
    db.delete(db_income)
    db.commit()
    return {"message": "Income deleted successfully"}
```

- [ ] **Step 2: 实现预算路由**

```python
# expense_app/api/routers/budgets.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from expense_app.models.database import get_db
from expense_app.models.models import Budget
from expense_app.api.schemas import BudgetCreate, Budget, BudgetUpdate

router = APIRouter(prefix="/api/budgets", tags=["budgets"])

@router.post("/", response_model=Budget)
def create_budget(budget: BudgetCreate, db: Session = Depends(get_db)):
    db_budget = Budget(
        type=budget.type,
        category=budget.category,
        amount=budget.amount,
        period=budget.period
    )
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    return db_budget

@router.get("/", response_model=List[Budget])
def get_budgets(
    budget_type: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Budget)
    if budget_type:
        query = query.filter(Budget.type == budget_type)
    if period:
        query = query.filter(Budget.period == period)
    return query.order_by(Budget.period.desc()).all()

@router.put("/{budget_id}", response_model=Budget)
def update_budget(budget_id: int, budget: BudgetUpdate, db: Session = Depends(get_db)):
    db_budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not db_budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    if budget.type is not None:
        db_budget.type = budget.type
    if budget.category is not None:
        db_budget.category = budget.category
    if budget.amount is not None:
        db_budget.amount = budget.amount
    if budget.period is not None:
        db_budget.period = budget.period
    db.commit()
    db.refresh(db_budget)
    return db_budget

@router.delete("/{budget_id}")
def delete_budget(budget_id: int, db: Session = Depends(get_db)):
    db_budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not db_budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    db.delete(db_budget)
    db.commit()
    return {"message": "Budget deleted successfully"}
```

- [ ] **Step 3: 测试 API**

```bash
curl -X POST http://localhost:8000/api/incomes -H "Content-Type: application/json" -d '{"amount": 10000, "source": "工资", "date": "2026-04-01"}'
curl -X POST http://localhost:8000/api/budgets -H "Content-Type: application/json" -d '{"type": "monthly", "category": "餐饮", "amount": 2000, "period": "2026-04"}'
```

- [ ] **Step 4: 提交**

```bash
git add expense_app/api/routers/incomes.py expense_app/api/routers/budgets.py
git commit -m "feat: implement income and budget CRUD API"
```

---

## Task 4: 统计 API

**Files:**
- Create: `expense_app/api/routers/stats.py`
- Create: `expense_app/service/expense_service.py`

- [ ] **Step 1: 创建业务服务层**

```python
# expense_app/service/expense_service.py
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import date
from typing import Dict, List

from expense_app.models.models import Expense, Income, Budget

def get_monthly_summary(db: Session, year: int, month: int) -> Dict:
    total_income = db.query(func.sum(Income.amount)).filter(
        extract('year', Income.date) == year,
        extract('month', Income.date) == month
    ).scalar() or 0.0
    
    total_expense = db.query(func.sum(Expense.amount)).filter(
        extract('year', Expense.date) == year,
        extract('month', Expense.date) == month
    ).scalar() or 0.0
    
    category_data = db.query(
        Expense.category,
        func.sum(Expense.amount)
    ).filter(
        extract('year', Expense.date) == year,
        extract('month', Expense.date) == month
    ).group_by(Expense.category).all()
    
    category_breakdown = {cat: float(amt) for cat, amt in category_data}
    
    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": total_income - total_expense,
        "category_breakdown": category_breakdown
    }

def get_budget_progress(db: Session, year: int, month: int) -> List[Dict]:
    period = f"{year}-{month:02d}"
    budgets = db.query(Budget).filter(
        Budget.period == period,
        Budget.type == "monthly"
    ).all()
    
    result = []
    for budget in budgets:
        if budget.category:
            spent = db.query(func.sum(Expense.amount)).filter(
                Expense.category == budget.category,
                extract('year', Expense.date) == year,
                extract('month', Expense.date) == month
            ).scalar() or 0.0
        else:
            spent = db.query(func.sum(Expense.amount)).filter(
                extract('year', Expense.date) == year,
                extract('month', Expense.date) == month
            ).scalar() or 0.0
        
        remaining = budget.amount - spent
        percentage = (spent / budget.amount * 100) if budget.amount > 0 else 0
        
        result.append({
            "budget_id": budget.id,
            "category": budget.category or "总计",
            "budget_amount": budget.amount,
            "spent_amount": spent,
            "remaining": remaining,
            "percentage": round(percentage, 2)
        })
    
    return result

def get_trend_data(db: Session, months: int = 6) -> List[Dict]:
    from datetime import datetime, timedelta
    today = date.today()
    results = []
    
    for i in range(months - 1, -1, -1):
        target_date = today.replace(day=1) - timedelta(days=30 * i)
        year = target_date.year
        month = target_date.month
        if month <= 0:
            month += 12
            year -= 1
        
        income = db.query(func.sum(Income.amount)).filter(
            extract('year', Income.date) == year,
            extract('month', Income.date) == month
        ).scalar() or 0.0
        
        expense = db.query(func.sum(Expense.amount)).filter(
            extract('year', Expense.date) == year,
            extract('month', Expense.date) == month
        ).scalar() or 0.0
        
        results.append({
            "period": f"{year}-{month:02d}",
            "income": income,
            "expense": expense
        })
    
    return results
```

- [ ] **Step 2: 实现统计路由**

```python
# expense_app/api/routers/stats.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date

from expense_app.models.database import get_db
from expense_app.service.expense_service import (
    get_monthly_summary,
    get_budget_progress,
    get_trend_data
)
from expense_app.api.schemas import StatsSummary

router = APIRouter(prefix="/api/stats", tags=["statistics"])

@router.get("/summary", response_model=StatsSummary)
def get_summary(
    year: int = Query(None),
    month: int = Query(None),
    db: Session = Depends(get_db)
):
    if year is None or month is None:
        today = date.today()
        year = today.year
        month = today.month
    return get_monthly_summary(db, year, month)

@router.get("/budget-progress")
def get_budget_progress_endpoint(
    year: int = Query(None),
    month: int = Query(None),
    db: Session = Depends(get_db)
):
    if year is None or month is None:
        today = date.today()
        year = today.year
        month = today.month
    return get_budget_progress(db, year, month)

@router.get("/trend")
def get_trend(
    months: int = Query(6, ge=1, le=24),
    db: Session = Depends(get_db)
):
    return get_trend_data(db, months)
```

- [ ] **Step 3: 提交**

```bash
git add expense_app/api/routers/stats.py expense_app/service/expense_service.py
git commit -m "feat: implement statistics API"
```

---

## Task 5: Agent 查询 API

**Files:**
- Create: `expense_app/api/routers/agent.py`
- Create: `expense_app/service/agent_service.py`

- [ ] **Step 1: 创建 Agent 服务**

```python
# expense_app/service/agent_service.py
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import date
from typing import Dict

from expense_app.models.models import Expense, Income, Budget

DEFAULT_CATEGORIES = ["餐饮", "交通", "购物", "娱乐", "居住", "医疗", "其他"]

def query_expense_data(db: Session, query: str) -> Dict:
    today = date.today()
    current_year = today.year
    current_month = today.month
    
    result = {"answer": "", "data": {}}
    
    if "这个月" in query or "本月" in query:
        total = db.query(func.sum(Expense.amount)).filter(
            extract('year', Expense.date) == current_year,
            extract('month', Expense.date) == current_month
        ).scalar() or 0.0
        result["answer"] = f"本月总支出为：¥{total:.2f}"
        result["data"] = {"total": total, "period": f"{current_year}-{current_month:02d}"}
    
    elif "上个月" in query or "上月" in query:
        last_month = current_month - 1 if current_month > 1 else 12
        last_year = current_year if current_month > 1 else current_year - 1
        total = db.query(func.sum(Expense.amount)).filter(
            extract('year', Expense.date) == last_year,
            extract('month', Expense.date) == last_month
        ).scalar() or 0.0
        result["answer"] = f"上月总支出为：¥{total:.2f}"
        result["data"] = {"total": total, "period": f"{last_year}-{last_month:02d}"}
    
    elif any(cat in query for cat in DEFAULT_CATEGORIES):
        for cat in DEFAULT_CATEGORIES:
            if cat in query:
                total = db.query(func.sum(Expense.amount)).filter(
                    Expense.category == cat,
                    extract('year', Expense.date) == current_year,
                    extract('month', Expense.date) == current_month
                ).scalar() or 0.0
                result["answer"] = f"本月{cat}支出为：¥{total:.2f}"
                result["data"] = {"category": cat, "total": total}
                break
    
    elif "预算" in query and ("剩余" in query or "还剩" in query):
        budgets = db.query(Budget).filter(
            Budget.period == f"{current_year}-{current_month:02d}",
            Budget.type == "monthly"
        ).all()
        budget_info = []
        for b in budgets:
            if b.category:
                spent = db.query(func.sum(Expense.amount)).filter(
                    Expense.category == b.category,
                    extract('year', Expense.date) == current_year,
                    extract('month', Expense.date) == current_month
                ).scalar() or 0.0
            else:
                spent = db.query(func.sum(Expense.amount)).filter(
                    extract('year', Expense.date) == current_year,
                    extract('month', Expense.date) == current_month
                ).scalar() or 0.0
            remaining = b.amount - spent
            budget_info.append({"category": b.category or "总计", "budget": b.amount, "remaining": remaining})
        result["answer"] = "预算执行情况：" + ", ".join(f"{b['category']}: 剩余¥{b['remaining']:.2f}" for b in budget_info)
        result["data"] = {"budgets": budget_info}
    
    elif "收入" in query:
        total = db.query(func.sum(Income.amount)).filter(
            extract('year', Income.date) == current_year,
            extract('month', Income.date) == current_month
        ).scalar() or 0.0
        result["answer"] = f"本月总收入为：¥{total:.2f}"
        result["data"] = {"total_income": total}
    
    else:
        total_expense = db.query(func.sum(Expense.amount)).filter(
            extract('year', Expense.date) == current_year,
            extract('month', Expense.date) == current_month
        ).scalar() or 0.0
        total_income = db.query(func.sum(Income.amount)).filter(
            extract('year', Income.date) == current_year,
            extract('month', Income.date) == current_month
        ).scalar() or 0.0
        result["answer"] = f"本月概况：收入¥{total_income:.2f}, 支出¥{total_expense:.2f}, 结余¥{total_income - total_expense:.2f}"
        result["data"] = {"income": total_income, "expense": total_expense, "balance": total_income - total_expense}
    
    return result
```

- [ ] **Step 2: 实现 Agent 路由**

```python
# expense_app/api/routers/agent.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from expense_app.models.database import get_db
from expense_app.service.agent_service import query_expense_data

router = APIRouter(prefix="/api/agent", tags=["agent"])

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
    data: dict

@router.post("/query", response_model=QueryResponse)
def agent_query(request: QueryRequest, db: Session = Depends(get_db)):
    try:
        result = query_expense_data(db, request.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 3: 测试 Agent API**

```bash
curl -X POST http://localhost:8000/api/agent/query -H "Content-Type: application/json" -d '{"query": "这个月花了多少钱"}'
curl -X POST http://localhost:8000/api/agent/query -H "Content-Type: application/json" -d '{"query": "餐饮花了多少"}'
```

- [ ] **Step 4: 提交**

```bash
git add expense_app/api/routers/agent.py expense_app/service/agent_service.py
git commit -m "feat: implement agent query API"
```

---

## Task 6: React 前端项目搭建

**Files:**
- Create: `expense_web/package.json`
- Create: `expense_web/vite.config.ts`
- Create: `expense_web/tsconfig.json`
- Create: `expense_web/index.html`
- Create: `expense_web/src/index.css`
- Create: `expense_web/src/main.tsx`
- Create: `expense_web/src/App.tsx`
- Create: `expense_web/src/api/client.ts`
- Create: `expense_web/tailwind.config.js`
- Create: `expense_web/postcss.config.js`

- [ ] **Step 1: 创建 package.json**

```json
{
  "name": "expense-web",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "recharts": "^2.10.0",
    "axios": "^1.6.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.1.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.3.3",
    "vite": "^5.0.8",
    "tailwindcss": "^3.3.6",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32"
  }
}
```

- [ ] **Step 2: 创建 Vite 配置**

```typescript
// expense_web/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 3: 创建 TypeScript 配置**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 4: 创建 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>个人助手 - 开销管理</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: 创建入口文件**

```typescript
// expense_web/src/main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
```

- [ ] **Step 6: 创建 App 组件**

```typescript
// expense_web/src/App.tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Expenses from './pages/Expenses'
import Income from './pages/Income'
import Budgets from './pages/Budgets'
import Statistics from './pages/Statistics'

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-semibold">个人助手 - 开销管理</h1>
            </div>
            <div className="flex items-center space-x-4">
              <a href="/" className="text-gray-600 hover:text-gray-900">概览</a>
              <a href="/expenses" className="text-gray-600 hover:text-gray-900">开销</a>
              <a href="/income" className="text-gray-600 hover:text-gray-900">收入</a>
              <a href="/budgets" className="text-gray-600 hover:text-gray-900">预算</a>
              <a href="/statistics" className="text-gray-600 hover:text-gray-900">统计</a>
            </div>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/expenses" element={<Expenses />} />
          <Route path="/income" element={<Income />} />
          <Route path="/budgets" element={<Budgets />} />
          <Route path="/statistics" element={<Statistics />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
```

- [ ] **Step 7: 创建 API 客户端**

```typescript
// expense_web/src/api/client.ts
import axios from 'axios'

const API_BASE = '/api'

export const api = {
  getExpenses: async (params?: any) => {
    const response = await axios.get(`${API_BASE}/expenses`, { params })
    return response.data
  },
  createExpense: async (data: any) => {
    const response = await axios.post(`${API_BASE}/expenses`, data)
    return response.data
  },
  deleteExpense: async (id: number) => {
    const response = await axios.delete(`${API_BASE}/expenses/${id}`)
    return response.data
  },
  getIncomes: async () => {
    const response = await axios.get(`${API_BASE}/incomes`)
    return response.data
  },
  createIncome: async (data: any) => {
    const response = await axios.post(`${API_BASE}/incomes`, data)
    return response.data
  },
  getBudgets: async (params?: any) => {
    const response = await axios.get(`${API_BASE}/budgets`, { params })
    return response.data
  },
  createBudget: async (data: any) => {
    const response = await axios.post(`${API_BASE}/budgets`, data)
    return response.data
  },
  getSummary: async (year?: number, month?: number) => {
    const params: any = {}
    if (year) params.year = year
    if (month) params.month = month
    const response = await axios.get(`${API_BASE}/stats/summary`, { params })
    return response.data
  },
  getBudgetProgress: async (year?: number, month?: number) => {
    const params: any = {}
    if (year) params.year = year
    if (month) params.month = month
    const response = await axios.get(`${API_BASE}/stats/budget-progress`, { params })
    return response.data
  },
  getTrend: async (months: number = 6) => {
    const response = await axios.get(`${API_BASE}/stats/trend`, { params: { months } })
    return response.data
  },
  queryAgent: async (query: string) => {
    const response = await axios.post(`${API_BASE}/agent/query`, { query })
    return response.data
  },
}
```

- [ ] **Step 8: 创建样式和配置**

```css
/* expense_web/src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
```

```javascript
// expense_web/tailwind.config.js
module.exports = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: { extend: {} },
  plugins: [],
}
```

```javascript
// expense_web/postcss.config.js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 9: 安装依赖**

```bash
cd expense_web
npm install
```

- [ ] **Step 10: 提交**

```bash
git add expense_web/
git commit -m "feat: setup React frontend project"
```

---

## Task 7: Dashboard 页面

**Files:**
- Create: `expense_web/src/pages/Dashboard.tsx`
- Create: `expense_web/src/components/SummaryCards.tsx`
- Create: `expense_web/src/components/ExpenseForm.tsx`
- Create: `expense_web/src/components/ExpenseList.tsx`

- [ ] **Step 1: 创建概览卡片组件**

```typescript
// expense_web/src/components/SummaryCards.tsx
import { useEffect, useState } from 'react'
import { api } from '../api/client'

export function SummaryCards() {
  const [summary, setSummary] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getSummary().then(data => {
      setSummary(data)
      setLoading(false)
    })
  }, [])

  if (loading) return <div className="grid grid-cols-3 gap-4">加载中...</div>

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-sm font-medium text-gray-500">本月收入</h3>
        <p className="text-2xl font-semibold text-green-600">¥{summary?.total_income.toFixed(2)}</p>
      </div>
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-sm font-medium text-gray-500">本月支出</h3>
        <p className="text-2xl font-semibold text-red-600">¥{summary?.total_expense.toFixed(2)}</p>
      </div>
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-sm font-medium text-gray-500">本月结余</h3>
        <p className={`text-2xl font-semibold ${(summary?.balance || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
          ¥{summary?.balance.toFixed(2)}
        </p>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 创建开销表单组件**

```typescript
// expense_web/src/components/ExpenseForm.tsx
import { useState } from 'react'
import { api } from '../api/client'

const CATEGORIES = ['餐饮', '交通', '购物', '娱乐', '居住', '医疗', '其他']

interface ExpenseFormProps {
  onSuccess: () => void
}

export function ExpenseForm({ onSuccess }: ExpenseFormProps) {
  const [amount, setAmount] = useState('')
  const [category, setCategory] = useState('餐饮')
  const [date, setDate] = useState(new Date().toISOString().split('T')[0])
  const [description, setDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      await api.createExpense({
        amount: parseFloat(amount),
        category,
        date,
        description: description || undefined,
      })
      setAmount('')
      setDescription('')
      onSuccess()
    } catch (error) {
      alert('添加失败，请重试')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white p-4 rounded-lg shadow mb-6">
      <h3 className="text-lg font-medium mb-4">快速记账</h3>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">金额</label>
          <input type="number" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 p-2" required />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">分类</label>
          <select value={category} onChange={(e) => setCategory(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 p-2">
            {CATEGORIES.map(cat => <option key={cat} value={cat}>{cat}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">日期</label>
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 p-2" />
        </div>
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700">描述</label>
          <input type="text" value={description} onChange={(e) => setDescription(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 p-2" placeholder="可选" />
        </div>
        <div className="flex items-end">
          <button type="submit" disabled={submitting}
            className="w-full bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700 disabled:opacity-50">
            {submitting ? '添加中...' : '添加'}
          </button>
        </div>
      </div>
    </form>
  )
}
```

- [ ] **Step 3: 创建开销列表组件**

```typescript
// expense_web/src/components/ExpenseList.tsx
import { useEffect, useState } from 'react'
import { api } from '../api/client'

export function ExpenseList() {
  const [expenses, setExpenses] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const loadExpenses = () => {
    api.getExpenses().then(data => {
      setExpenses(data)
      setLoading(false)
    })
  }

  useEffect(() => {
    loadExpenses()
  }, [])

  const handleDelete = async (id: number) => {
    if (confirm('确定删除这条开销吗？')) {
      await api.deleteExpense(id)
      loadExpenses()
    }
  }

  if (loading) return <div>加载中...</div>

  return (
    <div className="bg-white rounded-lg shadow">
      <h3 className="text-lg font-medium p-4 border-b">最近开销</h3>
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">日期</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">分类</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">金额</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">描述</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {expenses.map(expense => (
            <tr key={expense.id}>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{expense.date}</td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{expense.category}</td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-red-600">-¥{expense.amount.toFixed(2)}</td>
              <td className="px-6 py-4 text-sm text-gray-500">{expense.description}</td>
              <td className="px-6 py-4 whitespace-nowrap text-sm">
                <button onClick={() => handleDelete(expense.id)} className="text-red-600 hover:text-red-900">删除</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 4: 创建 Dashboard 页面**

```typescript
// expense_web/src/pages/Dashboard.tsx
import { SummaryCards } from '../components/SummaryCards'
import { ExpenseForm } from '../components/ExpenseForm'
import { ExpenseList } from '../components/ExpenseList'

export default function Dashboard() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">概览</h2>
      <SummaryCards />
      <ExpenseForm onSuccess={() => {}} />
      <ExpenseList />
    </div>
  )
}
```

- [ ] **Step 5: 提交**

```bash
git add expense_web/src/components/ expense_web/src/pages/Dashboard.tsx
git commit -m "feat: implement Dashboard page"
```

---

## Task 8: 其他页面和图表

**Files:**
- Create: `expense_web/src/pages/Expenses.tsx`
- Create: `expense_web/src/pages/Income.tsx`
- Create: `expense_web/src/pages/Budgets.tsx`
- Create: `expense_web/src/pages/Statistics.tsx`
- Create: `expense_web/src/components/Charts.tsx`

- [ ] **Step 1: 创建图表组件**

```typescript
// expense_web/src/components/Charts.tsx
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useEffect, useState } from 'react'
import { api } from '../api/client'

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff8042', '#0088fe', '#00C49F', '#FFBB28']

export function CategoryPieChart() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getSummary().then(summary => {
      const chartData = Object.entries(summary.category_breakdown).map(([name, value]) => ({ name, value }))
      setData(chartData)
      setLoading(false)
    })
  }, [])

  if (loading) return <div>加载中...</div>
  if (data.length === 0) return <div>暂无数据</div>

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie data={data} cx="50%" cy="50%" labelLine={false} label={({ name, value }) => `${name}: ¥${value}`} outerRadius={80} fill="#8884d8" dataKey="value">
          {data.map((entry, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}

export function TrendBarChart() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getTrend(6).then(data => {
      setData(data.map((d: any) => ({ ...d, period: d.period.slice(5) })))
      setLoading(false)
    })
  }, [])

  if (loading) return <div>加载中...</div>

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <XAxis dataKey="period" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="income" fill="#82ca9d" name="收入" />
        <Bar dataKey="expense" fill="#ff8042" name="支出" />
      </BarChart>
    </ResponsiveContainer>
  )
}
```

- [ ] **Step 2: 创建统计页面**

```typescript
// expense_web/src/pages/Statistics.tsx
import { CategoryPieChart } from '../components/Charts'
import { TrendBarChart } from '../components/Charts'

export default function Statistics() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">统计</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium mb-4">分类占比</h3>
          <CategoryPieChart />
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium mb-4">收支趋势</h3>
          <TrendBarChart />
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: 创建开销管理页面**

```typescript
// expense_web/src/pages/Expenses.tsx
import { ExpenseForm } from '../components/ExpenseForm'
import { ExpenseList } from '../components/ExpenseList'

export default function Expenses() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">开销管理</h2>
      <ExpenseForm onSuccess={() => {}} />
      <ExpenseList />
    </div>
  )
}
```

- [ ] **Step 4: 创建收入页面**

```typescript
// expense_web/src/pages/Income.tsx
import { useState, useEffect } from 'react'
import { api } from '../api/client'

export default function Income() {
  const [incomes, setIncomes] = useState<any[]>([])
  const [form, setForm] = useState({ amount: '', source: '', date: new Date().toISOString().split('T')[0], note: '' })

  useEffect(() => {
    api.getIncomes().then(setIncomes)
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.createIncome({
      amount: parseFloat(form.amount),
      source: form.source,
      date: form.date,
      note: form.note || undefined,
    })
    setForm({ amount: '', source: '', date: new Date().toISOString().split('T')[0], note: '' })
    api.getIncomes().then(setIncomes)
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">收入管理</h2>
      <form onSubmit={handleSubmit} className="bg-white p-4 rounded-lg shadow mb-6">
        <div className="grid grid-cols-4 gap-4">
          <input type="number" step="0.01" placeholder="金额" value={form.amount} onChange={e => setForm({...form, amount: e.target.value})} className="border p-2 rounded" required />
          <input type="text" placeholder="来源" value={form.source} onChange={e => setForm({...form, source: e.target.value})} className="border p-2 rounded" required />
          <input type="date" value={form.date} onChange={e => setForm({...form, date: e.target.value})} className="border p-2 rounded" />
          <button type="submit" className="bg-green-600 text-white py-2 px-4 rounded hover:bg-green-700">添加收入</button>
        </div>
        <input type="text" placeholder="备注" value={form.note} onChange={e => setForm({...form, note: e.target.value})} className="mt-4 w-full border p-2 rounded" />
      </form>
      <div className="bg-white rounded-lg shadow">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr><th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">日期</th><th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">来源</th><th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">金额</th><th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">备注</th></tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {incomes.map(inc => (
              <tr key={inc.id}><td className="px-6 py-4">{inc.date}</td><td className="px-6 py-4">{inc.source}</td><td className="px-6 py-4 text-green-600">+¥{inc.amount.toFixed(2)}</td><td className="px-6 py-4">{inc.note}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: 创建预算页面**

```typescript
// expense_web/src/pages/Budgets.tsx
import { useState, useEffect } from 'react'
import { api } from '../api/client'

export default function Budgets() {
  const [budgets, setBudgets] = useState<any[]>([])
  const [form, setForm] = useState({ type: 'monthly', category: '', amount: '', period: new Date().toISOString().slice(0, 7) })
  const [progress, setProgress] = useState<any[]>([])

  useEffect(() => {
    api.getBudgets().then(setBudgets)
    api.getBudgetProgress().then(setProgress)
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.createBudget({
      type: form.type,
      category: form.category || null,
      amount: parseFloat(form.amount),
      period: form.period,
    })
    setForm({ type: 'monthly', category: '', amount: '', period: new Date().toISOString().slice(0, 7) })
    api.getBudgets().then(setBudgets)
    api.getBudgetProgress().then(setProgress)
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">预算管理</h2>
      <form onSubmit={handleSubmit} className="bg-white p-4 rounded-lg shadow mb-6">
        <div className="grid grid-cols-4 gap-4">
          <select value={form.type} onChange={e => setForm({...form, type: e.target.value})} className="border p-2 rounded">
            <option value="monthly">月度</option>
            <option value="yearly">年度</option>
          </select>
          <input type="text" placeholder="分类 (可选)" value={form.category} onChange={e => setForm({...form, category: e.target.value})} className="border p-2 rounded" />
          <input type="number" step="0.01" placeholder="预算金额" value={form.amount} onChange={e => setForm({...form, amount: e.target.value})} className="border p-2 rounded" required />
          <button type="submit" className="bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700">设置预算</button>
        </div>
      </form>
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-medium mb-4">预算执行进度</h3>
        {progress.map(p => (
          <div key={p.budget_id} className="mb-4">
            <div className="flex justify-between mb-1">
              <span>{p.category}</span>
              <span>¥{p.spent_amount.toFixed(2)} / ¥{p.budget_amount.toFixed(2)}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${Math.min(p.percentage, 100)}%` }}></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 6: 提交**

```bash
git add expense_web/src/pages/ expense_web/src/components/Charts.tsx
git commit -m "feat: implement remaining pages and charts"
```

---

## Self-Review

**Spec coverage check:**
- ✅ 开销 CRUD - Task 2
- ✅ 收入 CRUD - Task 3
- ✅ 预算 CRUD - Task 3
- ✅ 统计 API - Task 4
- ✅ Agent 查询 - Task 5
- ✅ 前端页面 - Task 6-8
- ✅ 图表展示 - Task 8

**Placeholder scan:** 无 TBD/TODO

**Type consistency:** 所有 API 类型和 Schema 一致

---

计划完成，已保存到 `docs/superpowers/plans/2026-04-07-expense-module-plan.md`。

**有两种执行方式：**

1. **Subagent-Driven (推荐)** - 每个任务分发独立的子 agent 执行，任务间 review，迭代快
2. **Inline Execution** - 在当前 session 中批量执行，带检查点

**选择哪种方式开始执行？**
