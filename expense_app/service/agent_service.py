"""
Agent 查询服务层

提供自然语言查询开销数据的功能
支持常见问题如：
- "这个月花了多少钱"
- "餐饮花了多少"
- "预算还剩多少"
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import date
from typing import Dict, List
import logging

from expense_app.models.models import Expense, Income, Budget

logger = logging.getLogger(__name__)

# 默认开销分类列表
DEFAULT_CATEGORIES = ["餐饮", "交通", "购物", "娱乐", "居住", "医疗", "其他"]


def query_expense_data(db: Session, query: str) -> Dict:
    """
    解析自然语言查询并返回数据

    Args:
        db: 数据库会话
        query: 用户查询文本

    Returns:
        Dict: 包含回答和数据的字典
    """
    today = date.today()
    current_year = today.year
    current_month = today.month

    result = {"answer": "", "data": {}}

    logger.info(f"Processing query: {query}")

    # 本月总支出
    if "这个月" in query or "本月" in query:
        total = db.query(func.sum(Expense.amount)).filter(
            extract('year', Expense.date) == current_year,
            extract('month', Expense.date) == current_month
        ).scalar() or 0.0
        result["answer"] = f"本月总支出为：¥{total:.2f}"
        result["data"] = {"total": total, "period": f"{current_year}-{current_month:02d}"}
        logger.info(f"Query result: {result['answer']}")

    # 上月总支出
    elif "上个月" in query or "上月" in query:
        last_month = current_month - 1 if current_month > 1 else 12
        last_year = current_year if current_month > 1 else current_year - 1
        total = db.query(func.sum(Expense.amount)).filter(
            extract('year', Expense.date) == last_year,
            extract('month', Expense.date) == last_month
        ).scalar() or 0.0
        result["answer"] = f"上月总支出为：¥{total:.2f}"
        result["data"] = {"total": total, "period": f"{last_year}-{last_month:02d}"}
        logger.info(f"Query result: {result['answer']}")

    # 特定分类支出
    elif any(cat in query for cat in DEFAULT_CATEGORIES):
        for cat in DEFAULT_CATEGORIES:
            if cat in query:
                # 检查时间范围
                if "这个月" in query or "本月" in query:
                    total = db.query(func.sum(Expense.amount)).filter(
                        Expense.category == cat,
                        extract('year', Expense.date) == current_year,
                        extract('month', Expense.date) == current_month
                    ).scalar() or 0.0
                    result["answer"] = f"本月{cat}支出为：¥{total:.2f}"
                elif "上个月" in query or "上月" in query:
                    last_month = current_month - 1 if current_month > 1 else 12
                    last_year = current_year if current_month > 1 else current_year - 1
                    total = db.query(func.sum(Expense.amount)).filter(
                        Expense.category == cat,
                        extract('year', Expense.date) == last_year,
                        extract('month', Expense.date) == last_month
                    ).scalar() or 0.0
                    result["answer"] = f"上月{cat}支出为：¥{total:.2f}"
                else:
                    total = db.query(func.sum(Expense.amount)).filter(
                        Expense.category == cat
                    ).scalar() or 0.0
                    result["answer"] = f"{cat}总支出为：¥{total:.2f}"
                result["data"] = {"category": cat, "total": total}
                logger.info(f"Query result for {cat}: {result['answer']}")
                break

    # 预算剩余
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
            budget_info.append({
                "category": b.category or "总计",
                "budget": b.amount,
                "remaining": remaining
            })
        result["answer"] = "预算执行情况：" + ", ".join(
            f"{b['category']}: 剩余¥{b['remaining']:.2f}" for b in budget_info
        )
        result["data"] = {"budgets": budget_info}
        logger.info(f"Query result: {result['answer']}")

    # 收入查询
    elif "收入" in query:
        total = db.query(func.sum(Income.amount)).filter(
            extract('year', Income.date) == current_year,
            extract('month', Income.date) == current_month
        ).scalar() or 0.0
        result["answer"] = f"本月总收入为：¥{total:.2f}"
        result["data"] = {"total_income": total}
        logger.info(f"Query result: {result['answer']}")

    # 默认：返回本月概况
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
        result["data"] = {
            "income": total_income,
            "expense": total_expense,
            "balance": total_income - total_expense
        }
        logger.info(f"Query result: {result['answer']}")

    return result
