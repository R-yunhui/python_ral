"""
预算管理路由模块

提供预算设置的 CRUD 接口：
- POST /api/budgets - 创建预算
- GET /api/budgets - 获取预算列表
- GET /api/budgets/{id} - 获取单个预算
- PUT /api/budgets/{id} - 更新预算
- DELETE /api/budgets/{id} - 删除预算
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from expense_app.models.database import get_db
from expense_app.models.models import Budget as BudgetModel
from expense_app.api.schemas import BudgetCreate, BudgetUpdate, Budget

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


@router.post("/", response_model=Budget, status_code=status.HTTP_201_CREATED)
def create_budget(budget: BudgetCreate, db: Session = Depends(get_db)):
    """
    创建新的预算设置

    Args:
        budget: 预算创建请求体
        db: 数据库会话

    Returns:
        Budget: 创建的预算记录
    """
    try:
        db_budget = BudgetModel(
            type=budget.budget_type,
            category=budget.category,
            amount=budget.amount,
            period=budget.period
        )
        db.add(db_budget)
        db.commit()
        db.refresh(db_budget)
        logger.info(f"Created budget: id={db_budget.id}, type={db_budget.type}, period={db_budget.period}")
        return db_budget
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create budget: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create budget: {str(e)}")


@router.get("/", response_model=List[Budget])
def get_budgets(
    budget_type: Optional[str] = Query(None, description="预算类型 (monthly/yearly)"),
    period: Optional[str] = Query(None, description="预算周期"),
    db: Session = Depends(get_db)
):
    """
    获取预算列表（支持筛选）

    Args:
        budget_type: 按类型筛选（可选）
        period: 按周期筛选（可选）
        db: 数据库会话

    Returns:
        List[Budget]: 预算列表
    """
    try:
        query = db.query(BudgetModel)

        if budget_type:
            query = query.filter(BudgetModel.type == budget_type)
        if period:
            query = query.filter(BudgetModel.period == period)

        results = query.order_by(BudgetModel.period.desc()).all()
        logger.info(f"Retrieved {len(results)} budgets")
        return results
    except Exception as e:
        logger.error(f"Failed to retrieve budgets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve budgets: {str(e)}")


@router.get("/{budget_id}", response_model=Budget)
def get_budget(budget_id: int, db: Session = Depends(get_db)):
    """
    获取单个预算记录详情
    """
    budget = db.query(BudgetModel).filter(BudgetModel.id == budget_id).first()
    if not budget:
        logger.warning(f"Budget not found: id={budget_id}")
        raise HTTPException(status_code=404, detail="Budget not found")

    logger.info(f"Retrieved budget: id={budget_id}")
    return budget


@router.put("/{budget_id}", response_model=Budget)
def update_budget(budget_id: int, budget: BudgetUpdate, db: Session = Depends(get_db)):
    """
    更新预算设置
    """
    db_budget = db.query(BudgetModel).filter(BudgetModel.id == budget_id).first()
    if not db_budget:
        logger.warning(f"Budget not found: id={budget_id}")
        raise HTTPException(status_code=404, detail="Budget not found")

    try:
        if budget.budget_type is not None:
            db_budget.type = budget.budget_type
        if budget.category is not None:
            db_budget.category = budget.category
        if budget.amount is not None:
            db_budget.amount = budget.amount
        if budget.period is not None:
            db_budget.period = budget.period

        db.commit()
        db.refresh(db_budget)
        logger.info(f"Updated budget: id={db_budget.id}")
        return db_budget
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update budget: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update budget: {str(e)}")


@router.delete("/{budget_id}")
def delete_budget(budget_id: int, db: Session = Depends(get_db)):
    """
    删除预算设置
    """
    db_budget = db.query(BudgetModel).filter(BudgetModel.id == budget_id).first()
    if not db_budget:
        logger.warning(f"Budget not found: id={budget_id}")
        raise HTTPException(status_code=404, detail="Budget not found")

    try:
        db.delete(db_budget)
        db.commit()
        logger.info(f"Deleted budget: id={budget_id}")
        return {"message": "Budget deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete budget: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete budget: {str(e)}")
