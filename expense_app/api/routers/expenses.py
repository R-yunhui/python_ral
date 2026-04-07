"""
开销管理路由模块

提供开销记录的 CRUD 接口：
- POST /api/expenses - 创建开销
- GET /api/expenses - 获取开销列表
- GET /api/expenses/{id} - 获取单个开销
- PUT /api/expenses/{id} - 更新开销
- DELETE /api/expenses/{id} - 删除开销
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import json
import logging

from expense_app.models.database import get_db
from expense_app.models.models import Expense as ExpenseModel
from expense_app.api.schemas import ExpenseCreate, ExpenseUpdate, Expense

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/expenses", tags=["expenses"])


@router.post("/", response_model=Expense, status_code=status.HTTP_201_CREATED)
def create_expense(expense: ExpenseCreate, db: Session = Depends(get_db)):
    """
    创建新的开销记录

    Args:
        expense: 开销创建请求体
        db: 数据库会话

    Returns:
        Expense: 创建的开销记录
    """
    try:
        db_expense = ExpenseModel(
            amount=expense.amount,
            category=expense.category,
            date=expense.record_date,
            description=expense.description,
            tags=json.dumps(expense.tags) if expense.tags else None
        )
        db.add(db_expense)
        db.commit()
        db.refresh(db_expense)
        logger.info(f"Created expense: id={db_expense.id}, amount={db_expense.amount}, category={db_expense.category}")
        return db_expense
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create expense: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create expense: {str(e)}")


@router.get("/", response_model=List[Expense])
def get_expenses(
    category: Optional[str] = Query(None, description="按分类筛选"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: Session = Depends(get_db)
):
    """
    获取开销列表（支持筛选）

    Args:
        category: 按分类筛选（可选）
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
        db: 数据库会话

    Returns:
        List[Expense]: 开销列表
    """
    try:
        query = db.query(ExpenseModel)

        if category:
            query = query.filter(ExpenseModel.category == category)

        if start_date:
            query = query.filter(ExpenseModel.date >= start_date)

        if end_date:
            query = query.filter(ExpenseModel.date <= end_date)

        results = query.order_by(ExpenseModel.date.desc()).all()
        logger.info(f"Retrieved {len(results)} expenses")
        return results
    except Exception as e:
        logger.error(f"Failed to retrieve expenses: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve expenses: {str(e)}")


@router.get("/{expense_id}", response_model=Expense)
def get_expense(expense_id: int, db: Session = Depends(get_db)):
    """
    获取单个开销记录详情
    """
    expense = db.query(ExpenseModel).filter(ExpenseModel.id == expense_id).first()
    if not expense:
        logger.warning(f"Expense not found: id={expense_id}")
        raise HTTPException(status_code=404, detail="Expense not found")

    logger.info(f"Retrieved expense: id={expense_id}")
    return expense


@router.put("/{expense_id}", response_model=Expense)
def update_expense(expense_id: int, expense: ExpenseUpdate, db: Session = Depends(get_db)):
    """
    更新开销记录
    """
    db_expense = db.query(ExpenseModel).filter(ExpenseModel.id == expense_id).first()
    if not db_expense:
        logger.warning(f"Expense not found: id={expense_id}")
        raise HTTPException(status_code=404, detail="Expense not found")

    try:
        if expense.amount is not None:
            db_expense.amount = expense.amount
        if expense.category is not None:
            db_expense.category = expense.category
        if expense.record_date is not None:
            db_expense.date = expense.record_date
        if expense.description is not None:
            db_expense.description = expense.description
        if expense.tags is not None:
            db_expense.tags = json.dumps(expense.tags)

        db.commit()
        db.refresh(db_expense)
        logger.info(f"Updated expense: id={db_expense.id}")
        return db_expense
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update expense: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update expense: {str(e)}")


@router.delete("/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    """
    删除开销记录
    """
    db_expense = db.query(ExpenseModel).filter(ExpenseModel.id == expense_id).first()
    if not db_expense:
        logger.warning(f"Expense not found: id={expense_id}")
        raise HTTPException(status_code=404, detail="Expense not found")

    try:
        db.delete(db_expense)
        db.commit()
        logger.info(f"Deleted expense: id={expense_id}")
        return {"message": "Expense deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete expense: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete expense: {str(e)}")
