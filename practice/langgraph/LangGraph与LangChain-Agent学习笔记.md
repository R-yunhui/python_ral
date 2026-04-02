# LangGraph 与 LangChain Agent 学习笔记

> 便于复习：图编排、`create_agent`、中间件、记忆与存储、编译/调用参数、interrupt 等概念梳理。  
> 环境参考：`langchain` 1.2.x、`langgraph` 1.x、`deepagents`（可选）。

---

## 1. 图（Graph）与 Agent 的本质区别

- **LangGraph `StateGraph`**：用状态 + 节点 + 边做**流程编排**（分支、子图、`interrupt` 等）。
- **LangChain `create_agent`**：在实现上是框架生成的一张**「模型 ↔ 工具」循环图**，不是「任意图都能挂中间件」。
- **关系**：Agent **可以**作为大图里的**一个节点/子图**；**编排用 Graph，工具循环用 Agent** 是常见组合。
- **LangChain Agent 中间件**：由 `create_agent` 工厂**织入**固定拓扑（`model` / `tools` 与 `wrap_model_call` 等），**不能**指望把手写 `StateGraph` 和 `middleware=[...]` 一拼就自动生效；需要中间件时应用 **`create_agent(..., middleware=[...])` 得到子图再嵌套**，或在节点里手写等价逻辑。

---

## 2. LangChain 预置中间件（`langchain.agents.middleware`）

与厂商无关、通过 `create_agent(..., middleware=[...])` 使用，例如：

| 中间件 | 作用概要 |
|--------|----------|
| `SummarizationMiddleware` | 触达 token/条数阈值时压缩历史 |
| `HumanInTheLoopMiddleware` | 工具执行前人工批准/编辑/拒绝（需 checkpointer） |
| `ModelCallLimitMiddleware` / `ToolCallLimitMiddleware` | 限制模型/工具调用次数 |
| `ModelFallbackMiddleware` / `ModelRetryMiddleware` / `ToolRetryMiddleware` | 降级与重试 |
| `PIIMiddleware` | PII 检测与脱敏策略 |
| `TodoListMiddleware` | `write_todos` 规划工具 |
| `LLMToolSelectorMiddleware` | 调用主模型前先筛选工具 |
| `LLMToolEmulator` | 用 LLM 模拟工具（测试） |
| `ContextEditingMiddleware` | 清理较早 tool 输出等 |
| `ShellToolMiddleware` / `FilesystemFileSearchMiddleware` | Shell、Glob/Grep 等 |

**Deep Agents 包**（`deepagents`）另含：`FilesystemMiddleware`、`SubAgentMiddleware`、`MemoryMiddleware`（AGENTS.md 等）等，与 `create_agent` / `create_deep_agent` 组合使用。

**厂商专用中间件**需在对应集成包与文档中查看（如 Anthropic / OpenAI / Bedrock）。

---

## 3. 用装饰器写的「钩子类」中间件（`langchain.agents.middleware.types`）

| 装饰器 | 调用时机（语义） |
|--------|------------------|
| `@before_agent` | 本次 `invoke` 进入 Agent **入口**时（偏一次） |
| `@after_agent` | 本次 Agent **整体结束**时 |
| `@before_model` | **每次**调用主模型**之前**（含工具回到模型前的每一轮） |
| `@after_model` | **每次**主模型返回并写入 state **之后** |
| `@wrap_model_call` | **包裹真实 ChatModel 调用**（可重试、换模型、改 request/response） |
| `@dynamic_prompt` | 基于 `wrap_model_call` 只动态改 **system prompt** |
| `@wrap_tool_call` | **包裹每次工具执行** |
| `@hook_config(can_jump_to=...)` | 声明 `before_model`/`after_model` 可 `jump_to`：`model` / `tools` / `end` |

**粗略循环顺序**：`before_agent` →（循环）`before_model` → `wrap_model_call`（含模型）→ `after_model` → 工具（`wrap_tool_call`）→ 再回到 `before_model` → … → `after_agent`。

### `wrap_tool_call` 补充：`handler`、`await` 与 `astream` / `ainvoke`

- **`handler` 本身不是协程对象**，它是框架传入的**可调用对象**（内部对应 `ToolNode` 里的 `execute` 或 `_sync_execute`）。
- **`handler(request)`** 的返回值：若当前路径上 `handler` 是 **`async def execute`**，则**这一次调用**返回的是**协程对象**，必须用 **`await handler(request)`** 才能得到 `ToolMessage | Command`；若未 `await` 就把返回值当结果往上抛，会出现 **`Unsupported message type: coroutine`**、`execute was never awaited` 一类错误。
- **是否与「工具写成 `async def`」无关**：同步工具 / 异步工具由框架在 `handler` 内部通过 **`tool.ainvoke` / `tool.invoke`** 处理；中间件里一般**不必**为工具是否 async 写两套分支。
- **`astream` / `ainvoke`（异步跑图）** 会走 `ToolNode` 的**异步路径**（`_arun_one`）。此时若你的中间件是 **`async def` + `@wrap_tool_call`**（注册为 **`awrap_tool_call`**），传进来的 **`handler` 就是异步的 `execute`** → **必须 `await handler(request)`**。
- 若中间件是**纯同步** **`def` + `@wrap_tool_call`**（仅有 **`wrap_tool_call`**、没有 `awrap_tool_call`），即使用 **`astream`**，框架仍会传入**同步**的 **`_sync_execute`** → 应 **`return handler(request)`**，**不要** `await`。
- **实践建议**：用 `astream`/`ainvoke` 时，自定义工具包装统一写 **`async def` + `await handler(request)`** 最简单；避免在同一个 `middleware` 列表里叠两层 `wrap_tool_call` 却一层忘了 `await`。

---

## 4. Checkpointer、Store、Cache

| 机制 | 存什么 | 典型用途 |
|------|--------|----------|
| **Checkpointer** | 按 `thread_id` 的**图执行快照**（channel 状态、步骤、interrupt 点等） | 同一会话**续跑**、`interrupt`/`Command(resume)`、多轮 state |
| **Store** | **跨 thread** 的命名空间 KV/文档（可选向量检索） | 长期记忆、用户画像、跨会话知识；**需主动读写** |
| **Cache** | 带 TTL 的缓存键值 | **加速**重复计算；可清空，非「会话真相来源」 |

**上下文怎么理解：**

- **会话内**可恢复的 state/消息：主要靠 **state + Checkpointer**（外加摘要/截断控长度）。
- **跨会话**事实与画像：**Store 或业务库**，不是 checkpoint 的子集；二者**正交**。
- Checkpoint **不是**「人类意义上会话的全部上下文」：未写进 state 的临时量、环境变量、代码里写死的 prompt 等**不会**自动进 checkpoint。

---

## 5. 记忆与结构化数据（设计分层）

- **工作记忆**：`messages` 等进 state + Checkpointer；过长用摘要或截断。
- **长期记忆**：Store / 向量库，按 user/租户 namespace；**读时裁剪 top-k**。
- **用户画像**：强 schema，可与「记忆条目」分库存；低频更新、按需注入。
- **订单/任务等强一致数据**：业务 DB + **工具**访问；state 只放本轮需要的子集或 ID。

---

## 6. 动态建图

- **按请求拼 `StateGraph`**：只对本次需要的节点 `add_node` / `add_edge` 再 **`compile()`**（可缓存编译结果）。
- **单图 + 条件边**：所有节点注册在一张图里，用路由只走子路径；未执行节点本轮不跑。
- **`create_agent` 返回的图**可 **`name=`** 后作为**子图节点**嵌进父图。

---

## 7. `StateGraph.compile(...)` 要点

| 参数 | 含义 |
|------|------|
| `checkpointer` | 会话快照；`interrupt` 依赖它；`config` 里需 `thread_id` |
| `store` | 跨 thread 存储（与 Store API 配合） |
| `cache` | 图级缓存 |
| `interrupt_before` / `interrupt_after` | 在指定**节点名前/后**由框架暂停 |
| `debug` | 调试输出 |
| `name` | 编译图名称（子图、追踪用） |

---

## 8. `CompiledStateGraph.ainvoke(...)` 要点

| 参数 | 含义 |
|------|------|
| `input` | 首次：状态字典；恢复：`Command(resume=...)` |
| `config` | `RunnableConfig`，常用 `configurable.thread_id` |
| `context` | 若定义了 `context_schema` 的静态上下文 |
| `stream_mode` | 默认 `"values"` 聚合为最终状态；含 interrupt 时结果中带 `__interrupt__` |
| `interrupt_before` / `interrupt_after` | **单次调用**级打断（与 compile 同类语义） |
| `durability` | checkpoint 持久化时机（sync/async/exit 等） |

---

## 9. `interrupt(payload)` vs `interrupt_before` / `interrupt_after`

- **`interrupt(value)`（节点内）**：在**节点内部任意位置**暂停；`value` 可动态（如 dict）；需 **checkpointer**；`Command(resume=...)` 继续；**resume 后该节点会从头再执行**（注意节点内 interrupt 前的副作用幂等）。
- **`interrupt_before` / `interrupt_after`**：只在**节点边界**停；没有节点内自定义的 `value`，除非事先写入 state。

**粒度与信息丰富度**：节点内 `interrupt` 更细、payload 更自由；边界 interrupt 更声明式。

---

## 10. `SummarizationMiddleware` 如何确认「是否执行」

- 框架**无**专门 info 日志；靠 **触发条件**与**状态特征**判断。
- 触发：`trigger` 多条件一般为 **OR**（如 `messages ≥ N` 或 `tokens ≥ M`）；**同一 `thread_id` 才会累加历史**。
- 执行后消息中会出现 **`HumanMessage`**，正文以 **`Here is a summary of the conversation to date:`** 开头，`additional_kwargs` 常含 **`lc_source": "summarization"`**。
- 调试：`create_agent(..., debug=True)`、`stream_mode="updates"`、临时降低 `trigger` 门槛、在 `@after_model` 里看条数骤降。

---

## 11. Token 用量记录

- **单次调用**：看 **`AIMessage.usage_metadata`**（配合 `stream_options.include_usage` 等）。
- **全链路**：**LangSmith** tracing。
- **累计**：`create_agent` **不会**自动把累计写入 state；需 **`@after_model` / callback / 业务层**自行累加（可扩展 `state_schema`）。
- **摘要 + 主模型**：费用 = 主模型 + 摘要模型分别统计。

---

## 12. 官方文档入口（查阅更新）

- LangChain Agents / Middleware：<https://docs.langchain.com/oss/python/langchain/middleware/built-in>  
- LangGraph 持久化等：以当前版本文档为准。

---

## 13. 本目录 demo 索引（可选）

- `01_langgraph_demo.py`：`ReportAgentState` 工作流、`interrupt` + `Command(resume)`、Checkpointer。  
- `02_langgraph_demo.py`：`create_agent`、`SummarizationMiddleware`、装饰器中间件等实验。

---

*文档由学习过程整理，若库版本升级请以官方文档与源码为准。*
