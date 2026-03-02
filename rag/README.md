# RAG 知识库问答系统

基于 FastAPI + Vue.js + SQLite + Qdrant 的 RAG 知识库问答系统。

## 功能特性

- 📚 **知识库管理** - 创建、删除、查看知识库
- 📄 **文档管理** - 上传、删除、查看文档（支持 txt/md/pdf/docx）
- 💬 **问答对话** - 普通问答和知识库问答两种模式
- 🎨 **精美界面** - 现代专业风格设计，支持明暗双主题
- ⚡ **流式响应** - 支持 SSE 流式输出
- 💾 **统一存储** - 所有数据集中存储在 `rag_data` 目录

## 快速开始

### 1. 配置环境变量

复制 `.env.example` 为 `.env` 并填写你的 API 密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
DASHSCOPE_API_KEY=your_api_key_here
QWEN_CHAT_MODEL=qwen-plus
```

### 2. 启动服务

```bash
# 使用 uv 启动
uv run python start_rag.py

# 或直接使用 Python
python start_rag.py
```

### 3. 访问应用

- 🏠 **前端页面**: http://localhost:8000
- 📖 **API 文档**: http://localhost:8000/docs

## 数据存储结构

所有数据统一存储在 `rag_data/` 目录下，结构清晰，便于管理和备份：

```
rag_data/
├── database/
│   └── rag.db              # SQLite 数据库（元数据）
├── documents/
│   ├── kb_1/               # 知识库 1 的文档
│   │   ├── file1.txt
│   │   └── file2.pdf
│   ├── kb_2/               # 知识库 2 的文档
│   │   └── ...
│   └── ...
└── qdrant/
    ├── meta.json           # Qdrant 元数据
    └── collection/         # 向量集合
        ├── kb_1/
        ├── kb_2/
        └── ...
```

### 存储说明

| 目录 | 用途 | 文件示例 |
|------|------|----------|
| `database/` | SQLite 数据库 | `rag.db` - 存储知识库、文档元数据 |
| `documents/kb_{id}/` | 上传的文档文件 | `kb_1/document.pdf` |
| `qdrant/` | Qdrant 向量数据库 | `meta.json`, `collection/` |

### 数据说明

1. **SQLite 数据库** (`rag_data/database/rag.db`)
   - 知识库表：存储知识库名称、描述、集合名称等
   - 文档表：存储文档文件名、路径、状态、错误信息等

2. **文档文件** (`rag_data/documents/kb_{id}/`)
   - 按知识库 ID 分组存储
   - 支持 txt、md、pdf、docx 格式
   - 原始文件保存

3. **向量数据库** (`rag_data/qdrant/`)
   - Qdrant 本地存储
   - 每个知识库对应一个集合（`kb_{id}`）
   - 存储文档的向量嵌入

## 项目结构

```
rag/
├── api/                    # API 层
│   ├── main.py            # FastAPI 应用入口
│   ├── schemas.py         # Pydantic 模型
│   └── routers/           # API 路由
│       ├── knowledge_base.py  # 知识库管理
│       ├── document.py        # 文档管理
│       └── chat.py            # 问答接口
├── models/                # 数据库模型
│   ├── database.py        # SQLite 配置
│   └── models.py          # ORM 模型
├── service/               # 业务逻辑层
│   ├── kb_service.py      # 知识库服务
│   ├── document_service.py # 文档服务
│   └── chat_service.py    # 问答服务
├── static/                # 前端静态文件
│   ├── index.html         # 单页应用
│   ├── css/style.css      # 样式文件
│   └── js/app.js          # Vue 应用
├── config.py              # 统一配置模块
└── data/                  # (旧版，已迁移到 rag_data/)
```

## API 接口

### 知识库管理
- `POST /api/kb` - 创建知识库
- `GET /api/kb` - 获取知识库列表
- `GET /api/kb/{id}` - 获取知识库详情
- `DELETE /api/kb/{id}` - 删除知识库

### 文档管理
- `POST /api/kb/{kb_id}/documents` - 上传文档
- `GET /api/kb/{kb_id}/documents` - 获取文档列表
- `DELETE /api/documents/{doc_id}` - 删除文档

### 问答接口
- `POST /api/chat` - 普通问答
- `POST /api/chat/rag` - 知识库问答
- `POST /api/chat/stream` - 流式问答

## 技术栈

### 后端
- **FastAPI** - Web 框架
- **SQLModel** - ORM (SQLite)
- **Qdrant** - 向量数据库
- **LlamaIndex** - RAG 框架
- **LangChain** - LLM 应用框架
- **DashScope** - 通义千问 API

### 前端
- **Vue 3** - 渐进式框架 (CDN 方式)
- **Element Plus** - UI 组件库
- **CSS3** - 自定义样式（支持明暗双主题）

## 配置说明

### 环境变量 (`.env`)

```env
# 阿里云 DashScope API 密钥
DASHSCOPE_API_KEY=your_api_key_here

# 通义千问模型
QWEN_CHAT_MODEL=qwen-plus
```

### 配置项 (`rag/config.py`)

```python
# 文本分块配置
CHUNK_SIZE = 512      # 分块大小
CHUNK_OVERLAP = 50    # 分块重叠

# Embedding 配置
EMBEDDING_MODEL = "text-embedding-v3"
EMBEDDING_DIMENSION = 1024

# 向量检索配置
DEFAULT_TOP_K = 3     # 默认检索文档数
MAX_TOP_K = 10        # 最大检索文档数
```

## 注意事项

1. **首次启动**需要配置 DashScope API 密钥
2. **文档上传**后会自动在后台处理，可能需要一些时间
3. **数据备份**：只需备份 `rag_data/` 目录即可
4. **主题切换**：点击左下角的月亮/太阳图标切换明暗主题
5. **知识库详情**：点击知识库卡片可进入查看详情和文档

## 开发说明

- 使用 `uv` 进行依赖管理
- 使用 `uv run` 运行 Python 脚本
- 前端使用 CDN 方式引入 Vue 3 和 Element Plus，无需构建
- 所有存储路径在 `rag/config.py` 中统一配置

## 数据迁移

如果需要迁移数据，只需复制整个 `rag_data/` 目录到新位置，然后更新 `rag/config.py` 中的 `STORAGE_ROOT` 路径即可。
