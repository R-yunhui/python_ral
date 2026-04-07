"""
开销业务服务层

提供开销数据统计相关的业务逻辑：
- 月度收支汇总
- 预算执行进度
- 收支趋势分析
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import date, timedelta
from typing import Dict, List
import logging

from expense_app.models.models import Expense, Income, Budget

logger = logging.getLogger(__name__)


def get_monthly_summary(db: Session, year: int, month: int) -> Dict:
    """
    获取月度收支汇总

    Args:
        db: 数据库会话
        year: 年份
        month: 月份

    Returns:
        Dict: 包含总收入、总支出、结余和分类明细
    """
    # 计算总收入
    total_income = db.query(func.sum(Income.amount)).filter(
        extract('year', Income.date) == year,
        extract('month', Income.date) == month
    ).scalar() or 0.0
    logger.debug(f"Total income for {year}-{month}: {total_income}")

    # 计算总支出
    total_expense = db.query(func.sum(Expense.amount)).filter(
        extract('year', Expense.date) == year,
        extract('month', Expense.date) == month
    ).scalar() or 0.0
    logger.debug(f"Total expense for {year}-{month}: {total_expense}")

    # 按分类汇总支出
    category_data = db.query(
        Expense.category,
        func.sum(Expense.amount)
    ).filter(
        extract('year', Expense.date) == year,
        extract('month', Expense.date) == month
    ).group_by(Expense.category).all()

    category_breakdown = {cat: float(amt) for cat, amt in category_data}
    logger.debug(f"Category breakdown: {category_breakdown}")

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": total_income - total_expense,
        "category_breakdown": category_breakdown
    }


def get_budget_progress(db: Session, year: int, month: int) -> List[Dict]:
    """
    获取预算执行进度

    Args:
        db: 数据库会话
        year: 年份
        month: 月份

    Returns:
        List[Dict]: 预算执行进度列表
    """
    period = f"{year}-{month:02d}"
    budgets = db.query(Budget).filter(
        Budget.period == period,
        Budget.type == "monthly"
    ).all()

    result = []
    for budget in budgets:
        # 计算该分类的实际支出
        if budget.category:
            spent = db.query(func.sum(Expense.amount)).filter(
                Expense.category == budget.category,
                extract('year', Expense.date) == year,
                extract('month', Expense.date) == month
            ).scalar() or 0.0
        else:
            # 总预算
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

    logger.info(f"Budget progress for {period}: {len(result)} budgets")
    return result


def get_trend_data(db: Session, months: int = 6) -> List[Dict]:
    """
    获取月度收支趋势数据

    Args:
        db: 数据库会话
        months: 获取最近几个月的数据（默认 6 个月）

    Returns:
        List[Dict]: 趋势数据列表
    """
    today = date.today()
    results = []

    for i in range(months - 1, -1, -1):
        # 计算目标月份
        target_date = today.replace(day=1) - timedelta(days=30 * i)
        year = target_date.year
        month = target_date.month

        # 处理年份借位
        if month <= 0:
            month += 12
            year -= 1

        # 查询收入
        income = db.query(func.sum(Income.amount)).filter(
            extract('year', Income.date) == year,
            extract('month', Income.date) == month
        ).scalar() or 0.0

        # 查询支出
        expense = db.query(func.sum(Expense.amount)).filter(
            extract('year', Expense.date) == year,
            extract('month', Expense.date) == month
        ).scalar() or 0.0

        results.append({
            "period": f"{year}-{month:02d}",
            "income": income,
            "expense": expense
        })

    logger.info(f"Trend data: {months} months")
    return results
