## Bisheng Workflow Studio 前端集成文档

面向：前端工程师  
后端：FastAPI（`bisheng_generator/api.py`）

---

### 1. 服务基础信息

- **Base URL（本地开发）**: `http://localhost:8000`
- **Swagger / OpenAPI 文档**: `http://localhost:8000/docs`
- **内置 Demo 前端**: `http://localhost:8000/`

主要需要对接的接口：

- 生成工作流（流式，推荐）: `POST /api/generate/stream` 或 `GET /api/generate/stream`
- 生成工作流（同步 JSON）: `POST /api/generate`
- 会话历史与回放: `GET /api/sessions`、`GET /api/sessions/{sessionId}`
- 工作流文件管理: `GET /api/workflows`、`GET /api/workflow/{filename}`、`GET /api/download/{filename}`、`POST /api/workflow/import`

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
  "isResume": false,
  "originalQuery": null
}
```

- **`query`** `string`（必填）
  - 首轮：用户自然语言需求。
  - 续轮：根据澄清类型不同：
    - 意图澄清：用户补充说明文本。
    - 草图选择：选中的草图方案 ID（如 `"simple_exec_first"`）。

- **`config`** `object | null`（可选）
  - 高级配置，目前主要用：
    - `auto_import: boolean` – 是否在生成后自动导入到毕昇平台并上线。
  - 不关心可传 `{}` 或省略。

- **`sessionId`** `string | null`
  - 会话 ID。
  - 首轮可不传，后端会自动生成并返回。
  - 续轮（`isResume=true`）**必须传**首轮的 `session_id`。

- **`isResume`** `boolean`
  - 是否为续轮：
    - 首轮：`false`
    - 续轮：`true`

- **`originalQuery`** `string | null`
  - 首轮用户原始输入，续轮时建议原样传回，用于模型恢复上下文。
  - 可从 `pending_clarification.original_user_input` 读取。

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
  "isResume": false,
  "originalQuery": null
}
```

##### GET（可选）

```http
GET /api/generate/stream?query=...&session_id=...&is_resume=true&original_query=...
Accept: text/event-stream
```

两种方式等价，返回的都是 **SSE** 事件流。

#### 3.2 SSE 响应格式

HTTP 头：

```http
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

事件示例：

```text
event: progress
data: {"event_type":"agent_complete","agent_name":"tool_selection", ...}

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
  - 图在某个节点被 `interrupt` 暂停，等待用户澄清或选择草图方案。
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

- 最终完成：

```json
{
  "workflow": { "... 工作流 JSON ..." },
  "metadata": {
    "intent": { "... 意图信息 ..." },
    "tools_count": 3,
    "knowledge_count": 2,
    "flow_sketch_mermaid": "graph TD; ..."
  }
}
```

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

- `session_id`: 续轮时必须带回。
- `pending_clarification.type`: 决定用哪种 UI。

#### 4.1 意图澄清：`type = "intent_clarification"`

示例：

```json
{
  "type": "intent_clarification",
  "message": "请补充以下信息，以便更准确生成工作流",
  "questions": [
    "你主要想查询哪些类型的政策？",
    "是否需要接入企业信息查询？"
  ],
  "rewritten_input_preview": "规范化后的需求预览",
  "original_user_input": "用户首轮原始输入"
}
```

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

#### 4.2 流程图草图多方案选择：`type = "flow_sketch_selection"`

示例：

```json
{
  "type": "flow_sketch_selection",
  "stage": "flow_sketch",
  "message": "已为当前需求生成多个流程图草图方案，请选择一个用于后续完整工作流生成。",
  "options": [
    {
      "id": "simple_exec_first",
      "title": "方案A：上线可执行优先",
      "description": "流程尽量简单、节点数少、便于快速上线…",
      "nodes_count": 10,
      "mermaid": "graph TD; start --> input; ..."
    },
    {
      "id": "robust_high_accuracy",
      "title": "方案B：准确性与鲁棒性优先",
      "description": "增加检索/校验/异常兜底，提高整体准确率和鲁棒性…",
      "nodes_count": 16,
      "mermaid": "graph TD; ..."
    }
  ],
  "original_user_input": "用户首轮输入",
  "intent_rewritten_input": "规范化后的意图"
}
```

前端建议：

1. 聊天区显示“候选草图”卡片。
2. 每个 `options[i]` 渲染为**一行可折叠的方案**：
   - 折叠头：标题 + 简短描述 + 节点数 + ID。
   - 展开体：详细描述 + 用 `mermaid` 字符串渲染的完整流程图 + “使用该方案”按钮。
3. 用户点击“使用该方案”后：
   - 在聊天中插入一条“选择流程图方案：XXX”的用户消息；
   - 调用 `/api/generate/stream` 续轮：

```json
{
  "query": "simple_exec_first",
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

返回最近会话列表（用于左侧“历史会话”）：

```json
[
  {
    "session_id": "abcd1234efgh5678",
    "preview": "用户首轮输入的前 60 字…",
    "last_at": "2026-03-10T12:34:56.000Z"
  }
]
```

#### 5.2 `GET /api/sessions/{sessionId}`

返回该会话的时间线（用于回放）：

```json
{
  "session_id": "abcd1234efgh5678",
  "timeline": [
    {
      "item_type": "message",
      "payload": { "role": "user", "content": "创建一个招商政策查询助手" }
    },
    {
      "item_type": "progress_event",
      "payload": { "... ProgressEvent JSON ..." }
    },
    {
      "item_type": "message",
      "payload": { "role": "assistant", "content": "澄清问题..." }
    },
    {
      "item_type": "progress_event",
      "payload": { "... 最终 complete 事件 ..." }
    }
  ]
}
```

前端可以按以下逻辑渲染：

- `item_type = "message"`：根据 `role=user/assistant` 渲染气泡。
- `item_type = "progress_event"`：
  - `event_type = "needs_clarification"`：插入澄清/草图选择 UI。
  - `event_type = "complete"` 且带有 `data.workflow`：插入结果卡片。
  - 其它事件可简略显示为阶段日志或忽略。

#### 5.3 工作流文件管理

- `GET /api/workflows`：返回本地 `output` 目录下所有已保存的 `workflow_*.json` 文件（文件名、大小、创建时间等）。
- `GET /api/workflow/{filename}`：返回 `{ filename, workflow }`，`workflow` 为完整 JSON。
- `GET /api/download/{filename}`：直接下载该 JSON 文件。
- `POST /api/workflow/import`：

```json
{
  "workflow": { "...": "完整工作流 JSON" }, // 与 filename 二选一
  "filename": null,
  "name": "可选：在毕昇中的展示名称",
  "publish": true
}
```

返回：

```json
{
  "status": "success",
  "message": "已导入到毕昇",
  "import_result": {
    "flow_id": 123,
    "version_id": 456,
    "published": true,
    "chat_url": "https://bisheng/chat/xxx",
    "flow_edit_url": "https://bisheng/flows/xxx/edit"
  }
}
```

---

### 6. 前端集成简要伪代码

下方是一个极简的前端集成示例，展示如何使用 SSE 接口：

```js
function startGeneration(userQuery) {
  const params = new URLSearchParams({ query: userQuery });
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

      if (pending.type === 'intent_clarification') {
        showIntentClarification(pending, sid);
      } else if (pending.type === 'flow_sketch_selection') {
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

续轮（澄清 / 选择方案）时，同样调用 `/api/generate/stream`，但需要：

- 带上 `session_id`；
- 设置 `is_resume=true`；
- `query` 填补充说明或方案 ID。

