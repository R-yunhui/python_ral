# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

这是一个 **Python + LLM 应用** 个人学习项目，包含三个主要子系统：

| 子系统 | 路径 | 说明 |
|--------|------|------|
| **RAG 知识库问答系统** | `rag/` | FastAPI + Vue + SQLite + Qdrant 的知识库问答 |
| **AI 对话助手** | `assistant/` | FastAPI + LangGraph + 记忆系统 + 工具调用的对话服务 |
| **练习代码** | `practice/` | LangChain、LangGraph、FastAPI、AutoGen 等 demo |

此外，`interview/` 目录存放各技术栈的面试复习资料，`docs/` 存放设计文档。

## 开发环境

- **依赖管理：** `uv`（所有依赖在 `pyproject.toml`）
- **Python 版本：** 3.12+
- **LLM API：** 阿里云 DashScope（通义千问），配置在 `.env`

## 常用命令

### RAG 系统

```bash
# 启动 RAG 知识库问答服务（后端 FastAPI + 前端 Vue SPA）
uv run python start_rag.py

# 启动后访问
# 前端: http://localhost:8000
# API 文档: http://localhost:8000/docs
```

### AI 对话助手

```bash
# 启动助手后端服务（需 .env 配置完整）
uv run python -m assistant.backend.app

# 测试
uv run pytest tests/
uv run pytest tests/backend/ -v  # 详细输出
```

### 运行单个练习脚本

```bash
uv run python practice/langchain/15_chain_demo.py
uv run python practice/scenario/01_rag.py
```

### 依赖管理

```bash
# 添加新依赖
uv add <package>

# 安装依赖
uv sync

# 运行任意 Python 脚本
uv run python <script.py>
```

## 架构说明

### RAG 知识库问答系统 (`rag/`)

```
rag/
├── api/main.py            # FastAPI 入口，挂载 CORS、静态文件、路由
├── api/routers/           # 知识库管理(kb)、文档管理(document)、问答(chat)
├── models/                # SQLModel ORM + SQLite
├── service/               # 业务逻辑层
├── config.py              # 统一配置（存储路径、分块参数、Qdrant 路径）
├── static/                # Vue 3 前端（CDN 引入，无需构建）
└── rag_data/              # 运行时数据（SQLite、文档、Qdrant 向量库）
```

**启动流程：** `start_rag.py` → `uvicorn` → `rag/api/main.py` → 初始化数据库 → 挂载路由

### AI 对话助手 (`assistant/backend/`)

```
assistant/backend/
├── app.py                 # FastAPI 工厂函数 create_app()
├── config/settings.py     # 配置管理（settings 实例，启动时 validate）
├── graph/chat_graph.py    # LangGraph 图定义，对话主流程编排
├── model/                 # Pydantic schemas + SQLModel 模型
├── service/               # 服务层
│   ├── llm_client.py           # LLM 客户端封装
│   ├── llm_orchestrator_service.py  # LLM 编排
│   ├── short_memory_service.py    # 短期记忆（对话历史）
│   ├── long_memory_service.py     # 长期记忆
│   ├── structured_store_service.py # 结构化存储
│   ├── tool_registry_service.py   # 工具注册中心
│   ├── query_service.py           # 查询服务
│   ├── reply_service.py           # 回复服务
│   └── background_jobs.py         # 后台任务
├── middleware/auth.py     # API Key 认证中间件
└── api/chat.py            # /v1/chat 路由
```

**启动流程：** `create_app()` → 建表 + 种子数据 → `ChatGraph` 初始化 → `start_background_worker()` → 启动路由

### 练习代码 (`practice/`)

| 子目录 | 内容 |
|--------|------|
| `langchain/` | LangChain LCEL Chain 和 Structured Output demo |
| `langgraph/` | LangGraph 状态机 Agent demo |
| `fastapi/` | FastAPI 基础练习 |
| `autogen/` | AutoGen 多 Agent 练习 |
| `scenario/` | RAG 性能优化场景（意图识别、缓存、并行检索） |

## 环境变量

关键变量（详见 `.env.example`）：

- `DASHSCOPE_API_KEY` — 阿里云 DashScope API 密钥
- `DASHSCOPE_BASE_URL` — DashScope 兼容模式端点
- `QWEN_CHAT_MODEL` — 主对话模型
- `QWEN_FLASH_MODEL` — 轻量快速模型（改写、意图识别）
- `EMBEDDING_MODEL` — 嵌入模型

## 注意事项

- RAG 系统的数据存储在 `rag/rag_data/`，备份只需复制该目录
- AI 助手使用 SQLite（PRAGMA WAL + busy_timeout），测试时路径可配置
- `interview/` 下的面试文档格式统一，各子目录含 README + 详细面试文档
