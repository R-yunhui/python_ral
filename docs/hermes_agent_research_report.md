# Hermes Agent 综合调研报告

**生成日期:** 2026-04-20  
**调研范围:** NousResearch/hermes-agent 开源项目  
**Stars:** 104,282 | **License:** MIT  
**文档地址:** https://hermes-agent.nousresearch.com/docs/  
**主仓库:** https://github.com/NousResearch/hermes-agent

---

## 执行摘要

Hermes Agent 是由 Nous Research 开发的自改进 AI Agent 框架，是目前最流行的开源个人 Agent 之一（10万+ Stars）。其核心卖点包括：内置学习循环、47 个内置工具、18 个消息平台适配器、6 种终端执行后端、可插拔记忆系统、以及基于 DSPy+GEPA 的自我进化能力。

**关键发现：**
- 记忆系统采用文件 + SQLite 方案，**没有**内置向量存储检索
- 自我进化发生在 skill/prompt 层面，**不是**模型权重级别
- 沙箱隔离是可选的，默认是本地直接执行
- MCP 工具集成是原生支持的，且可作为 MCP Server 对外提供服务

---

## 1. 核心架构

### 技术栈

| 维度 | 实现 |
|------|------|
| 语言 | Python 3.11+ |
| 依赖管理 | uv |
| 会话存储 | SQLite + FTS5 全文搜索 |
| 对话循环 | `run_agent.py` 同步编排 (~10,700 行) |
| CLI | 交互式 TUI (~10,000 行) |
| 网关层 | 18 个平台适配器（Telegram, Discord, Slack, 微信, 钉钉, 飞书等） |

### 架构分层

```
入口层 (CLI / Gateway / ACP / Batch Runner / API Server)
    |
    v
AIAgent (run_agent.py) -- 核心对话循环
├── Prompt Builder      -- 系统提示组装
├── Provider Resolution -- 多 LLM 提供商路由
└── Tool Dispatch       -- 47 工具 / 19 工具集
    |                        |
    v                        v
Session Storage          Tool Backends
(SQLite + FTS5)          Terminal (6 后端: local, Docker, SSH,
                          Modal, Daytona, Singularity)
                          Browser, Web, MCP, File, Vision 等
```

### LLM 提供商支持

18+ 提供商：OpenAI, Anthropic, OpenRouter (200+ 模型), NVIDIA NIM, Hugging Face, Kimi/Moonshot, MiniMax 等。

---

## 2. 亮点分析

### 2.1 记忆系统（四层架构）

| 层级 | 文件 | 大小限制 | 说明 |
|------|------|----------|------|
| 人格定义 | SOUL.md | 始终加载 | Agent 默认声音、性格、行为准则 |
| 长期记忆 | MEMORY.md | ~2,200 字符 | Agent 自维护的环境事实、项目约定、工具特性 |
| 用户画像 | USER.md | ~1,375 字符 | 用户偏好、沟通风格、期望 |
| 短期记忆 | SQLite + FTS5 | 无限制 | 全量会话历史，按需全文检索 + LLM 摘要 |

**关键发现：**
- 长期记忆是**文件型**的，Agent 自己写入和维护
- **没有**内置向量存储检索（embedding-based retrieval 不存在）
- 支持 8 种外部记忆提供商插件（Honcho, OpenViking, Mem0, Hindsight 等）
- 社区正在推动升级为结构化图记忆系统（Issue #346）

### 2.2 自我进化机制

**双层进化：**

1. **经验学习循环（内置）：**
   - 完成任务后自动生成 Skill 文件
   - 使用过程中持续改进已有 Skill
   - 更多使用 = 更多 Skill 积累

2. **进化优化（独立仓库 `hermes-agent-self-evolution`）：**
   - 使用 DSPy + GEPA 自动优化 skills、prompts、工具描述
   - 发生在 skill/prompt/config 层面，**不是**模型权重更新

**限制：** 不会学习超出已有 tool/skill 框架的新能力。

### 2.3 沙箱隔离

**防御纵深模型：**

| 后端 | 隔离级别 | 说明 |
|------|----------|------|
| local（默认） | 无 | 直接在宿主机执行 |
| docker | 中 | 容器隔离，严格安全加固 |
| gVisor | 高 | 用户空间内核，减少宿主机攻击面 |
| Modal | 云端 | 无服务器执行 |
| Daytona | 云端沙箱 | 隔离云环境 |
| SSH | 远程 | 远程机器执行 |

**Docker 安全加固：**
- `--cap-drop ALL`（移除所有 Linux 能力）
- `--security-opt no-new-privileges`
- `--pids-limit 256`
- tmpfs 限制（/tmp 512MB, /var/tmp 256MB）

**已知安全问题：**
- Issue #3969: Docker 容器以 root 运行，权限过大
- Issue #4146: 沙箱代码执行可能绕过危险命令审批

### 2.4 MCP 工具和 Skills

**MCP 集成：**
- 内置原生 MCP 客户端，自动发现外部 MCP Server 的工具
- 启动时注册所有发现的 MCP 工具为带 schema 的函数
- 可作为 MCP Server 对外提供服务（Issue #342）
- v0.4.0 (2026-03) 引入 MCP Server 管理

**Skills 系统：**
- 按需加载的知识文档（`SKILL.md` 文件）
- 渐进式披露（3 级：列表 → 查看 → 具体文件）
- Skills Hub 支持 7 个来源：官方、skills.sh、GitHub、ClawHub、LobeHub、Claude marketplace 等
- Agent 可以自己创建、修补、删除 Skill
- 兼容 agentskills.io 标准

**内置工具：** 47 个工具 / 19 工具集
- Web 搜索、浏览器自动化、终端执行、文件编辑
- 记忆管理、代码执行、子代理委派
- Home Assistant 集成、RL 训练等

### 2.5 Profile 隔离

- 支持多个 Profile，每个 Profile 有独立的 config、memory、sessions、gateway
- 这是实现多用户隔离的基础设施

---

## 3. 与主流框架对比

| 维度 | Hermes Agent | LangGraph | AutoGen |
|------|-------------|-----------|---------|
| 定位 | 持久化个人 Agent | 图编排工作流 | 多 Agent 对话 |
| 记忆 | 文件 + SQLite + 外部提供商 | 无内置 | 无内置 |
| 自我改进 | 自主 Skill 创建 + GEPA 进化 | 无 | 无 |
| 平台支持 | CLI + 18 消息平台 | 无（纯库） | 无（纯库） |
| 终端后端 | 6 种 | N/A | N/A |
| MCP | 原生客户端 + 可作为 Server | 需手动集成 | 需手动集成 |
| Stars | 104K+ | 20K+ | 30K+ |

---

## 4. 项目局限性与风险

| 风险 | 说明 |
|------|------|
| 默认无沙箱 | `terminal.backend: local` 是默认配置，生产环境需要手动切换 |
| 记忆容量限制 | MEMORY.md 2,200 字符 + USER.md 1,375 字符，有严格上限 |
| 无内置向量检索 | 大规模知识检索需要外部插件 |
| 单进程架构 | Gateway 单进程运行，高并发场景需评估 |
| 社区活跃度高但 Issue 积压 | 10万 Stars 的项目有较多 open issue，部分安全问题尚未解决 |

---

## 5. 结论

Hermes Agent 是目前功能最全面的开源个人 Agent 框架，特别适合需要持久化、自改进、多平台交互的场景。其 Profile 隔离、MCP 集成、Skills 系统、Docker 沙箱为多用户扩展提供了基础，但需要额外的架构设计来满足生产级的多租户隔离需求。
