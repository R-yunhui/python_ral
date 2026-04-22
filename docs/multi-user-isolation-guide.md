# Hermes Agent 多用户隔离扩展指南

> 本文档总结了如何在**不修改 Hermes 源码**的前提下，利用现有机制实现多用户隔离。

---

## 一、核心发现：Profile 机制

Hermes 已有一套完整的 **Profile 隔离机制**（`hermes_cli/profiles.py`），每个 Profile 是一个完全独立的 `HERMES_HOME` 目录。

### 1.1 Profile 目录结构

```
~/.hermes/                          ← default profile
├── config.yaml                     ← 配置
├── .env                            ← API Keys / Bot Tokens
├── SOUL.md                         ← 人格 / 系统提示
├── state.db                        ← 会话数据库（SQLite）
├── memories/                       ← 记忆
├── skills/                         ← 技能
├── cron/                           ← 定时任务
├── home/                           ← 子进程 HOME（git/ssh/gh 凭据隔离）
├── sessions/ | logs/ | plans/
└── profiles/
    ├── alice/                      ← 用户 Alice 的 profile
    │   ├── config.yaml / .env / SOUL.md / state.db
    │   ├── memories/ / skills/ / cron/ / home/
    │   └── ...
    └── bob/                        ← 用户 Bob 的 profile
        └── ...
```

### 1.2 工作原理

代码库中 **119+ 个文件**都通过 `get_hermes_home()` 解析路径：

```python
# hermes_constants.py
def get_hermes_home() -> Path:
    val = os.environ.get("HERMES_HOME", "").strip()
    return Path(val) if val else Path.home() / ".hermes"
```

当 wrapper 脚本设置 `HERMES_HOME=~/.hermes/profiles/alice` 后，config、sessions、memory、skills、cron、logs **全部自动隔离到该目录**。

### 1.3 Profile 隔离能力一览

| 资源 | 隔离 | 说明 |
|------|:----:|------|
| config.yaml | ✅ | 每 profile 独立配置 |
| .env（API Keys） | ✅ | 每 profile 独立密钥 |
| SOUL.md（人格） | ✅ | 每 profile 独立人格 |
| state.db（会话） | ✅ | 每 profile 独立数据库 |
| memories/ | ✅ | 每 profile 独立记忆 |
| skills/ | ✅ | 每 profile 独立技能 |
| cron/ | ✅ | 每 profile 独立定时任务 |
| home/（subprocess HOME） | ✅ | git/ssh/gh 凭据隔离 |
| Gateway 进程 | ✅ | 每 profile 独立进程 |
| Bot Token | ✅ | Token 锁机制防冲突 |
| Terminal / 文件系统 | ❌ | 共享宿主机文件系统 |
| Token 配额 | ❌ | 无使用量限制 |

---

## 二、多用户隔离方案

### 核心思路：1 User = 1 Profile

**Profile = 用户（长期存在），Session = 对话（通过 header 区分）。**

- 用户注册时创建 Profile，注销时删除
- 每次对话通过 `X-Hermes-Session-Id` header 区分，不需要创建/删除任何东西

### 方案对比

| 维度 | A: Docker 容器（推荐） | B: Profile + Proxy | C: Session Header |
|------|:---:|:---:|:---:|
| 源码改动 | 无 | 无 | 无 |
| Session 隔离 | ✅ | ✅ | ✅ |
| Memory 隔离 | ✅ | ✅ | ❌ |
| Skills 隔离 | ✅ | ✅ | ❌ |
| Terminal 隔离 | ✅ 容器级 | ⚠️ 需配置 cwd | ❌ |
| 资源开销 | 高 | 中 | 低 |
| 适用场景 | 生产环境 | 小团队 | 可信内部团队 |
| 实施时间 | 1-2 天 | 半天 | 1 小时 |

---

## 三、方案 A：Docker 容器（推荐）

每个用户一个独立 Docker 容器，通过 Nginx 按 API Key 路由。

### 3.1 架构

```
用户请求 → Nginx（按 API Key 路由）→ Docker 容器（每用户独立）→ 独立 Volume
```

### 3.2 docker-compose.yml

```yaml
version: '3.8'

x-hermes-base: &hermes-base
  image: hermes-agent:latest
  build: .
  restart: unless-stopped
  command: ["gateway", "start"]

services:
  proxy:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - hermes-alice
      - hermes-bob

  hermes-alice:
    <<: *hermes-base
    environment:
      HERMES_HOME: /opt/data
      API_SERVER_KEY: sk-alice-secret-key
      API_SERVER_HOST: "0.0.0.0"
      API_SERVER_PORT: "8642"
      OPENROUTER_API_KEY: ${SHARED_LLM_KEY}
    volumes:
      - alice-data:/opt/data

  hermes-bob:
    <<: *hermes-base
    environment:
      HERMES_HOME: /opt/data
      API_SERVER_KEY: sk-bob-secret-key
      API_SERVER_HOST: "0.0.0.0"
      API_SERVER_PORT: "8642"
      OPENROUTER_API_KEY: ${SHARED_LLM_KEY}
    volumes:
      - bob-data:/opt/data

volumes:
  alice-data:
  bob-data:
```

### 3.3 Nginx 路由配置

```nginx
map $http_authorization $target_backend {
    default           "";
    "Bearer sk-alice-secret-key"  "hermes-alice:8642";
    "Bearer sk-bob-secret-key"    "hermes-bob:8642";
}

server {
    listen 80;

    location /v1/ {
        if ($target_backend = "") {
            return 401 '{"error": {"message": "Invalid API key"}}';
        }
        proxy_pass http://$target_backend;
        proxy_set_header Host $host;
        proxy_buffering off;
        chunked_transfer_encoding on;
    }
}
```

---

## 四、方案 B：Profile + Proxy（轻量）

单机运行多个 Profile 进程，前面加一层 Proxy 路由。

### 4.1 创建 Profile 的两种方式

**方式 1：CLI 命令（subprocess 调用）**

```bash
# 创建 profile（继承当前配置）
hermes profile create alice --clone --no-alias

# 配置 API Server
hermes -p alice config set platforms.api_server.enabled true
hermes -p alice config set platforms.api_server.port 8001
hermes -p alice config set platforms.api_server.key sk-alice-xxx

# 启动 gateway
hermes -p alice gateway start
```

**方式 2：Python API（in-process）**

```python
from hermes_cli.profiles import create_profile, get_profile_dir

profile_dir = create_profile(
    name="alice",
    clone_config=True,     # 继承管理员的 config.yaml, .env, SOUL.md
    no_alias=True,         # 服务端模式不需要 shell wrapper
)
# → 返回: ~/.hermes/profiles/alice
```

### 4.2 Profile CLI 参考

| CLI 命令 | Python API | 说明 |
|---------|------------|------|
| `hermes profile create <name> --clone` | `create_profile(name, clone_config=True)` | 创建 |
| `hermes profile delete <name> --yes` | `delete_profile(name, yes=True)` | 删除 |
| `hermes profile list` | `list_profiles()` → `List[ProfileInfo]` | 列出 |
| `hermes -p <name> gateway start` | subprocess + HERMES_HOME env | 启动 |
| `hermes profile show <name>` | `get_profile_dir()` + `_read_config_model()` | 查看 |

### 4.3 Profile 生命周期

```
用户注册 → create_profile("user-alice", clone_config=True)
         → 配置 API Server 端口和 Key
         → gateway start
         → （长期运行，跨对话保留 memory/skills）

每次对话 → POST /v1/chat/completions
           Header: X-Hermes-Session-Id: conv-20260420-001
         → 换个 session ID 就是新对话

用户注销 → gateway stop
         → delete_profile("user-alice", yes=True)
```

> ⚠️ **不要**每次对话创建/删除 Profile。Profile 应该长期保留，这样 Agent 的 memory 和 skills 才能跨对话积累。

---

## 五、MCP Server 动态管理

### 5.1 MCP CLI 命令

```bash
hermes mcp add <name> --url <url>                          # 添加 HTTP 类型
hermes mcp add <name> --command <cmd> --args <args>        # 添加 stdio 类型
hermes mcp remove <name>                                    # 删除
hermes mcp list                                             # 列出所有
hermes mcp test <name>                                      # 测试连接
hermes mcp configure <name>                                 # 交互式选择工具
hermes mcp login <name>                                     # 重新认证 OAuth
```

### 5.2 程序化管理（直接写 config.yaml）

CLI 有交互式提示，不适合程序化调用。推荐**直接操作 config.yaml**：

```python
import yaml
from pathlib import Path

def add_mcp_server(profile_home: Path, name: str, server_config: dict):
    config_path = profile_home / "config.yaml"
    config = yaml.safe_load(config_path.read_text()) if config_path.exists() else {}
    config.setdefault("mcp_servers", {})[name] = server_config
    config_path.write_text(yaml.dump(config, default_flow_style=False))

def remove_mcp_server(profile_home: Path, name: str):
    config_path = profile_home / "config.yaml"
    config = yaml.safe_load(config_path.read_text()) or {}
    servers = config.get("mcp_servers", {})
    if name in servers:
        del servers[name]
        if not servers:
            config.pop("mcp_servers", None)
        config_path.write_text(yaml.dump(config, default_flow_style=False))
```

### 5.3 config.yaml 中的 MCP 配置格式

```yaml
mcp_servers:
  # HTTP/SSE 类型
  my-api:
    url: "https://mcp.example.com/sse"
    enabled: true
    headers:
      Authorization: "Bearer ${MCP_MYAPI_API_KEY}"

  # stdio 类型
  github:
    command: "npx"
    args: ["@modelcontextprotocol/server-github"]
    enabled: true
    env:
      GITHUB_TOKEN: "ghp_xxx"

  # 只启用部分工具
  database:
    url: "https://db-mcp.example.com/sse"
    enabled: true
    tools:
      include: ["query", "list_tables"]       # 白名单
      # 或 exclude: ["drop_table", "truncate"]  # 黑名单
```

> 修改 config.yaml 后需要**新的 session** 才会生效。

### 5.4 会话期间工具动态变化

**Hermes 已内置支持 MCP 工具热更新**（`mcp_tool.py` L816-895）。

工作流程：

```
MCP Server 工具数量变化
  → Server 发送 notifications/tools/list_changed（MCP 协议标准通知）
    → Hermes 捕获通知（_make_message_handler）
      → 调用 session.list_tools() 重新获取工具列表
        → 注销旧工具 registry.deregister()
          → 注册新工具 _register_server_tools()
            → 日志输出 "tools changed dynamically — added: X; removed: Y"
```

**前提条件**：

- MCP Server 需要发送 `notifications/tools/list_changed` 通知（MCP 协议标准）
- MCP SDK 版本需要支持 `message_handler`（较新版本）

**如果 MCP Server 不发通知**：工具变化只能在新 session 时重新发现（连接建立时调用一次 `_discover_tools()`）。

---

## 六、API 调用示例

### 6.1 发送对话请求

Hermes API Server 兼容 OpenAI 格式：

```python
import requests

# 同一用户的不同对话，通过 X-Hermes-Session-Id 区分
response = requests.post(
    "http://localhost:8001/v1/chat/completions",    # 用户 Alice 的端口
    headers={
        "Authorization": "Bearer sk-alice-xxx",
        "X-Hermes-Session-Id": "conv-001",          # 对话 ID
    },
    json={
        "model": "hermes-agent",
        "messages": [{"role": "user", "content": "你好"}],
        "stream": False,
    },
)
print(response.json())
```

### 6.2 支持的 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/chat/completions` | POST | OpenAI Chat Completions 格式 |
| `/v1/responses` | POST | OpenAI Responses API 格式（有状态） |
| `/v1/responses/{id}` | GET/DELETE | 获取/删除已存储的 response |
| `/v1/models` | GET | 列出可用模型 |
| `/v1/runs` | POST | 启动异步 run |
| `/v1/runs/{id}/events` | GET | SSE 事件流 |
| `/health` | GET | 健康检查 |

---

## 七、完整编排示例

以下是一个完整的多用户编排脚本：

```python
#!/usr/bin/env python3
"""multi_user_orchestrator.py — Hermes 多用户编排"""

import json
import secrets
import subprocess
import yaml
from pathlib import Path

class HermesMultiUserManager:
    def __init__(self):
        self.users_file = Path("users.json")
        self.users = json.loads(self.users_file.read_text()) if self.users_file.exists() else {}
        self.base_port = 8001

    def _save(self):
        self.users_file.write_text(json.dumps(self.users, indent=2, ensure_ascii=False))

    def add_user(self, username: str, mcp_servers: dict = None) -> dict:
        """注册新用户"""
        if username in self.users:
            return self.users[username]

        port = self.base_port + len(self.users)
        api_key = f"sk-{username}-{secrets.token_hex(16)}"
        profile_name = f"user-{username}"

        # 1. 创建 Profile
        subprocess.run(
            ["hermes", "profile", "create", profile_name, "--clone", "--no-alias"],
            check=True,
        )

        # 2. 获取 Profile 目录并配置
        profile_home = Path.home() / ".hermes" / "profiles" / profile_name
        config_path = profile_home / "config.yaml"
        config = yaml.safe_load(config_path.read_text()) if config_path.exists() else {}

        # 配置 API Server
        config.setdefault("platforms", {}).setdefault("api_server", {}).update({
            "enabled": True,
            "port": port,
            "key": api_key,
            "host": "127.0.0.1",
        })

        # 配置 MCP Servers（可选）
        if mcp_servers:
            config["mcp_servers"] = mcp_servers

        config_path.write_text(yaml.dump(config, default_flow_style=False))

        # 3. 启动 Gateway
        subprocess.Popen(["hermes", "-p", profile_name, "gateway", "start"])

        # 4. 记录
        self.users[username] = {
            "profile": profile_name,
            "port": port,
            "api_key": api_key,
        }
        self._save()

        return self.users[username]

    def remove_user(self, username: str):
        """注销用户"""
        if username not in self.users:
            return
        info = self.users[username]
        subprocess.run(["hermes", "-p", info["profile"], "gateway", "stop"], check=False)
        subprocess.run(["hermes", "profile", "delete", info["profile"], "--yes"], check=True)
        del self.users[username]
        self._save()

    def add_mcp_to_user(self, username: str, name: str, server_config: dict):
        """为用户动态添加 MCP Server"""
        info = self.users[username]
        profile_home = Path.home() / ".hermes" / "profiles" / info["profile"]
        config_path = profile_home / "config.yaml"
        config = yaml.safe_load(config_path.read_text()) or {}
        config.setdefault("mcp_servers", {})[name] = server_config
        config_path.write_text(yaml.dump(config, default_flow_style=False))

    def remove_mcp_from_user(self, username: str, name: str):
        """为用户删除 MCP Server"""
        info = self.users[username]
        profile_home = Path.home() / ".hermes" / "profiles" / info["profile"]
        config_path = profile_home / "config.yaml"
        config = yaml.safe_load(config_path.read_text()) or {}
        servers = config.get("mcp_servers", {})
        if name in servers:
            del servers[name]
            if not servers:
                config.pop("mcp_servers", None)
            config_path.write_text(yaml.dump(config, default_flow_style=False))

    def get_endpoint(self, username: str) -> str:
        """获取用户的 API 地址"""
        info = self.users[username]
        return f"http://127.0.0.1:{info['port']}/v1"


# ========== 使用示例 ==========
if __name__ == "__main__":
    mgr = HermesMultiUserManager()

    # 注册用户
    alice = mgr.add_user("alice")
    print(f"Alice API: {mgr.get_endpoint('alice')}")
    print(f"Alice Key: {alice['api_key']}")

    # 为 Alice 添加 MCP 工具
    mgr.add_mcp_to_user("alice", "github", {
        "command": "npx",
        "args": ["@modelcontextprotocol/server-github"],
        "enabled": True,
        "env": {"GITHUB_TOKEN": "ghp_xxx"},
    })

    # 对话（用标准 OpenAI 客户端或 requests）
    import requests
    resp = requests.post(
        f"{mgr.get_endpoint('alice')}/chat/completions",
        headers={
            "Authorization": f"Bearer {alice['api_key']}",
            "X-Hermes-Session-Id": "conv-001",
        },
        json={
            "model": "hermes-agent",
            "messages": [{"role": "user", "content": "Hello!"}],
        },
    )
    print(resp.json())
```

---

## 八、注意事项

| 事项 | 说明 |
|------|------|
| **Profile ≠ 对话** | Profile 是用户级别（长期存在），对话通过 Session ID 区分 |
| **Memory 跨对话积累** | Profile 长期保留才能让 Agent 记住用户偏好 |
| **MCP 配置变更生效时机** | config.yaml 修改后需要新 session 才生效 |
| **MCP 工具热更新** | 如 Server 发送 `tools/list_changed` 通知，会话内实时生效 |
| **Terminal 无沙箱** | Profile 不限制文件系统访问，需 Docker 或 `terminal.cwd` 限制 |
| **资源开销** | 每用户一个 gateway 进程，100 用户 ≈ 100 进程 |
| **`get_hermes_home()` 是进程全局的** | 并发场景需子进程方案，不能在同一进程内切换 |
