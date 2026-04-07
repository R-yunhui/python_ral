# Personal Assistant - Expense Module Design

## Overview

一个基于 Web 的个人助手应用，从开销管理模块开始，逐步扩展到工作记录、计划管理、个人状况等功能。

## Technical Stack

- **Frontend**: React + TypeScript + Vite
- **UI Components**: shadcn/ui
- **Charts**: Recharts
- **Backend**: FastAPI
- **Database**: SQLite + SQLAlchemy
- **AI Agent**: LangChain + Claude API
- **RAG**: Chroma vector database

## Expense Module Architecture

### Data Models

```
Expense:
  - id: int
  - amount: decimal
  - category: string (餐饮/交通/购物/娱乐/居住/医疗/其他)
  - date: date
  - description: string
  - tags: list[string]
  - created_at: datetime

Income:
  - id: int
  - amount: decimal
  - source: string
  - date: date
  - note: string
  - created_at: datetime

Budget:
  - id: int
  - type: string (monthly/yearly)
  - category: string (null for total)
  - amount: decimal
  - period: string (YYYY-MM or YYYY)
  - created_at: datetime
```

### API Endpoints

```
# Expenses
POST   /api/expenses          - 添加开销
GET    /api/expenses          - 列表 (支持筛选)
PUT    /api/expenses/{id}     - 更新开销
DELETE /api/expenses/{id}     - 删除开销

# Income
POST   /api/incomes           - 添加收入
GET    /api/incomes           - 列表
PUT    /api/incomes/{id}      - 更新收入
DELETE /api/incomes/{id}      - 删除收入

# Budgets
POST   /api/budgets           - 设置预算
GET    /api/budgets           - 获取预算
PUT    /api/budgets/{id}      - 更新预算
DELETE /api/budgets/{id}      - 删除预算

# Statistics
GET    /api/stats/summary     - 月度概览
GET    /api/stats/category    - 分类占比
GET    /api/stats/trend       - 趋势分析
GET    /api/stats/budget      - 预算进度

# Agent
POST   /api/agent/query       - Agent 问答
```

### Frontend Pages

1. **Dashboard (/)** - 概览页
   - 本月收入/支出/结余卡片
   - 预算进度条
   - 快速记账按钮
   - 最近开销列表

2. **Expenses (/expenses)** - 开销管理
   - 开销列表
   - 筛选 (日期/分类)
   - 添加/编辑对话框

3. **Income (/income)** - 收入管理
   - 收入列表
   - 添加/编辑对话框

4. **Budgets (/budgets)** - 预算管理
   - 月度/年度预算设置
   - 预算执行进度

5. **Statistics (/stats)** - 统计分析
   - 分类饼图
   - 月度趋势折线图
   - 时间范围筛选

## Implementation Phases

### Phase 1: Foundation
- FastAPI 项目结构
- SQLite 数据库模型
- 基础 CRUD API

### Phase 2: Basic Frontend
- React 项目搭建
- Dashboard 页面
- 开销记录表单

### Phase 3: Statistics
- 图表组件
- 统计 API
- 数据可视化

### Phase 4: Agent Integration
- LangChain Agent
- RAG 向量存储
- 自然语言查询

## File Structure

```
python_ral/
├── expense_app/
│   ├── api/
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── expenses.py
│   │   │   ├── incomes.py
│   │   │   ├── budgets.py
│   │   │   ├── stats.py
│   │   │   └── agent.py
│   │   └── schemas.py
│   ├── models/
│   │   ├── database.py
│   │   └── models.py
│   ├── service/
│   │   ├── expense_service.py
│   │   └── agent_service.py
│   ├── utils/
│   │   └── logger.py
│   └── static/
├── expense_web/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── api/
│   └── package.json
└── start_app.py
```
