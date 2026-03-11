## Bisheng Workflow Studio 前端集成文档

面向：前端工程师  
后端：FastAPI（`bisheng_generator/api.py`）  
API 版本：**0.2.0**

---

### 1. 服务基础信息

- **Base URL（本地开发）**: `http://localhost:8000`
- **Swagger / OpenAPI 文档**: `http://localhost:8000/docs`
- **内置 Demo 前端**: `http://localhost:8000/`
- **健康检查**: `GET /api/health` → `{ "status": "healthy", "version": "0.2.0" }`

主要需要对接的接口：

| 能力 | 方法 | 路径 |
|------|------|------|
| 生成工作流（流式，推荐） | POST / GET | `/api/generate/stream` |
| 生成工作流（同步 JSON） | POST | `/api/generate` |
| 会话列表 | GET | `/api/sessions` |
| 会话时间线（回放） | GET | `/api/sessions/{session_id}` |
| 删除会话（软删除） | DELETE | `/api/sessions/{session_id}` |
| 工作流列表 | GET | `/api/workflows` |
| 工作流详情 | GET | `/api/workflow/{filename}` |
| 下载工作流文件 | GET | `/api/download/{filename}` |
| 手动导入到毕昇 | POST | `/api/workflow/import` |
| 健康检查 | GET | `/api/health` |

**鉴权说明**：导入到毕昇（`auto_import` 或 `POST /api/workflow/import`）需在请求中携带 Cookie `access_token_cookie`（用户登录毕昇后由毕昇前端写入）。

**常见错误码**：

- `400`：参数错误（如续轮未传 `sessionId`、未传 `query`、导入时未传 `workflow`/`filename` 或工作流格式无效；**会话已删除时续轮**会返回「会话已删除，无法续轮」）。
- `404`：工作流文件不存在；或请求的会话已软删除（`GET /api/sessions/{session_id}` 返回 404）。
- `409`：续轮时会话已过期（thread/checkpoint 失效），需提示用户重新发起。
- `502`：导入毕昇失败（如 token 无效、网络错误）。

---

### 2. 同步生成接口：`POST /api/generate`

> 一般用于调试或简单脚本调用；正式前端建议优先使用流式接口 `/api/generate/stream`。

#### 2.1 请求体（`GenerateRequest`）

```json
{
  "query": "创建一个深汕招商政策查询助手",
  "config": {
    "auto_import": true
  },
  "sessionId": "abcd1234efgh5678",
  "threadId": "thread_xyz_optional",
  "isResume": false,
  "originalQuery": null
}
```

- **`query`** `string`（必填）
  - 首轮：用户自然语言需求。
  - 续轮：根据澄清类型不同：
    - 意图澄清：用户补充说明文本。
    - 流程方案选择：选中的方案 ID（如 `"full"` / `"medium"` / `"simple"`）。

- **`config`** `object | null`（可选）
  - 高级配置，目前主要用：
    - `auto_import: boolean` – 是否在生成后自动导入到毕昇平台并上线。
  - 不关心可传 `{}` 或省略。

- **`sessionId`** `string | null`
  - 会话 ID。
  - 首轮可不传，后端会自动生成并返回。
  - 续轮（`isResume=true`）**必须传**首轮的 `session_id`。

- **`threadId`** `string | null`（可选，别名 `thread_id`）
  - 仅用于 LangGraph checkpointer 的 `thread_id`，与「会话列表、时间线、删除」等无关。
  - 同一轮生成（含续轮澄清/选方案）使用同一 `threadId`；生成完成后再发新问题时使用新的 `threadId`，可避免上一轮 checkpoint 干扰。
  - 不传时后端使用 `sessionId` 作为 `thread_id`（与旧版行为一致）。

- **`isResume`** `boolean`
  - 是否为续轮：
    - 首轮：`false`
    - 续轮：`true`

- **`originalQuery`** `string | null`（别名 `original_query`）
  - 首轮用户原始输入，续轮时建议原样传回，用于模型恢复上下文。
  - 可从 `pending_clarification.original_user_input` 读取。

> **请求体字段名**：后端 Pydantic 模型支持 **camelCase**（`sessionId`、`threadId`、`isResume`、`originalQuery`）与 **snake_case**（`session_id`、`thread_id`、`is_resume`、`original_query`），二者等价。

#### 2.2 响应体（`GenerateResponse`）

```json
{
  "status": "success",
  "message": "工作流生成成功",
  "workflow": { "...": "完整毕昇工作流 JSON" },
  "metadata": {
    "intent": {
      "workflow_type": "工具调用",
      "needs_tool": true,
      "needs_knowledge": true
    },
    "tools_count": 3,
    "knowledge_count": 2,
    "flow_sketch_mermaid": "graph TD; start --> input; ..."
  },
  "flow_sketch_mermaid": "graph TD; start --> input; ...",
  "error": null,
  "file_path": "output/workflow_1710000000.json",
  "import_result": {
    "flow_id": 123,
    "version_id": 456,
    "published": true,
    "chat_url": "https://bisheng/chat/xxx",
    "flow_edit_url": "https://bisheng/flows/xxx/edit"
  },
  "import_error": null,
  "session_id": "abcd1234efgh5678",
  "needs_clarification": false,
  "pending_clarification": null
}
```

关键字段：

- **`status`**: `"success"` 或 `"error"`。
- **`workflow`**: 最终生成的毕昇工作流 JSON。
- **`metadata`**:
  - `intent`: 意图信息（`workflow_type`、`needs_tool` 等）。
  - `tools_count` / `knowledge_count`: 使用的工具 / 知识库数量。
  - `flow_sketch_mermaid`: 流程图草图的 Mermaid 文本。
- **`flow_sketch_mermaid`**: 冗余给一份草图 Mermaid，便于前端渲染。
- **`file_path`**: 本地保存的 `workflow_*.json` 文件路径。
- **`import_result`**（当 `auto_import = true` 且导入成功时存在）：
  - `flow_id` / `version_id` / `published`
  - `chat_url`: 毕昇聊天链接
  - `flow_edit_url`: 毕昇工作流编辑页链接
- **`needs_clarification`**: `true` 则表示本次请求只是告诉前端“需要澄清/选择方案”，不会给出最终工作流。
- **`pending_clarification`**: 澄清详情，详见第 4 节。

---

### 3. 流式生成接口：`/api/generate/stream`

> 推荐前端统一使用此接口；可实时获取进度、澄清提示、最终结果。

#### 3.1 请求方式

##### POST（推荐）

```http
POST /api/generate/stream
Content-Type: application/json
Accept: text/event-stream
```

请求体与 `GenerateRequest` 完全一致：

```json
{
  "query": "创建一个招商政策查询助手",
  "config": { "auto_import": true },
  "sessionId": null,
  "threadId": null,
  "isResume": false,
  "originalQuery": null
}
```

##### GET（可选）

GET 方式通过 **query 参数**传参（均为 snake_case）：

```http
GET /api/generate/stream?query=用户需求描述&session_id=xxx&thread_id=yyy&is_resume=true&original_query=首轮用户输入
Accept: text/event-stream
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | 是 | 用户查询（首轮）或澄清回复/方案 ID（续轮） |
| `session_id` | string | 续轮必填 | 会话 ID（时间线、列表、删除等） |
| `thread_id` | string | 否 | 仅用于 checkpointer 隔离；不传则用 `session_id` |
| `is_resume` | string | 否 | 续轮时为 `true`、`1` 或 `yes`（不区分大小写） |
| `original_query` | string | 续轮建议 | 首轮用户原始输入 |

两种方式等价，返回的都是 **SSE** 事件流。

#### 3.2 SSE 响应格式

HTTP 头：

```http
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
Transfer-Encoding: chunked
```

事件格式：每条为一行 `data:` 加 JSON，**无 `event:` 行**，事件类型在 JSON 的 `event_type` 字段中：

```text
data: {"event_type":"agent_complete","agent_name":"tool_selection","message":"...", ...}

```

每条 `data:` 后都是一个 JSON，结构为 `ProgressEvent`。

#### 3.3 事件模型：`ProgressEvent`

通用结构：

```json
{
  "event_type": "agent_complete",
  "timestamp": "2026-03-03T21:18:11.623Z",
  "agent_name": "tool_selection",
  "data": { "tools_count": 3 },
  "message": "✅ 工具选择完成：选中 3 个工具",
  "progress": 50.0,
  "duration_ms": 1800.5,
  "error": null
}
```

#### 3.3.1 `event_type` 取值

- **`"start"`**
  - 仅首轮发送一条，表示“开始生成工作流”。
  - 续轮（`isResume=true`）不会再次发送。

- **`"agent_start"`**
  - 某个阶段 Agent 开始执行。
  - 搭配 `agent_name` 使用。

- **`"agent_complete"`**
  - 某个阶段 Agent 执行完成。
  - `data` 内带有该阶段的统计信息（工具数、知识库数、草图节点数等）。

- **`"agent_error"`**
  - 某个阶段 Agent 执行失败，`error` 字段为原因。

- **`"needs_clarification"`**
  - 图在某个节点被 `interrupt` 暂停，等待用户澄清或选择流程方案。
  - `data.pending_clarification` 提供具体问题 / 候选方案。

- **`"complete"`**
  - 全流程成功完成。
  - `data.workflow` + `data.metadata` 为最终结果。

- **`"error"`**
  - 整体生成失败。

#### 3.3.2 `agent_name` 取值

- `"intent_understanding"`：意图理解
- `"tool_selection"`：工具选择
- `"knowledge_matching"`：知识库匹配
- `"flow_sketch"`：流程图草图生成
- `"workflow_generation"`：完整工作流生成
- `"import"`：导入毕昇

#### 3.3.3 常见 `data` 结构

- 意图理解完成：

```json
{
  "workflow_type": "工具调用",
  "needs_tool": true,
  "needs_knowledge": true,
  "rewritten_input": "规范化后的需求"
}
```

- 工具选择完成：

```json
{
  "tools_count": 3,
  "selected_tools": [
    { "name": "天气查询", "description": "...", "tool_key": "..." }
  ]
}
```

- 知识库匹配完成：

```json
{
  "knowledge_count": 2,
  "matched_knowledge_bases": [
    { "name": "招商政策库", "description": "...", "id": 6 }
  ]
}
```

- 流程图草图完成（单草图模式）：

```json
{
  "nodes_count": 12,
  "flow_sketch_mermaid": "graph TD; start --> input; ..."
}
```

- 需要澄清：

```json
{
  "needs_clarification": true,
  "pending_clarification": { "... 见第 4 节 ..." },
  "session_id": "abcd1234efgh5678"
}
```

- 最终完成（`event_type === "complete"` 时，`data` 为完整 result，与同步接口一致）：

```json
{
  "status": "success",
  "workflow": { "... 工作流 JSON ..." },
  "metadata": {
    "intent": { "... 意图信息 ..." },
    "tools_count": 3,
    "knowledge_count": 2,
    "flow_sketch_mermaid": "graph TD; ..."
  },
  "file_path": "output/workflow_1710000000.json",
  "session_id": "abcd1234efgh5678",
  "import_result": { "flow_id": 123, "chat_url": "...", "flow_edit_url": "..." }
}
```

  - 若开启了 `config.auto_import` 且导入成功，`import_result` 会存在，可用于展示「打开聊天」「编辑工作流」等链接。

---

### 4. `needs_clarification` 场景

当 `event_type === "needs_clarification"` 时：

```json
{
  "event_type": "needs_clarification",
  "message": "⏸️ 需要您补充更多信息",
  "data": {
    "needs_clarification": true,
    "pending_clarification": { "... 看 type 字段 ..." },
    "session_id": "abcd1234efgh5678"
  },
  "progress": 10.0
}
```

前端关心：

- `data.session_id`：续轮时必须带回。
- `pending_clarification` 的形态决定用哪种 UI：
  - 若存在 **`questions`** 数组且无 **`options`** → 意图澄清（见 4.1）。
  - 若存在 **`type === "flow_sketch_selection"`** 且含 **`options`** → 流程图草图多方案选择（见 4.2）。

#### 4.1 意图澄清（存在 `questions`）

当前端收到 `event_type === "needs_clarification"` 且 `pending_clarification.questions` 存在时，按意图澄清处理。示例：

```json
{
  "message": "请补充以下信息，以便更准确生成工作流",
  "questions": [
    "你主要想查询哪些类型的政策？",
    "是否需要接入企业信息查询？"
  ],
  "rewritten_input_preview": "规范化后的需求预览",
  "original_user_input": "用户首轮原始输入"
}
```

（后端可能不返回 `type` 字段，以 `questions` 存在且无 `options` 判断即可。）

前端建议：

1. 在聊天中展示 `message` + `questions` 列表。
2. 输入框 placeholder 设为“请补充信息以继续…”，用户输入一段自然语言回答。
3. 用户发送后，调用 `/api/generate/stream` 续轮：

```json
{
  "query": "我需要查询深汕招商相关政策，并接入企业信用信息",
  "config": {},
  "sessionId": "abcd1234efgh5678",
  "isResume": true,
  "originalQuery": "original_user_input"
}
```

后端会继续执行后续节点，最终发出 `complete` 事件。

#### 4.2 流程方案多选：`type === "flow_sketch_selection"`

三种方案按**复杂度从高到低**呈现：完整版 → 适中版 → 精简版，供用户选择其一继续生成工作流。

示例：

```json
{
  "type": "flow_sketch_selection",
  "stage": "flow_sketch",
  "message": "我们为当前需求准备了三种不同复杂度的流程方案（完整版 → 适中版 → 精简版），请选择一种继续生成。",
  "options": [
    {
      "id": "full",
      "title": "完整版",
      "description": "步骤最全、分支清晰，适合需要区分多种情况、后续还要扩展的场景。",
      "nodes_count": 11,
      "mermaid": "graph TD; start --> input; ..."
    },
    {
      "id": "medium",
      "title": "适中版",
      "description": "只保留核心步骤和主要分支，结构清晰、便于理解。",
      "nodes_count": 8,
      "mermaid": "graph TD; ..."
    },
    {
      "id": "simple",
      "title": "精简版",
      "description": "步骤最少、一条主流程，先确认「是不是这个意思」再细化。",
      "nodes_count": 6,
      "mermaid": "graph TD; ..."
    }
  ],
  "original_user_input": "用户首轮输入",
  "intent_rewritten_input": "规范化后的意图"
}
```

前端建议：

1. 聊天区显示“流程方案”卡片。
2. 每个 `options[i]` 渲染为**一行可折叠的方案**：
   - 折叠头：标题 + 简短描述（`description`，面向非技术用户）+ 步骤数。
   - 展开体：描述 + 用 `mermaid` 渲染的流程图 + “使用该方案”按钮。
3. 用户点击“使用该方案”后：
   - 在聊天中插入一条“选择流程图方案：XXX”的用户消息；
   - 调用 `/api/generate/stream` 续轮：

```json
{
  "query": "simple",
  "config": {},
  "sessionId": "abcd1234efgh5678",
  "isResume": true,
  "originalQuery": "original_user_input"
}
```

4. 后端行为：
   - 在 `flow_sketch` 节点恢复执行，根据 `query` 选中对应草图写入 `state.flow_sketch`；
   - 继续执行 `workflow_generation` 节点，使用该草图生成完整工作流；
   - SSE 中会继续发出 `agent_start/agent_complete`（`flow_sketch`、`workflow_generation`）以及最终 `complete` 事件。

---

### 5. 历史与工作流管理接口

#### 5.1 `GET /api/sessions`

返回最近会话列表（用于左侧「历史会话」）。**已软删除的会话不会出现在列表中**。仅当已配置 MySQL/SQLite 时返回数据，否则返回空数组 `[]`。

**Query 参数**：`limit`（可选，默认 100，单页条数）

**响应示例**：

```json
[
  {
    "session_id": "abcd1234efgh5678",
    "preview": "用户首轮输入的前 80 字…",
    "last_at": "2026-03-10T12:34:56.000000",
    "is_executing": false
  }
]
```

- `preview`：该会话第一条用户消息的内容截断（最多 80 字）；若无则取 `session_id` 前 16 位。
- `last_at`：该会话最后活动时间，ISO 8601 字符串。
- `is_executing`：该会话是否正在执行流式生成（`true` 时表示当前有流式请求在进行，可用于左侧列表展示「执行中」状态）。

#### 5.2 `DELETE /api/sessions/{session_id}`

软删除会话：将会话标记为已删除。删除后该会话**不再出现在列表**且**不可续轮**（续轮请求会返回 400「会话已删除，无法续轮」）。时间线数据仍保留在库中，仅通过 `session_meta` 表标记删除。

**Path**：`session_id` 为要删除的会话 ID。

**响应**：`204 No Content`（成功）；`400` 表示 `session_id` 为空；`500` 表示未启用数据库或删除失败。

#### 5.3 `GET /api/sessions/{session_id}`

返回该会话的完整时间线（用于回放）。**若该会话已软删除，返回 `404`**。仅当已配置 MySQL/SQLite 时返回数据，否则 `timeline` 为空数组。

**Path**：`session_id` 为会话 ID。  
**Query 参数**：`limit`（可选，默认 500，时间线条数）

**响应示例**：

```json
{
  "session_id": "abcd1234efgh5678",
  "timeline": [
    {
      "id": 1,
      "item_type": "message",
      "sort_key": "2026-03-10T12:34:56.000000",
      "payload": { "role": "user", "content": "创建一个招商政策查询助手" }
    },
    {
      "id": 2,
      "item_type": "progress_event",
      "sort_key": "2026-03-10T12:35:00.000000",
      "payload": { "event_type": "start", "message": "🚀 开始生成工作流", ... }
    },
    {
      "id": 3,
      "item_type": "progress_event",
      "sort_key": "2026-03-10T12:35:30.000000",
      "payload": { "event_type": "complete", "data": { "workflow": {...}, "metadata": {...} }, ... }
    }
  ]
}
```

- `id`：时间线记录主键。
- `item_type`：`"message"` 或 `"progress_event"`。
- `sort_key`：该条目的时间戳（ISO 8601），按此升序排列。
- `payload`：消息时为 `{ role, content }`；进度事件时为完整的 `ProgressEvent` 对象（含 `event_type`、`data` 等）。

前端渲染建议：

- `item_type = "message"`：根据 `payload.role`（user/assistant）渲染气泡。
- `item_type = "progress_event"`：根据 `payload.event_type` 处理；
  - `needs_clarification`：插入澄清/草图选择 UI（使用 `payload.data.pending_clarification`）。
  - `complete` 且 `payload.data.workflow` 存在：插入结果卡片。
  - 其它可简略显示为阶段日志或忽略。

#### 5.4 工作流文件管理

- **`GET /api/workflows`**：返回本地 `output` 目录下所有已保存的 `workflow_*.json` 文件列表，按文件修改时间倒序。响应为数组，每项形如：

```json
{
  "filename": "workflow_1710000000.json",
  "filepath": "output/workflow_1710000000.json",
  "created_at": 1710000000.0,
  "size": 12345
}
```

  - `created_at` 为 Unix 时间戳（秒，浮点）。
  - 若 `output` 不存在或为空，返回 `[]`。

- **`GET /api/workflow/{filename}`**：返回 `{ "filename": "<filename>", "workflow": <完整工作流 JSON> }`。文件不存在时 404。
- **`GET /api/download/{filename}`**：以 `application/json` 形式返回工作流 JSON，并带 `Content-Disposition: attachment; filename=...`，供浏览器下载。
- **`POST /api/workflow/import`**：将工作流导入到毕昇平台，需 Cookie 中携带 `access_token_cookie`。请求体：

```json
{
  "workflow": { "...": "完整工作流 JSON" },
  "filename": null,
  "name": "可选：在毕昇中的展示名称（不传则用工作流内 name 或「导入的工作流」+ 时间戳）",
  "publish": true
}
```

- `workflow` 与 `filename` **二选一**：传 `workflow` 直接提交 JSON；传 `filename` 则从本地 `output/` 下读取已保存文件。
- 工作流格式需包含 `nodes` 和 `edges`，否则返回 400。

**响应**（成功 200）：

```json
{
  "status": "success",
  "message": "已导入到毕昇",
  "import_result": {
    "flow_id": 123,
    "version_id": 456,
    "published": true,
    "chat_url": "https://<bisheng_base>/workspace/chat/<chat_id>/<flow_id>/10",
    "flow_edit_url": "https://<bisheng_base>/flow/<flow_id>"
  }
}
```

导入失败时返回 502，detail 为错误信息。

---

### 6. 前端集成简要伪代码

- **GET 流式**：可使用 `EventSource`，仅支持 GET，参数通过 URL query 传递。
- **POST 流式**：需使用 `fetch(url, { method: 'POST', body: JSON.stringify(body), headers: { 'Content-Type': 'application/json' } })` + 对返回 body 做 SSE 解析（按 `\n\n` 分行，取 `data:` 后 JSON 解析）。

以下为 GET 方式的极简示例（SSE 每条为 `data: <JSON>`，无 `event:` 行）：

```js
function startGeneration(userQuery) {
  const params = new URLSearchParams({
    query: userQuery
  });
  const es = new EventSource('/api/generate/stream?' + params.toString());

  es.onmessage = (ev) => {
    const d = JSON.parse(ev.data); // ProgressEvent

    if (d.event_type === 'start') {
      // 更新 UI：开始生成
    } else if (d.event_type === 'agent_start' || d.event_type === 'agent_complete') {
      // 根据 d.agent_name / d.progress / d.data 更新步骤进度
    } else if (d.event_type === 'needs_clarification') {
      const data = d.data || {};
      const pending = data.pending_clarification || {};
      const sid = data.session_id;

      if (pending.questions && !pending.options) {
        showIntentClarification(pending, sid);
      } else if (pending.type === 'flow_sketch_selection' && pending.options) {
        showFlowSketchOptions(pending, sid);
      }
      es.close();
    } else if (d.event_type === 'complete') {
      const payload = d.data || {};
      showFinalWorkflow(payload.workflow, payload.metadata);
      es.close();
    } else if (d.event_type === 'error') {
      showError(d.message || d.error);
      es.close();
    }
  };
}
```

续轮（澄清 / 选择方案）时，同样调用 `/api/generate/stream`：

- **GET**：`query=...&session_id=xxx&is_resume=true&original_query=首轮用户输入`，其中 `query` 为补充说明或选中的方案 ID。
- **POST**：请求体 `{ "query": "补充说明或方案ID", "sessionId": "xxx", "isResume": true, "originalQuery": "首轮用户输入" }`。

