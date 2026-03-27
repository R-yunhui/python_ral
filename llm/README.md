# A2A (Agent-to-Agent) 协议学习示例

A2A 是 Google 提出的开放协议，用于不同 AI Agent 之间的标准化通信。

## 示例说明

| 文件 | 说明 | 端口 |
|------|------|------|
| `01_a2a_helloworld.py` | 最简单的 A2A Agent 服务端 | 9999 |
| `02_a2a_client.py` | A2A 客户端，用于测试 Agent | - |
| `03_a2a_langchain_agent.py` | 结合 LangChain 的 A2A Agent | 9998 |
| `04_a2a_multi_agent.py` | 多 Agent 协作示例 | 10001/10002 |

## 安装依赖

```bash
uv add a2a-sdk
```

## 快速开始

### 示例 1: HelloWorld Agent

```bash
# 终端1: 启动服务端
uv run llm/01_a2a_helloworld.py

# 终端2: 运行客户端
uv run llm/02_a2a_client.py
```

### 示例 2: LangChain Agent

```bash
# 启动 LangChain Agent
uv run llm/03_a2a_langchain_agent.py

# 使用客户端测试
uv run llm/02_a2a_client.py  # 修改 BASE_URL 为 http://localhost:9998
```

### 示例 3: 多 Agent 协作

```bash
# 终端1: 启动研究员 Agent
uv run llm/04_a2a_multi_agent.py --agent researcher

# 终端2: 启动写作者 Agent
uv run llm/04_a2a_multi_agent.py --agent writer

# 终端3: 运行协调器
uv run llm/04_a2a_multi_agent.py --orchestrator
```

## A2A 核心概念

```
┌─────────────────────────────────────────────────────────────┐
│                     A2A Agent 架构                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            A2AStarletteApplication                   │   │
│  │            (HTTP 服务器)                              │   │
│  └────────────────────────┬────────────────────────────┘   │
│                           │                                │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            DefaultRequestHandler                      │   │
│  │            (处理 A2A 协议请求)                        │   │
│  └────────────────────────┬────────────────────────────┘   │
│                           │                                │
│          ┌────────────────┼────────────────┐              │
│          ▼                ▼                ▼              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │AgentExecutor│  │  TaskStore  │  │  AgentCard  │       │
│  │ (执行逻辑)  │  │ (任务存储)  │  │ (能力描述)  │       │
│  └──────┬──────┘  └─────────────┘  └─────────────┘       │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │            Your Agent Logic                          │  │
│  │            (LLM / Tools / Memory)                    │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

| 概念 | 说明 |
|------|------|
| **AgentCard** | Agent 的"名片"，描述能力、URL、技能等 |
| **AgentSkill** | 具体技能定义（id、名称、描述、示例） |
| **AgentExecutor** | 执行接口，实现 `execute` 和 `cancel` 方法 |
| **TaskStore** | 任务状态存储（内存/数据库） |
| **EventQueue** | 事件队列，用于流式返回结果 |

## 与其他框架对比

| 特性 | A2A | LangGraph | DeepAgent |
|------|-----|-----------|-----------|
| 通信方式 | JSON-RPC over HTTP | State 共享 | task 工具 |
| 跨框架支持 | ✅ | ❌ | ❌ |
| 服务发现 | Agent Card | 硬编码 | 硬编码 |
| 标准化 | ✅ 开放标准 | ❌ 框架私有 | ❌ 框架私有 |
| 内部暴露 | ✅ 完全隔离 | 共享 State | 隔离 |