"""
统计查询路由模块

提供统计数据接口：
- GET /api/stats/summary - 月度收支汇总
- GET /api/stats/budget-progress - 预算执行进度
- GET /api/stats/trend - 收支趋势
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
import logging

from expense_app.models.database import get_db
from expense_app.service.expense_service import (
    get_monthly_summary,
    get_budget_progress,
    get_trend_data
)
from expense_app.api.schemas import StatsSummary, BudgetProgress

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stats", tags=["statistics"])


@router.get("/summary", response_model=StatsSummary)
def get_summary(
    year: int = Query(None, description="年份"),
    month: int = Query(None, description="月份"),
    db: Session = Depends(get_db)
):
    """
    获取月度收支汇总

    Args:
        year: 年份（可选，默认当前年）
        month: 月份（可选，默认当前月）
        db: 数据库会话

    Returns:
        StatsSummary: 收支汇总数据
    """
    if year is None or month is None:
        today = date.today()
        year = today.year
        month = today.month
        logger.info(f"No date provided, using current: {year}-{month}")

    return get_monthly_summary(db, year, month)


@router.get("/budget-progress", response_model=list[BudgetProgress])
def get_budget_progress_endpoint(
    year: int = Query(None, description="年份"),
    month: int = Query(None, description="月份"),
    db: Session = Depends(get_db)
):
    """
    获取预算执行进度

    Args:
        year: 年份（可选，默认当前年）
        month: 月份（可选，默认当前月）
        db: 数据库会话

    Returns:
        List[BudgetProgress]: 预算执行进度列表
    """
    if year is None or month is None:
        today = date.today()
        year = today.year
        month = today.month
        logger.info(f"No date provided, using current: {year}-{month}")

    return get_budget_progress(db, year, month)


@router.get("/trend")
def get_trend(
    months: int = Query(6, ge=1, le=24, description="获取最近几个月的数据"),
    db: Session = Depends(get_db)
):
    """
    获取月度收支趋势

    Args:
        months: 获取最近几个月的数据（1-24，默认 6）
        db: 数据库会话

    Returns:
        List[Dict]: 趋势数据列表
    """
    return get_trend_data(db, months)
