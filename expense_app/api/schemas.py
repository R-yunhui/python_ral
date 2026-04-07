"""
Pydantic 数据模型定义

用于 API 请求/响应的数据验证和序列化
包含 Expense、Income、Budget 及其相关的 Create/Update/Response 模型
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)


# ==================== Expense 相关模型 ====================

class ExpenseBase(BaseModel):
    """
    开销基础模型

    包含开销记录的核心字段，被其他 Expense 模型继承
    """
    model_config = ConfigDict(populate_by_name=True)

    amount: float = Field(..., gt=0, description="开销金额")
    category: str = Field(..., min_length=1, max_length=50, description="开销分类")
    record_date: date = Field(..., description="开销日期", alias="date")
    description: Optional[str] = Field(None, description="开销描述")
    tags: Optional[List[str]] = Field(None, description="标签列表")


class ExpenseCreate(ExpenseBase):
    """
    创建开销请求模型

    用于接收创建开销的 API 请求
    """
    pass


class ExpenseUpdate(BaseModel):
    """
    更新开销请求模型

    所有字段可选，用于部分更新开销记录
    """
    amount: Optional[float] = Field(None, gt=0, description="开销金额")
    category: Optional[str] = Field(None, min_length=1, max_length=50, description="开销分类")
    record_date: Optional[date] = Field(None, description="开销日期")
    description: Optional[str] = Field(None, description="开销描述")
    tags: Optional[List[str]] = Field(None, description="标签列表")


class Expense(ExpenseBase):
    """
    开销响应模型

    包含完整的开销记录信息，用于 API 响应
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="主键 ID")
    created_at: datetime = Field(..., description="创建时间")


# ==================== Income 相关模型 ====================

class IncomeBase(BaseModel):
    """
    收入基础模型

    包含收入记录的核心字段
    """
    model_config = ConfigDict(populate_by_name=True)

    amount: float = Field(..., gt=0, description="收入金额")
    source: str = Field(..., min_length=1, max_length=100, description="收入来源")
    record_date: date = Field(..., description="收入日期", alias="date")
    note: Optional[str] = Field(None, description="备注信息")


class IncomeCreate(IncomeBase):
    """
    创建收入请求模型

    用于接收创建收入的 API 请求
    """
    pass


class IncomeUpdate(BaseModel):
    """
    更新收入请求模型

    所有字段可选，用于部分更新收入记录
    """
    amount: Optional[float] = Field(None, gt=0, description="收入金额")
    source: Optional[str] = Field(None, min_length=1, max_length=100, description="收入来源")
    record_date: Optional[date] = Field(None, description="收入日期")
    note: Optional[str] = Field(None, description="备注信息")


class Income(IncomeBase):
    """
    收入响应模型

    包含完整的收入记录信息，用于 API 响应
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="主键 ID")
    created_at: datetime = Field(..., description="创建时间")


# ==================== Budget 相关模型 ====================

class BudgetBase(BaseModel):
    """
    预算基础模型

    包含预算设置的核心字段
    """
    budget_type: str = Field(..., pattern="^(monthly|yearly)$", description="预算类型")
    category: Optional[str] = Field(None, min_length=1, max_length=50, description="预算分类")
    amount: float = Field(..., gt=0, description="预算金额")
    period: str = Field(..., pattern="^\\d{4}(-\\d{2})?$", description="预算周期")


class BudgetCreate(BudgetBase):
    """
    创建预算请求模型

    用于接收创建预算的 API 请求
    """
    pass


class BudgetUpdate(BaseModel):
    """
    更新预算请求模型

    所有字段可选，用于部分更新预算设置
    """
    budget_type: Optional[str] = Field(None, pattern="^(monthly|yearly)$", description="预算类型")
    category: Optional[str] = Field(None, min_length=1, max_length=50, description="预算分类")
    amount: Optional[float] = Field(None, gt=0, description="预算金额")
    period: Optional[str] = Field(None, pattern="^\\d{4}(-\\d{2})?$", description="预算周期")


class Budget(BudgetBase):
    """
    预算响应模型

    包含完整的预算记录信息，用于 API 响应
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="主键 ID")
    created_at: datetime = Field(..., description="创建时间")


# ==================== Statistics 相关模型 ====================

class StatsSummary(BaseModel):
    """
    统计摘要模型

    用于返回收支汇总数据
    """
    total_income: float = Field(..., description="总收入")
    total_expense: float = Field(..., description="总支出")
    balance: float = Field(..., description="结余")
    category_breakdown: dict = Field(..., description="分类支出明细")


class BudgetProgress(BaseModel):
    """
    预算执行进度模型

    用于返回预算执行情况
    """
    budget_id: int = Field(..., description="预算 ID")
    category: str = Field(..., description="分类名称")
    budget_amount: float = Field(..., description="预算金额")
    spent_amount: float = Field(..., description="已花费金额")
    remaining: float = Field(..., description="剩余金额")
    percentage: float = Field(..., description="使用百分比")
