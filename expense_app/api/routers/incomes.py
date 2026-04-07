"""
收入管理路由模块

提供收入记录的 CRUD 接口：
- POST /api/incomes - 创建收入
- GET /api/incomes - 获取收入列表
- GET /api/incomes/{id} - 获取单个收入
- PUT /api/incomes/{id} - 更新收入
- DELETE /api/incomes/{id} - 删除收入
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from expense_app.models.database import get_db
from expense_app.models.models import Income as IncomeModel
from expense_app.api.schemas import IncomeCreate, IncomeUpdate, Income

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/incomes", tags=["incomes"])


@router.post("/", response_model=Income, status_code=status.HTTP_201_CREATED)
def create_income(income: IncomeCreate, db: Session = Depends(get_db)):
    """
    创建新的收入记录

    Args:
        income: 收入创建请求体
        db: 数据库会话

    Returns:
        Income: 创建的收入记录
    """
    try:
        db_income = IncomeModel(
            amount=income.amount,
            source=income.source,
            date=income.record_date,
            note=income.note
        )
        db.add(db_income)
        db.commit()
        db.refresh(db_income)
        logger.info(f"Created income: id={db_income.id}, amount={db_income.amount}, source={db_income.source}")
        return db_income
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create income: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create income: {str(e)}")


@router.get("/", response_model=List[Income])
def get_incomes(db: Session = Depends(get_db)):
    """
    获取收入列表

    Returns:
        List[Income]: 收入列表
    """
    try:
        results = db.query(IncomeModel).order_by(IncomeModel.date.desc()).all()
        logger.info(f"Retrieved {len(results)} incomes")
        return results
    except Exception as e:
        logger.error(f"Failed to retrieve incomes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve incomes: {str(e)}")


@router.get("/{income_id}", response_model=Income)
def get_income(income_id: int, db: Session = Depends(get_db)):
    """
    获取单个收入记录详情
    """
    income = db.query(IncomeModel).filter(IncomeModel.id == income_id).first()
    if not income:
        logger.warning(f"Income not found: id={income_id}")
        raise HTTPException(status_code=404, detail="Income not found")

    logger.info(f"Retrieved income: id={income_id}")
    return income


@router.put("/{income_id}", response_model=Income)
def update_income(income_id: int, income: IncomeUpdate, db: Session = Depends(get_db)):
    """
    更新收入记录
    """
    db_income = db.query(IncomeModel).filter(IncomeModel.id == income_id).first()
    if not db_income:
        logger.warning(f"Income not found: id={income_id}")
        raise HTTPException(status_code=404, detail="Income not found")

    try:
        if income.amount is not None:
            db_income.amount = income.amount
        if income.source is not None:
            db_income.source = income.source
        if income.record_date is not None:
            db_income.date = income.record_date
        if income.note is not None:
            db_income.note = income.note

        db.commit()
        db.refresh(db_income)
        logger.info(f"Updated income: id={db_income.id}")
        return db_income
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update income: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update income: {str(e)}")


@router.delete("/{income_id}")
def delete_income(income_id: int, db: Session = Depends(get_db)):
    """
    删除收入记录
    """
    db_income = db.query(IncomeModel).filter(IncomeModel.id == income_id).first()
    if not db_income:
        logger.warning(f"Income not found: id={income_id}")
        raise HTTPException(status_code=404, detail="Income not found")

    try:
        db.delete(db_income)
        db.commit()
        logger.info(f"Deleted income: id={income_id}")
        return {"message": "Income deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete income: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete income: {str(e)}")
