"""
Agent 查询路由模块

提供自然语言查询接口：
- POST /api/agent/query - 自然语言查询开销数据
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging

from expense_app.models.database import get_db
from expense_app.service.agent_service import query_expense_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])


class QueryRequest(BaseModel):
    """Agent 查询请求模型"""
    query: str = Field(..., description="自然语言查询文本")


class QueryResponse(BaseModel):
    """Agent 查询响应模型"""
    answer: str = Field(..., description="自然语言回答")
    data: dict = Field(..., description="结构化数据")


@router.post("/query", response_model=QueryResponse)
def agent_query(request: QueryRequest, db: Session = Depends(get_db)):
    """
    自然语言查询开销数据

    支持以下查询类型：
    - 本月/上月总支出
    - 特定分类支出（如"餐饮花了多少"）
    - 预算剩余查询
    - 收入查询
    - 本月概况

    Args:
        request: 查询请求
        db: 数据库会话

    Returns:
        QueryResponse: 包含自然语言回答和结构化数据

    Examples:
        - "这个月花了多少钱" -> 返回本月总支出
        - "餐饮花了多少" -> 返回本月餐饮支出
        - "预算还剩多少" -> 返回预算执行进度
        - "收入多少" -> 返回本月总收入
    """
    try:
        result = query_expense_data(db, request.query)
        return result
    except Exception as e:
        logger.error(f"Agent query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
