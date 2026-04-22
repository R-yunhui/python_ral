# Hermes Agent 多用户扩展可行性分析报告

**生成日期:** 2026-04-20  
**需求方:** renyh  
**基础框架:** NousResearch/hermes-agent (104K+ Stars)

---

## 需求概述

| 编号 | 需求 | 优先级 |
|------|------|--------|
| R1 | 每个用户作为一个独立的 Bot 与 Hermes Agent 交互 | P0 |
| R2 | 每个 Bot 拥有独立的 MCP 工具、Skills、记忆 | P0 |
| R3 | MCP 工具可动态增删 | P0 |
| R4 | 用户之间物理或逻辑隔离 | P0 |
| R5 | 每个用户只能操作分配给它的目录数据 | P0 |

---

## 1. 需求 R1：多 Bot 独立交互

### Hermes 现有能力

Hermes 提供了 **Profile 隔离机制**，每个 Profile 拥有：
- 独立的配置文件 (`~/.hermes/<profile>/config.json`)
- 独立的记忆文件 (SOUL.md, MEMORY.md, USER.md)
- 独立的会话历史 (SQLite 数据库)
- 独立的 Gateway 实例（可绑定不同平台账号）

### 可行方案

**方案 A：Profile 映射（推荐）**
- 每个用户 → 一个 Hermes Profile
- 通过 Gateway 层路由：根据消息来源（如不同微信/钉钉/飞书账号）自动路由到对应 Profile
- 利用 Hermes 已有的 `--profile <name>` 参数启动隔离实例

**方案 B：多进程部署**
- 每个用户启动独立的 Hermes Agent 进程
- 通过进程管理器（systemd / Docker Compose）统一管理
- 完全隔离，但资源开销较大

### 可行性评估

| 方案 | 可行性 | 优点 | 缺点 |
|------|--------|------|------|
| A: Profile 映射 | **高** | 官方支持、轻量、配置简单 | 共享进程，极端情况下可能互相影响 |
| B: 多进程 | **高** | 完全隔离 | 资源开销大（每个进程 ~500MB 内存） |

**结论：R1 可行，推荐 Profile 映射方案。**

---

## 2. 需求 R2：独立 MCP 工具、Skills、记忆

### 记忆隔离 ✅ 原生支持

Hermes 的 Profile 机制天然支持记忆隔离：
- 每个 Profile 有独立的 MEMORY.md / USER.md / SOUL.md
- 独立的 SQLite 会话数据库
- 独立的 FTS5 全文搜索索引

### Skills 隔离 ✅ 原生支持

- 每个 Profile 有独立的 skills 目录
- Skills 按需加载，不会跨 Profile 共享
- 可通过文件系统权限控制访问

### MCP 工具隔离 ⚠️ 部分支持

- Hermes 的 MCP Server 配置是 Profile 级别的
- 每个 Profile 可以配置不同的 `mcp.servers` 列表
- **但 MCP 工具发现是启动时自动扫描的，运行时动态切换需要额外开发**

### 可行方案

```yaml
# 用户 A 的 Profile 配置 (~/.hermes/user_a/config.json)
{
  "mcp": {
    "servers": {
      "calculator": { "command": "python", "args": ["mcp_calc.py"] },
      "weather": { "command": "node", "args": ["mcp_weather.js"] }
    }
  },
  "skills": {
    "paths": ["~/.hermes/user_a/skills/"]
  }
}

# 用户 B 的 Profile 配置 (~/.hermes/user_b/config.json)
{
  "mcp": {
    "servers": {
      "code_executor": { "command": "python", "args": ["mcp_code.py"] },
      "database": { "command": "python", "args": ["mcp_db.py"] }
    }
  },
  "skills": {
    "paths": ["~/.hermes/user_b/skills/"]
  }
}
```

### 可行性评估

| 组件 | 可行性 | 说明 |
|------|--------|------|
| 记忆隔离 | ✅ 原生支持 | Profile 级别天然隔离 |
| Skills 隔离 | ✅ 原生支持 | 独立目录，按需加载 |
| MCP 工具隔离 | ⚠️ 需配置管理 | 配置层面支持，但需要开发动态管理接口 |

**结论：R2 基本可行，MCP 工具动态管理需少量开发。**

---

## 3. 需求 R3：MCP 工具动态增删

### 方案调整：Tool 级别 vs Server 级别

> **结论：不需要动态增删 MCP Server，只需动态注册/注销已连接 Server 暴露的单个 tools。**

MCP Server 的生命周期：
```
启动进程 → 建立通信通道 → 发现工具列表 → 注册到 Agent → 运行时调用
```

- **增删 Server** = 重新走完整生命周期（进程管理、连接建立、配置重载）
- **增删 Tools** = Server 已连接，只需修改 Agent 侧的工具注册表（字典操作）

类比：增删 Server = 拔插 USB 设备；增删 Tools = 同一个 Hub 上切换端口。

### 可行方案

**方案 A：Tool 级注册/注销（推荐，开发量最低）**

每个 Profile 的 Agent 启动时连接所有配置的 MCP Server，获取全部可用 tools。运行时通过 ToolManager 控制单个 tool 的启用/禁用：

```python
# Tool 级动态管理
class ToolManager:
    def __init__(self, agent):
        self.agent = agent
        self._disabled_tools: set[str] = set()
    
    def list_available_tools(self, profile: str) -> list[dict]:
        """列出当前 Profile 已连接 Server 暴露的所有 tools"""
        agent = get_profile_agent(profile)
        tools = []
        for server_name, server in agent.mcp_servers.items():
            for tool in server.tools:
                status = "disabled" if f"{server_name}:{tool.name}" in self._disabled_tools else "enabled"
                tools.append({"server": server_name, "name": tool.name, "status": status})
        return tools
    
    def enable_tool(self, profile: str, server_name: str, tool_name: str):
        """启用某个 tool"""
        key = f"{server_name}:{tool_name}"
        self._disabled_tools.discard(key)
        tool = self._find_tool(server_name, tool_name)
        self.agent.register_tool(tool)
    
    def disable_tool(self, profile: str, server_name: str, tool_name: str):
        """禁用某个 tool（不断开 Server，只是 Agent 不再调用它）"""
        key = f"{server_name}:{tool_name}"
        self._disabled_tools.add(key)
        self.agent.unregister_tool(key)
    
    def _find_tool(self, server_name: str, tool_name: str):
        server = self.agent.mcp_servers[server_name]
        return next(t for t in server.tools if t.name == tool_name)
```

**方案 B：配置持久化 + 重启恢复**

将每个 tool 的启用状态写入 Profile 配置，Agent 重启时自动恢复：

```json
{
  "mcp": {
    "servers": {
      "calculator": { "command": "python", "args": ["mcp_calc.py"] }
    },
    "tool_overrides": {
      "calculator:add": { "enabled": true },
      "calculator:subtract": { "enabled": false }
    }
  }
}
```

### 可行性评估

| 维度 | 评估 | 说明 |
|------|------|------|
| 开发量 | **低 (~1天)** | 主要是工具注册表的增删操作，无需修改 Agent 核心连接逻辑 |
| 风险 | **低** | Server 连接保持稳定，只是工具级别的开关 |
| 可行性 | **高** | 不依赖 Hermes 内部 API，通过注册表封装即可实现 |

**结论：R3 可行，推荐 Tool 级注册/注销方案。开发量从原评估的 3 天降至 1 天，风险降为低。**

---

## 4. 需求 R4 & R5：用户隔离与数据目录限制

### 关键认知：隔离 vs 安全

- **逻辑隔离**（路径约束）= 防止用户"误操作"到其他目录，但 shell 执行可绕过
- **物理隔离**（Docker/容器）= 内核级隔离，shell 也无法绕过

如果你需要"完全拦住"（用户执行 shell 命令也无法越权），必须走物理隔离。

### 方案对比

| 方案 | 每用户内存 | 能否完全拦住 | 开发量 | 适合场景 |
|------|------------|-------------|--------|----------|
| A: 每用户一容器 | ~500MB | ✅ 是 | 低（配置） | 生产多租户 |
| B: 单进程 + 多 Profile + 路径约束 | ~50MB | ❌ shell 可绕过 | 中（改代码） | 内部可信环境 |

---

### 方案 A：每用户一 Docker 容器

每个用户一个独立容器，运行独立的 Hermes Agent 实例。

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Host                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │  Container A    │  │  Container B    │              │
│  │  Profile: user_a│  │  Profile: user_b│              │
│  │  Workdir: /data │  │  Workdir: /data │              │
│  │  /data → /user_a│  │  /data → /user_b│              │
│  └────────┬────────┘  └────────┬────────┘              │
│           │                    │                        │
│           ▼                    ▼                        │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │  /user_a (rw)   │  │  /user_b (rw)   │              │
│  │  其他目录 (none) │  │  其他目录 (none) │              │
│  └─────────────────┘  └─────────────────┘              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**具体实现：**

1. **容器隔离：** 每个用户一个容器，运行独立 Hermes Agent
2. **文件系统限制：** 容器内只挂载 `/data` → 用户专属目录，使用 `--read-only` + `--tmpfs`
3. **网关层路由：** 统一 Gateway 接收消息，根据用户身份路由到对应 Container
4. **动态启停：** 用户不在线时容器挂起，回收内存

**Docker Compose 模板：**
```yaml
# docker-compose.user.template.yml
services:
  hermes-{{user_id}}:
    image: nousresearch/hermes-agent:latest
    profiles: ["{{user_id}}"]
    volumes:
      - ./data/{{user_id}}:/data
      - ./profiles/{{user_id}}:/root/.hermes
    environment:
      - PROFILE={{user_id}}
      - HOME=/root/.hermes
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: "1G"
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp:size=512M
      - /var/tmp:size=256M
    cap_drop:
      - ALL
    cap_add:
      - DAC_OVERRIDE
```

---

### 方案 B：单进程 + 多 Profile + 路径约束（轻量方案）

一个 Hermes 进程承载所有用户，通过 Profile 切换上下文，在应用层限制文件访问范围。

#### 架构

```
                    单 Hermes 进程 (~500MB 总内存)
                   /        |         |        \
              Profile A  Profile B  Profile C  ...
              (user_a)   (user_b)   (user_c)
              数据根:     数据根:     数据根:
              /data/a    /data/b    /data/c
```

**核心思路：**
- 每个用户分配一个 Hermes Profile（独立的记忆、配置、MCP 工具列表）
- 每个用户绑定一个专属数据目录
- 在 Hermes 的文件操作入口加统一拦截，禁止访问目录外内容

#### Profile 的隔离能力（原生支持，不用改代码）

| 组件 | 隔离方式 | 路径 |
|------|----------|------|
| 配置 | 独立文件 | `~/.hermes/profiles/user_a/config.yaml` |
| 密钥 | 独立文件 | `~/.hermes/profiles/user_a/.env` |
| 记忆 | 独立目录 | `~/.hermes/profiles/user_a/memories/` |
| 会话 | 独立目录 | `~/.hermes/profiles/user_a/sessions/` |
| Skills | 独立目录 | `~/.hermes/profiles/user_a/skills/` |
| MCP 配置 | Profile 级 config | `config.yaml` 中的 `mcp_servers` 字段 |
| 状态库 | 独立 SQLite | `~/.hermes/profiles/user_a/state.db` |

#### 路径约束（需要改代码）

Hermes 访问文件系统的主要入口：

```
文件读写工具 ──→ SafeFileManager.validate_path()
Shell 执行    ──→ 命令白名单 / 路径过滤
Python 执行   ──→ 命令白名单 / 路径过滤
```

**核心代码：**

```python
# 统一的路径安全拦截
class SafeFileManager:
    def __init__(self, allowed_root: Path):
        self.allowed_root = allowed_root.resolve()
    
    def validate_path(self, target: Path) -> Path:
        """确保解析后的路径以 allowed_root 为前缀"""
        resolved = (self.allowed_root / target).resolve()
        if not str(resolved).startswith(str(self.allowed_root)):
            raise PermissionError(f"Access denied: {target}")
        return resolved
    
    def read_file(self, path: str) -> str:
        safe_path = self.validate_path(Path(path))
        return safe_path.read_text()
    
    def write_file(self, path: str, content: str) -> None:
        safe_path = self.validate_path(Path(path))
        safe_path.write_text(content)
    
    def list_directory(self, path: str) -> list[str]:
        safe_path = self.validate_path(Path(path))
        return [f.name for f in safe_path.iterdir()]
```

**Profile 配置示例：**
```yaml
# ~/.hermes/profiles/user_a/config.yaml
filesystem:
  allowed_root: "/data/users/user_a"
  read_only_paths:
    - "/data/users/user_a/templates/"

mcp_servers:
  calculator:
    command: python
    args: ["mcp_calc.py"]
```

#### Shell 执行的处理

这是路径约束方案的最大风险点。两种处理方式：

| 方式 | 做法 | 代价 |
|------|------|------|
| 禁用 Shell | 配置文件关闭 `allow_shell: false` | Agent 无法执行 shell 命令，功能受限 |
| 命令白名单 | 只允许安全命令（ls, cat, grep 等），过滤含 `../` 和绝对路径的命令 | 开发量增加，且仍有遗漏风险 |

#### 可行性评估

| 维度 | 方案 A (Docker) | 方案 B (单进程) |
|------|-----------------|-----------------|
| 安全性 | ✅ 内核级隔离 | ⚠️ 应用层，shell 可绕过 |
| 内存 | ~500MB/用户 | ~500MB 总 + ~50MB/用户 |
| 开发量 | 低（配置为主） | 中（改 Hermes 文件工具） |
| 动态启停 | 支持 | 不需要 |
| 运维 | 需要 Docker 编排 | 简单 |

**结论：**
- 需要"完全拦住"→ 方案 A（Docker 容器）
- 内部可信环境、快速验证 → 方案 B（单进程 + Profile + 路径约束）
- 可以混合演进：先用方案 B 跑起来，安全要求提高后升级到方案 A

**结论：R4 & R5 可行，根据安全要求选择方案。Docker 方案每用户 ~500MB；轻量方案 ~50MB/用户，但 shell 可绕过。**

---

## 5. 总体可行性评估

| 需求 | 可行性 | 开发量 | 风险 |
|------|--------|--------|------|
| R1: 多 Bot 独立交互 | ✅ 高 | 低 (配置为主) | 低 |
| R2: 独立 MCP/Skills/记忆 | ✅ 高 | 低-中 | 低 |
| R3: MCP 工具动态增删 | ✅ 高 | 低 (Tool 级注册) | 低 |
| R4: 用户隔离 | ✅ 高 | 中 (Docker 编排) / 低 (轻量方案) | 低 / 中 |
| R5: 数据目录限制 | ✅ 高 | 低 (Docker volume / 路径约束) | 低 / 中 |

### 总体结论：**可行，低-中等开发量**

---

## 6. 实施建议

### 阶段一：基础多用户架构（1-2 周）

1. 基于 Profile 机制搭建多用户配置管理
2. 实现用户 → Profile 的映射关系
3. 每个 Profile 独立的 MCP/Skills/记忆目录
4. Docker Compose 模板生成

### 阶段二：动态 MCP 工具管理（3-5 天）

1. 开发 Tool 级管理 API（启用/禁用/列表）
2. 封装 Agent 工具注册表的动态操作
3. 配置持久化（tool_overrides 写入 Profile 配置）

### 阶段三：安全加固（1 周）

1. Docker 容器安全配置（权限、资源限制）
2. 文件系统访问控制
3. 用户认证与网关路由

### 阶段四：生产化（1-2 周）

1. 资源监控与自动扩缩容
2. 日志收集与审计
3. 用户管理 UI/API

### 关键技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Hermes 版本升级不兼容 | 高 | 锁定版本，定期同步上游变更 |
| 高并发场景单进程瓶颈 | 中 | 评估后引入多进程/负载均衡 |
| MCP 热插拔与 Agent 状态冲突 | 低 | Tool 级操作不涉及 Server 重连，风险极低 |
| Docker 资源开销大 | 中 | 限制同时在线用户数，或使用轻量级隔离 |

