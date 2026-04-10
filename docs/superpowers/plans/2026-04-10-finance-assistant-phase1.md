# 个人财务助手 Phase 1 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 构建一个以大模型为核心的个人财务对话助手，支持自然语言理解、问题处理、数据查询与异步记账闭环。

**架构：** 采用“LLM 主导 + 工具执行”模式。LLM 先完成意图理解、参数抽取和回复规划，再调用结构化存储工具（SQLite）与长期记忆工具（mem0ai）；查询路径同步返回，存储路径异步执行，保证对话响应流畅。

**技术栈：** Python 3.12、FastAPI、LangGraph、LangChain、SQLModel/SQLite、mem0ai、Pydantic v2、pytest
**依赖管理：** uv

---

## 零、基础设施与配置（前置任务）

**文件：**
- 创建：`assistant/backend/__init__.py` 及各子包 `__init__.py`
- 创建：`assistant/backend/config/settings.py`
- 创建：`assistant/backend/config/__init__.py`
- 创建：`assistant/backend/utils/__init__.py`
- 创建：`assistant/backend/api/__init__.py`
- 创建：`assistant/backend/model/__init__.py`
- 创建：`assistant/backend/service/__init__.py`
- 创建：`assistant/backend/graph/__init__.py`
- 创建：`tests/__init__.py`
- 创建：`tests/backend/__init__.py`
- 创建：`tests/conftest.py`
- 创建：`tests/backend/test_config.py`
- 更新：`pyproject.toml`（添加 assistant 子包配置）
- 更新：`.env.example`（补充财务助手专属变量）

- [ ] **步骤 1：配置基础设施**

```python
# assistant/backend/config/settings.py
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # LLM - 意图识别（小模型）
    intent_model: str = "qwen-turbo"
    intent_api_key: str = ""
    intent_base_url: str = ""

    # LLM - 主对话（大模型）
    reply_model: str = "claude-sonnet-4-6-20250514"
    reply_api_key: str = ""
    reply_base_url: str = ""

    # 数据库
    sqlite_path: str = "data/finance.db"

    # mem0
    mem0_api_key: str = ""

    # 通用
    log_level: str = "INFO"
    timezone: str = "Asia/Shanghai"
    api_key: str = ""  # API 认证密钥

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def validate(self):
        """启动时校验必填项"""
        if not self.sqlite_path:
            raise ValueError("SQLITE_PATH is required")
        if not self.reply_api_key:
            raise ValueError("REPLY_API_KEY is required")

settings = Settings()
settings.validate()
```

- [ ] **步骤 2：配置测试验证**

```python
# tests/backend/test_config.py
import pytest
from assistant.backend.config.settings import Settings

def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("REPLY_API_KEY", "test-key")
    monkeypatch.setenv("SQLITE_PATH", ":memory:")
    s = Settings()
    assert s.reply_api_key == "test-key"

def test_settings_fails_without_required_keys(monkeypatch):
    monkeypatch.delenv("REPLY_API_KEY", raising=False)
    with pytest.raises(ValueError):
        Settings().validate()
```

- [ ] **步骤 3：测试基础设施（conftest.py）**

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine
from assistant.backend.config.settings import Settings
from assistant.backend.app import create_app

@pytest.fixture
def test_db_url():
    return "sqlite:///file:testdb?mode=memory&cache=shared"

@pytest.fixture
def app(test_db_url):
    """返回测试用 FastAPI 应用"""
    settings = Settings(
        reply_api_key="test-key",
        sqlite_path=test_db_url,
        api_key="test-api-key"
    )
    return create_app(settings, test_mode=True)

@pytest.fixture
def client(app):
    return TestClient(app)
```

- [ ] **步骤 4：更新 .env.example**

```
# 意图识别（小模型）
INTENT_MODEL=qwen-turbo
INTENT_API_KEY=
INTENT_BASE_URL=

# 主对话（大模型）
REPLY_MODEL=claude-sonnet-4-6-20250514
REPLY_API_KEY=
REPLY_BASE_URL=

# 数据库
SQLITE_PATH=data/finance.db

# mem0
MEM0_API_KEY=

# 通用
LOG_LEVEL=INFO
TIMEZONE=Asia/Shanghai
API_KEY=your-secret-api-key
```

- [ ] **步骤 5：更新 pyproject.toml**

```toml
[project]
# 确保 assistant 包可被导入
packages = [{ include = "assistant" }]
```

- [ ] **步骤 6：提交**

```bash
git add assistant/backend/config/ assistant/backend/utils/__init__.py assistant/backend/api/__init__.py assistant/backend/model/__init__.py assistant/backend/service/__init__.py assistant/backend/graph/__init__.py assistant/backend/__init__.py tests/__init__.py tests/backend/__init__.py tests/conftest.py tests/backend/test_config.py pyproject.toml .env.example
git commit -m "feat: 初始化配置基础设施与测试环境"
```

---

## 一、范围与原则

- 范围内：中文自然语言对话、收支记录、预算设置与查询、趋势问答（基础版）、三层记忆打通。
- 范围外：语音/OCR、多账户、多币种、自动推送预警。
- 时区标准：Asia/Shanghai（UTC+08:00），所有“本周/本月”等时间语义统一按该时区解析。
- 体验目标：API P95 响应 < 1.8s（不含异步入库完成时间）。

## 二、核心设计（LLM 优先）

- 不走”传统表单提交”流程，所有输入默认是自然语言，由 LLM 统一理解。
- 一次 LLM 调用完成：
  - 用户问题理解
  - 存储意图抽取（可选）
  - 查询意图抽取（可选）
  - 回复草案规划
- LLM 不直接写库，只能通过受控工具执行：
  - `structured_store_tool`（写 SQLite）
  - `structured_query_tool`（查 SQLite）
  - `long_memory_tool`（写/查 mem0）
  - `resolve_category_tool`（分类标准化与置信度判定）
- 当用户输入”既在记账又在提问”时：
  - 主链路先回答问题
  - 存储操作放到后台异步执行
- LLM 客户端抽象层：
  - 统一的 `LLMClient` 接口，支持 `invoke(prompt, model=...)`
  - 配置映射：`intent_model`、`reply_model`、`summary_model`
  - 故障降级：主模型失败后尝试备用模型

## 分类与枚举补充（对齐需求文档第 14 章）

- 分类采用“数据库字典表”，非代码硬编码 Enum。
- 支持二级分类（L1/L2），且强制区分 `expense` 与 `income` 方向。
- 分类落库必须携带 `match_type`、`confidence`、`needs_review`。
- 未命中或低置信度时先落 `待分类/其他`，不阻塞记账。
- 用户纠正后同步更新 `category_aliases` 与 mem0 反馈记忆。

## 三、计划文件结构（拟新增）

- 创建：`assistant/backend/app.py` - FastAPI 启动入口。
- 创建：`assistant/backend/api/chat.py` - `/v1/chat` 接口。
- 创建：`assistant/backend/config/settings.py` - 大模型与存储配置。
- 创建：`assistant/backend/model/schemas.py` - 对话协议与工具输入输出协议。
- 创建：`assistant/backend/model/sql_models.py` - 财务结构化表模型。
- 创建：`assistant/backend/graph/chat_graph.py` - LangGraph 编排（LLM 节点 + 工具节点）。
- 创建：`assistant/backend/service/llm_orchestrator_service.py` - 大模型主编排服务。
- 创建：`assistant/backend/service/tool_registry_service.py` - 工具注册与权限边界。
- 创建：`assistant/backend/service/structured_store_service.py` - SQLite 写入能力。
- 创建：`assistant/backend/service/query_service.py` - SQL 聚合与查询能力。
- 创建：`assistant/backend/service/long_memory_service.py` - mem0ai 读写封装。
- 创建：`assistant/backend/service/background_jobs.py` - 异步存储队列与重试。
- 创建：`assistant/backend/service/short_memory_service.py` - 短期记忆压缩。
- 创建：`assistant/backend/service/reply_service.py` - 最终回复组装与兜底。
- 创建：`assistant/backend/utils/time_range.py` - 时间语义解析。
- 创建：`assistant/backend/utils/logging.py` - trace 与脱敏日志。
- 创建：`tests/backend/test_chat_api.py`
- 创建：`tests/backend/test_llm_orchestrator.py`
- 创建：`tests/backend/test_structured_store.py`
- 创建：`tests/backend/test_query_service.py`
- 创建：`tests/backend/test_short_memory.py`

## 四、需求映射

- “自然语言处理和问题解答为主” -> 任务 2、任务 5、任务 6
- “三层记忆” -> 任务 3、任务 4、任务 7
- “异步存储 + 同步回复” -> 任务 4、任务 6
- “预算与收支查询” -> 任务 5

### 任务 1：接口骨架与对话协议（中文优先）

**文件：**
- 创建：`assistant/backend/app.py`
- 创建：`assistant/backend/api/chat.py`
- 创建：`assistant/backend/api/health.py`
- 创建：`assistant/backend/model/schemas.py`
- 创建：`assistant/backend/middleware/auth.py`
- 创建：`tests/backend/test_chat_api.py`
- 创建：`tests/backend/test_health.py`

- [ ] **步骤 1：先写失败测试（接口契约 + 健康检查）**

```python
from fastapi.testclient import TestClient
from assistant.backend.app import create_app
from assistant.backend.config.settings import Settings

@pytest.fixture()
def client():
    settings = Settings(reply_api_key="test", sqlite_path=":memory:", api_key="test-key")
    app = create_app(settings, test_mode=True)
    return TestClient(app)

def test_chat_contract_cn(client):
    resp = client.post("/v1/chat", json={"user_id": "u1", "message": "我今天午饭30，顺便看下这周餐饮总额"},
                       headers={"Authorization": "Bearer test-key"})
    assert resp.status_code == 200
    body = resp.json()
    assert "answer" in body
    assert "trace_id" in body
    assert body.get("lang") == "zh-CN"

def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

def test_chat_rejects_without_auth():
    # 无 API Key 应返回 401
    settings = Settings(reply_api_key="test", sqlite_path=":memory:", api_key="test-key")
    app = create_app(settings, test_mode=True)
    resp = TestClient(app).post("/v1/chat", json={"user_id": "u1", "message": "test"})
    assert resp.status_code == 401
```

- [ ] **步骤 2：执行测试并确认失败**

运行：`pytest tests/backend/test_chat_api.py tests/backend/test_health.py -v`
预期：FAIL。

- [ ] **步骤 3：最小实现 app、chat 路由、健康检查、认证中间件**

```python
# assistant/backend/app.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import SQLModel, create_engine
from .api.chat import router as chat_router
from .api.health import router as health_router
from .config.settings import Settings

def create_app(settings: Settings, test_mode: bool = False) -> FastAPI:
    engine = create_engine(
        settings.sqlite_path if test_mode else f"sqlite:///{settings.sqlite_path}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    # 启用 WAL 模式
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA busy_timeout=5000"))
    SQLModel.metadata.create_all(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield  # 启动时初始化，关闭时清理后台任务

    app = FastAPI(lifespan=lifespan)
    app.include_router(chat_router, prefix="/v1")
    app.include_router(health_router, prefix="/health")
    return app
```

```python
# assistant/backend/middleware/auth.py
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def get_api_key_checker(api_key: str):
    async def check_auth(request: Request, credentials: HTTPAuthorizationCredentials = security()):
        if credentials.credentials != api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
    return check_auth
```

```python
# assistant/backend/api/chat.py
from uuid import uuid4
from fastapi import APIRouter, Depends
from assistant.backend.model.schemas import ChatRequest, ChatResponse

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    return ChatResponse(answer="已收到，我正在处理你的财务问题。", trace_id=str(uuid4()))
```

```python
# assistant/backend/api/health.py
from fastapi import APIRouter

router = APIRouter()

@router.get("")
def health():
    return {"status": "ok"}
```

- [ ] **步骤 4：回归测试**

运行：`pytest tests/backend/test_chat_api.py tests/backend/test_health.py -v`
预期：PASS。

- [ ] **步骤 5：提交**

```bash
git add assistant/backend/app.py assistant/backend/api/chat.py assistant/backend/api/health.py assistant/backend/model/schemas.py assistant/backend/middleware/auth.py tests/backend/test_chat_api.py tests/backend/test_health.py
git commit -m "feat: 初始化中文对话接口、健康检查与认证中间件"
```

### 任务 2：LLM 编排器（统一理解+规划）

**文件：**
- 创建：`assistant/backend/service/llm_orchestrator_service.py`
- 创建：`assistant/backend/service/llm_client.py`
- 创建：`tests/backend/test_llm_orchestrator.py`
- 修改：`assistant/backend/model/schemas.py`

- [ ] **步骤 1：先写失败测试（单次抽取双意图，mock LLM）**

```python
from unittest.mock import patch
from assistant.backend.service.llm_orchestrator_service import plan_from_message
from assistant.backend.model.schemas import LLMPlan


def test_plan_contains_store_and_query():
    with patch("assistant.backend.service.llm_orchestrator_service.call_llm") as mock_llm:
        mock_llm.return_value = {
            "store_intents": [{"type": "structured", "data": {"amount": 45, "category": "交通"}}],
            "query_intent": {"type": "structured", "params": {"category": "交通", "period": "month"}},
            "reply_strategy": "concise_cn",
        }
        plan = plan_from_message("今天打车45，另外帮我看本月交通超预算没有")
        assert plan.query_intent is not None
        assert len(plan.store_intents) >= 1
```

- [ ] **步骤 2：执行测试并确认失败**

运行：`pytest tests/backend/test_llm_orchestrator.py -v`
预期：FAIL。

- [ ] **步骤 3：实现 LLM 客户端抽象层**

```python
# assistant/backend/service/llm_client.py
from langchain_core.language_models import BaseChatModel

class LLMClient:
    """统一 LLM 调用接口，支持多模型路由"""
    def __init__(self, model: BaseChatModel):
        self._model = model

    async def invoke(self, prompt: str, max_tokens: int = 500) -> str:
        response = await self._model.ainvoke(prompt)
        return response.content

def get_intent_client(settings) -> LLMClient:
    """意图识别用小模型"""
    return LLMClient(create_chat_model(settings.intent_model, settings.intent_api_key, settings.intent_base_url))

def get_reply_client(settings) -> LLMClient:
    """主对话用大模型"""
    return LLMClient(create_chat_model(settings.reply_model, settings.reply_api_key, settings.reply_base_url))
```

- [ ] **步骤 4：实现计划结构体与编排器（LLM 驱动，非关键词）**

```python
# assistant/backend/model/schemas.py
from pydantic import BaseModel

class LLMPlan(BaseModel):
    store_intents: list[dict] = []
    query_intent: dict | None = None
    reply_strategy: str = "concise_cn"
```

```python
# assistant/backend/service/llm_orchestrator_service.py
from assistant.backend.model.schemas import LLMPlan
from assistant.backend.service.llm_client import get_intent_client
from langchain_core.prompts import ChatPromptTemplate

INTENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是一个财务助手意图识别器。将用户输入拆解为存储意图和查询意图，输出 JSON。"),
    ("user", "{message}"),
])

async def plan_from_message(message: str, client) -> LLMPlan:
    """调用 LLM 结构化输出双意图"""
    prompt = INTENT_PROMPT.format(message=message)
    result = await client.invoke(prompt, max_tokens=500)
    # 解析 JSON 并返回 LLMPlan
    ...
```

- [ ] **步骤 5：回归测试**

运行：`pytest tests/backend/test_llm_orchestrator.py -v`
预期：PASS。

- [ ] **步骤 6：提交**

```bash
git add assistant/backend/service/llm_orchestrator_service.py assistant/backend/service/llm_client.py assistant/backend/model/schemas.py tests/backend/test_llm_orchestrator.py
git commit -m "feat: 新增 LLM 编排器与多模型客户端"
```

### 任务 3：工具注册中心（限制 LLM 权限边界）

**文件：**
- 创建：`assistant/backend/service/tool_registry_service.py`
- 创建：`tests/backend/test_tool_registry.py`

- [ ] **步骤 1：定义 ToolDefinition 与白名单注册**

```python
# assistant/backend/service/tool_registry_service.py
from pydantic import BaseModel

class ToolDefinition(BaseModel):
    name: str
    description: str
    is_write: bool
    input_schema: dict

class ToolNotFoundError(Exception):
    pass

class ToolRegistry:
    _tools: dict[str, ToolDefinition] = {}

    @classmethod
    def register(cls, tool: ToolDefinition):
        cls._tools[tool.name] = tool

    @classmethod
    def validate_tool_call(cls, tool_name: str, params: dict):
        if tool_name not in cls._tools:
            raise ToolNotFoundError(f"Tool '{tool_name}' is not registered")
        # TODO: 加上 params schema 校验
        return True

# 注册只读工具
ToolRegistry.register(ToolDefinition(name="structured_query", description="查询 SQLite 财务数据", is_write=False, input_schema={}))
ToolRegistry.register(ToolDefinition(name="long_memory", description="查询/写入 mem0 长期记忆", is_write=True, input_schema={}))
ToolRegistry.register(ToolDefinition(name="resolve_category", description="分类标准化", is_write=False, input_schema={}))
```

- [ ] **步骤 2：写入工具注册**

```python
ToolRegistry.register(ToolDefinition(name="structured_store", description="写入 SQLite 收支/预算记录", is_write=True, input_schema={}))
```

- [ ] **步骤 3：测试非法工具调用被拒绝**

```python
# tests/backend/test_tool_registry.py
import pytest
from assistant.backend.service.tool_registry_service import ToolRegistry, ToolNotFoundError

def test_unregistered_tool_is_rejected():
    with pytest.raises(ToolNotFoundError):
        ToolRegistry.validate_tool_call("delete_database", {})

def test_registered_tool_passes_validation():
    assert ToolRegistry.validate_tool_call("structured_query", {}) is True
```

- [ ] **步骤 4：执行测试**

运行：`pytest tests/backend/test_tool_registry.py -v`
预期：PASS。

- [ ] **步骤 5：提交**

```bash
git add assistant/backend/service/tool_registry_service.py tests/backend/test_tool_registry.py
git commit -m "feat: 增加工具注册中心与调用权限控制"
```

### 任务 4：异步存储流水线（用户无感）

**文件：**
- 创建：`assistant/backend/service/background_jobs.py`
- 创建：`assistant/backend/service/long_memory_service.py`
- 创建：`tests/backend/test_background_jobs.py`
- 修改：`assistant/backend/api/chat.py`

- [ ] **步骤 1：实现 mem0 封装（带降级）**

```python
# assistant/backend/service/long_memory_service.py
import logging

logger = logging.getLogger(__name__)

class LongMemoryService:
    """mem0ai 读写封装，连接失败时降级不阻塞"""
    def __init__(self, api_key: str):
        self._available = True
        try:
            from mem0 import Memory
            self._client = Memory(api_key=api_key)
        except Exception as e:
            logger.warning(f"mem0 init failed, long memory disabled: {e}")
            self._client = None
            self._available = False

    async def add(self, user_id: str, data: dict) -> bool:
        if not self._available:
            return False
        try:
            self._client.add(data, user_id=user_id)
            return True
        except Exception as e:
            logger.warning(f"mem0 write failed for user {user_id}: {e}")
            return False

    async def search(self, user_id: str, query: str) -> list[dict]:
        if not self._available:
            return []
        try:
            return self._client.search(query, user_id=user_id)
        except Exception as e:
            logger.warning(f"mem0 search failed for user {user_id}: {e}")
            return []
```

- [ ] **步骤 2：实现异步队列与重试**

```python
# assistant/backend/service/background_jobs.py
import asyncio
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

@dataclass
class StoreJob:
    user_id: str
    data: Any
    trace_id: str
    retry_count: int = 0

MAX_RETRIES = 3
QUEUE: asyncio.Queue[StoreJob] = asyncio.Queue()

async def enqueue_store(job: StoreJob):
    await QUEUE.put(job)

async def store_worker(store_service, mem0_service, max_retries: int = MAX_RETRIES):
    """后台消费队列，支持重试与死信记录"""
    while True:
        try:
            job = await QUEUE.get()
            success = await _execute_store(job, store_service, mem0_service, max_retries)
            if not success:
                logger.error(f"Dead letter: store job failed for trace_id={job.trace_id}")
                # TODO: 写入 failed_operations 表
            QUEUE.task_done()
        except Exception as e:
            logger.exception(f"store_worker error: {e}")

async def _execute_store(job, store_service, mem0_service, max_retries):
    for attempt in range(max_retries + 1):
        try:
            # 写入 SQLite
            await store_service.execute(job.data)
            # 写入 mem0（失败不影响主流程）
            await mem0_service.add(job.user_id, job.data)
            return True
        except Exception as e:
            if attempt < max_retries:
                wait = 0.5 * (2 ** attempt)  # 指数退避
                await asyncio.sleep(wait)
            else:
                logger.error(f"Store failed after {max_retries} retries: {e}")
                return False
```

- [ ] **步骤 3：编写测试（主链路不等待异步存储）**

```python
# tests/backend/test_background_jobs.py
import asyncio
import pytest
from unittest.mock import AsyncMock
from assistant.backend.service.background_jobs import StoreJob, QUEUE

@pytest.mark.asyncio
async def test_enqueue_does_not_block():
    """入队后立即返回，不等待写入完成"""
    job = StoreJob(user_id="u1", data={"amount": 30}, trace_id="t1")
    await QUEUE.put(job)
    assert QUEUE.qsize() == 1
```

- [ ] **步骤 4：mem0 降级测试**

```python
def test_long_memory_without_mem0():
    """mem0 不可用时返回空列表，不抛异常"""
    from assistant.backend.service.long_memory_service import LongMemoryService
    svc = LongMemoryService(api_key="invalid")
    import asyncio
    result = asyncio.get_event_loop().run_until_complete(svc.search("u1", "test"))
    assert result == []
```

- [ ] **步骤 5：回归测试**

运行：`pytest tests/backend/test_background_jobs.py tests/backend/test_chat_api.py -v`
预期：PASS。

- [ ] **步骤 6：提交**

```bash
git add assistant/backend/service/background_jobs.py assistant/backend/service/long_memory_service.py tests/backend/test_background_jobs.py assistant/backend/api/chat.py
git commit -m "feat: 完成异步存储流水线与长期记忆写入（含降级）"
```

### 任务 5：结构化存储与查询工具

**文件：**
- 创建：`assistant/backend/model/sql_models.py`
- 创建：`assistant/backend/service/structured_store_service.py`
- 创建：`assistant/backend/service/query_service.py`
- 创建：`assistant/backend/utils/time_range.py`
- 创建：`assistant/backend/service/seed_data.py`
- 创建：`tests/backend/test_structured_store.py`
- 创建：`tests/backend/test_query_service.py`

- [ ] **步骤 1：先写失败测试（收支/预算/时间范围查询）**

```python
# tests/backend/test_structured_store.py
import pytest
from sqlmodel import Session, create_engine
from assistant.backend.model.sql_models import Expense, Category, init_db
from assistant.backend.service.structured_store_service import StructuredStoreService

@pytest.fixture
def store_service():
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    return StructuredStoreService(engine)

def test_record_expense(store_service):
    """记录一笔支出并验证落库"""
    expense = store_service.create_expense(
        user_id="u1", amount=30.0, category_l1_code="餐饮",
        description="午餐", date="2026-04-10"
    )
    assert expense.id is not None
    assert expense.amount == 30.0
```

运行：`pytest tests/backend/test_structured_store.py tests/backend/test_query_service.py -v`
预期：FAIL。

- [ ] **步骤 2：实现 SQLModel 表和数据库初始化**

```python
# assistant/backend/model/sql_models.py
from datetime import datetime
from decimal import Decimal
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import text

class Category(SQLModel, table=True):
    __tablename__ = "categories"
    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True)
    name: str
    direction: str  # expense | income
    level: int  # 1 | 2
    parent_id: int | None = Field(default=None, foreign_key="categories.id")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CategoryAlias(SQLModel, table=True):
    __tablename__ = "category_aliases"
    id: int | None = Field(default=None, primary_key=True)
    category_id: int = Field(foreign_key="categories.id")
    alias: str
    locale: str = "zh-CN"
    weight: float = Field(default=1.0)

class Expense(SQLModel, table=True):
    __tablename__ = "expenses"
    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    amount: Decimal = Field(sa_type=Decimal)
    category_l1_id: int | None = Field(foreign_key="categories.id")
    category_l2_id: int | None = Field(foreign_key="categories.id")
    description: str
    date: datetime
    payment_method: str | None = None
    category_confidence: float | None = None
    needs_review: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Income(SQLModel, table=True):
    __tablename__ = "incomes"
    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    amount: Decimal = Field(sa_type=Decimal)
    source: str
    category_l1_id: int | None = Field(foreign_key="categories.id")
    category_l2_id: int | None = Field(foreign_key="categories.id")
    description: str
    date: datetime
    category_confidence: float | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Budget(SQLModel, table=True):
    __tablename__ = "budgets"
    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    category_id: int = Field(foreign_key="categories.id")
    amount: Decimal = Field(sa_type=Decimal)
    period_type: str  # daily | weekly | monthly | yearly
    period_start: datetime
    period_end: datetime
    alert_threshold_pct: float = Field(default=80.0)
    is_active: bool = Field(default=True)

class MonthlySummary(SQLModel, table=True):
    __tablename__ = "monthly_summaries"
    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    year: int
    month: int
    total_expense: Decimal = Field(sa_type=Decimal, default=0)
    total_income: Decimal = Field(sa_type=Decimal, default=0)
    top_category: str | None = None

def init_db(engine):
    """初始化数据库：建表 + 启用 WAL + 种子数据"""
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA busy_timeout=5000"))
    SQLModel.metadata.create_all(engine)
    seed_categories(engine)

def seed_categories(engine):
    """写入初始分类字典（需求文档 10.2 节）"""
    from sqlmodel import Session
    categories = [
        # 支出 L1
        Category(code="餐饮", name="餐饮", direction="expense", level=1),
        Category(code="交通", name="交通", direction="expense", level=1),
        Category(code="居住", name="居住", direction="expense", level=1),
        Category(code="购物", name="购物", direction="expense", level=1),
        Category(code="娱乐", name="娱乐", direction="expense", level=1),
        Category(code="医疗", name="医疗", direction="expense", level=1),
        Category(code="教育", name="教育", direction="expense", level=1),
        Category(code="通讯", name="通讯", direction="expense", level=1),
        Category(code="其他支出", name="其他", direction="expense", level=1),
        # 收入 L1
        Category(code="工资", name="工资", direction="income", level=1),
        Category(code="奖金", name="奖金", direction="income", level=1),
        Category(code="报销", name="报销", direction="income", level=1),
        Category(code="理财", name="理财", direction="income", level=1),
        Category(code="转账", name="转账", direction="income", level=1),
        Category(code="退款", name="退款", direction="income", level=1),
        Category(code="其他收入", name="其他", direction="income", level=1),
    ]
    with Session(engine) as session:
        session.add_all(categories)
        session.commit()
```

- [ ] **步骤 3：实现结构化存储与查询服务**

```python
# assistant/backend/service/structured_store_service.py
from sqlmodel import Session, select
from decimal import Decimal
from .tool_registry_service import ToolRegistry
from assistant.backend.model.sql_models import Expense, Income

ToolRegistry.register(...)  # 注册 structured_store 工具

class StructuredStoreService:
    def __init__(self, engine):
        self._engine = engine

    async def create_expense(self, user_id, amount, category_l1_code, description, date, **kwargs):
        with Session(self._engine) as session:
            expense = Expense(user_id=user_id, amount=Decimal(str(amount)), description=description, ...)
            session.add(expense)
            session.commit()
            return expense

# assistant/backend/service/query_service.py
from sqlmodel import Session, func, select
from datetime import datetime

class QueryService:
    def __init__(self, engine):
        self._engine = engine

    def sum_by_category(self, user_id, category_code, start, end):
        with Session(self._engine) as session:
            stmt = select(func.sum(Expense.amount)).where(
                Expense.user_id == user_id,
                Expense.date >= start,
                Expense.date <= end,
            )
            return session.exec(stmt).one() or 0
```

- [ ] **步骤 4：实现分类标准化工具**

```python
# 在 query_service.py 或独立 service 中
class CategoryResolver:
    """分类标准化：按 别名精确匹配 -> 语义相似度 -> 关键词兜底 顺序"""
    THRESHOLD_AUTO = 0.85
    THRESHOLD_REVIEW = 0.60

    def resolve(self, raw_category: str) -> dict:
        # 1. 别名精确匹配
        # 2. 语义相似度（embedding）
        # 3. 关键词映射兜底
        return {"matched_category_id": ..., "match_type": ..., "confidence": ...}
```

- [ ] **步骤 5：回归测试**

运行：`pytest tests/backend/test_structured_store.py tests/backend/test_query_service.py -v`
预期：PASS。

- [ ] **步骤 6：提交**

```bash
git add assistant/backend/model/sql_models.py assistant/backend/service/structured_store_service.py assistant/backend/service/query_service.py assistant/backend/utils/time_range.py assistant/backend/service/seed_data.py tests/backend/test_structured_store.py tests/backend/test_query_service.py
git commit -m "feat: 完成财务结构化存储与查询工具（含分类标准化与种子数据）"
```

### 任务 6：LangGraph 主流程（LLM 节点 + 工具节点）

**文件：**
- 创建：`assistant/backend/graph/chat_graph.py`
- 创建：`assistant/backend/service/reply_service.py`
- 修改：`assistant/backend/api/chat.py`

- [ ] **步骤 1：定义 LangGraph 状态 Schema**

```python
# assistant/backend/graph/chat_graph.py
from typing import TypedDict, Optional
from assistant.backend.model.schemas import LLMPlan

class GraphState(TypedDict):
    user_id: str
    message: str
    trace_id: str
    plan: Optional[LLMPlan]          # LLM 意图识别结果
    query_results: list[dict]        # SQLite 查询结果
    long_memory_results: list[dict]  # mem0 检索结果
    answer: str                      # 最终回复
    errors: list[str]                # 异常信息（不中断主流程）
```

- [ ] **步骤 2：先写失败测试（混合意图：一句话记账+提问）**

```python
# tests/backend/test_chat_api.py
def test_mixed_intent_store_and_query(client):
    “””同一句话既记账又查询”””
    resp = client.post(“/v1/chat”,
        json={“user_id”: “u1”, “message”: “今天午饭30块，帮我看看这个月餐饮花了多少”},
        headers={“Authorization”: “Bearer test-key”})
    assert resp.status_code == 200
    body = resp.json()
    assert “answer” in body
    assert body[“lang”] == “zh-CN”
    # 验证响应不等待异步存储完成
    assert “30” not in body.get(“answer”, “”) or “已记录” in body.get(“answer”, “”)
```

运行：`pytest tests/backend/test_chat_api.py -v`
预期：FAIL。

- [ ] **步骤 3：实现图节点（LLM计划 → 查询工具 → 回复生成 → 异步存储派发）**

```python
from langgraph.graph import StateGraph, END

def build_graph(settings) -> StateGraph:
    graph = StateGraph(GraphState)

    # 节点 1：LLM 意图识别
    graph.add_node(“plan”, plan_node)
    # 节点 2：查询执行
    graph.add_node(“query”, query_node)
    # 节点 3：回复生成
    graph.add_node(“reply”, reply_node)
    # 节点 4：异步存储派发（不阻塞）
    graph.add_node(“dispatch_store”, dispatch_store_node)

    graph.set_entry_point(“plan”)
    graph.add_edge(“plan”, “query”)
    graph.add_edge(“query”, “reply”)
    graph.add_edge(“reply”, “dispatch_store”)
    graph.add_edge(“dispatch_store”, END)

    return graph.compile()
```

- [ ] **步骤 4：实现回复服务（中文、解释型）**

```python
# assistant/backend/service/reply_service.py
class ReplyService:
    “””回复组装：结论 + 关键数字 + 建议动作，LLM 失败时走兜底模板”””

    FALLBACK_TEMPLATES = {
        “expense_record”: “已记录：{amount}元 {category}，{description}。”,
        “query_result”: “本月 {category} 共支出 {total} 元。”,
        “mixed”: “已记录 {amount} 元 {category}。本月该类别共支出 {total} 元。”,
    }

    def build_reply(self, state: GraphState) -> str:
        if state[“answer”]:
            return state[“answer”]
        # 兜底：模板拼接
        return self._build_fallback(state)
```

- [ ] **步骤 5：接入 chat API**

将 `app.py` 中的 `/v1/chat` 从直接返回改为调用 LangGraph。

- [ ] **步骤 6：回归测试**

运行：`pytest tests/backend/test_chat_api.py -v`
预期：PASS。

- [ ] **步骤 7：提交**

```bash
git add assistant/backend/graph/chat_graph.py assistant/backend/service/reply_service.py assistant/backend/api/chat.py tests/backend/test_chat_api.py
git commit -m “feat: 接入 LangGraph 对话主流程”
```

### 任务 7：短期记忆压缩与上下文保真

**文件：**
- 创建：`assistant/backend/service/short_memory_service.py`
- 创建：`tests/backend/test_short_memory.py`

- [ ] **步骤 1：先写失败测试（超过阈值自动压缩）**

运行：`pytest tests/backend/test_short_memory.py -v`
预期：FAIL。

- [ ] **步骤 2：实现压缩策略**

运行：消息数 > `summary_threshold` 时，摘要旧对话并保留最近 `max_turns`。
预期：上下文 token 可控，且历史关键信息可追溯。

- [ ] **步骤 3：回归测试**

运行：`pytest tests/backend/test_short_memory.py -v`
预期：PASS。

- [ ] **步骤 4：提交**

```bash
git add assistant/backend/service/short_memory_service.py tests/backend/test_short_memory.py
git commit -m "feat: 完成短期记忆压缩与保留策略"
```

### 任务 8：验收与可观测性

**文件：**
- 创建：`assistant/backend/utils/logging.py`
- 创建：`docs/phase1-acceptance-checklist.md`
- 创建：`tests/backend/test_acceptance.py`

> 注：日志基础设施应在任务 0/1 就初始化，任务 8 只做完善和脱敏策略。

- [ ] **步骤 1：实现 trace + 脱敏日志**

```python
# assistant/backend/utils/logging.py
import logging
import re
from contextvars import ContextVar

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")

class TraceFilter(logging.Filter):
    def filter(self, record):
        record.trace_id = trace_id_var.get()
        return True

def sanitize_amount(text: str) -> str:
    """日志中脱敏金额"""
    return re.sub(r"\d+\.\d{2}", "XXX.XX", text)

def setup_logging(level: str = "INFO"):
    handler = logging.StreamHandler()
    handler.addFilter(TraceFilter())
    formatter = logging.JSONFormatter(
        fmt='{"time":"%(asctime)s","level":"%(levelname)s","trace_id":"%(trace_id)s","msg":"%(message)s"}'
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper()))
```

- [ ] **步骤 2：编写验收清单（至少 20 条）**

参见 `docs/phase1-acceptance-checklist.md`，覆盖：
1. 中文对话正常
2. 纯记账输入正常落库
3. 纯查询输入返回数据
4. 混合意图（记账+查询）同时处理
5. 收入/支出方向识别正确
6. 一级分类命中
7. 二级分类命中
8. 低置信度进入 needs_review
9. 用户纠正后别名更新
10. 预算查询返回使用率
11. 时间范围（今天/本周/本月）解析正确
12. 异步存储不阻塞回复
13. mem0 不可用时系统降级运行
14. 短期记忆超过阈值自动压缩
15. 无 API Key 返回 401
16. 健康检查端点正常
17. 日志包含 trace_id
18. 日志金额已脱敏
19. 非法工具调用被拒绝
20. 数据库 WAL 模式启用

- [ ] **步骤 3：全量测试**

运行：`pytest tests/backend -v`
预期：PASS。

- [ ] **步骤 4：提交**

```bash
git add assistant/backend/utils/logging.py docs/phase1-acceptance-checklist.md tests/backend/test_acceptance.py
git commit -m "chore: 完成 phase1 验收标准与可观测性"
```

## 五、风险与应对

- 大模型抽取漂移：启用结构化输出校验 + 失败重试 + 规则兜底。
- 工具滥调用风险：仅允许白名单工具 + 参数 schema 严格校验。
- mem0 不可用：自动降级为”仅结构化查询回答”，记录告警（已在任务 4 实现）。
- 时间语义歧义：统一时区与固定解析规则（本周从周一开始）。
- SQLite 并发锁：启用 WAL 模式 + busy_timeout=5000 + 写入重试（已在任务 1/5 实现）。
- LangGraph API 变更：锁定 `langgraph>=1.0.10,<2.0.0`，避免 breaking changes。
- LLM 成本失控：小模型做意图识别 + 月度 token 预算监控 + 降级策略。

## 六、Phase 1 完成标准

- 用户可以用中文自然语言直接提问与记账，无需表单输入。
- 单条消息可同时完成”记录 + 查询”，系统先答复后异步入库。
- 收支与预算可被准确查询并由 LLM 输出可读解释。
- 三层记忆链路可用，短期记忆会自动压缩。
- 分类方向识别准确率（收入/支出）>= 98%，一级分类命中率 >= 95%。
- 低置信度分类必须进入 `needs_review` 或 `待分类`，不得静默误分类。
- 用户纠正后同类表达在后续 5 次内命中率显著提升（回归测试证明）。
- `tests/backend` 全部通过，验收清单通过率 >= 95%。
- 健康检查端点正常返回，mem0 降级可用。
- 日志包含 trace_id，金额已脱敏。
- 数据库启用 WAL 模式，分类种子数据已加载。

## 七、自检结论

- 需求覆盖：已覆盖你文档中的 Phase 1 核心闭环。
- 文档语言：已改为中文。
- 设计导向：已从“表单式录入”切换为“LLM 主导 + 工具执行”模式。
