# Claude Code 完整命令参考手册

> 版本：2026-04-22 | 适用：Claude Code CLI v2.1+

---

## 目录

1. [CLI 启动命令](#一cli-启动命令)
2. [CLI 启动参数](#二cli-启动参数flags)
3. [Slash 命令（会话内命令）](#三slash-命令会话内命令)
4. [键盘快捷键](#四键盘快捷键)
5. [配置文件与权限模式](#五配置文件与权限模式)
6. [扩展系统](#六扩展系统)

---

## 一、CLI 启动命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `claude` | 启动交互式会话 | `claude` |
| `claude "问题"` | 启动会话并发送初始提示 | `claude "解释这个项目"` |
| `claude -p "问题"` | 非交互模式，打印结果后退出 | `claude -p "解释这个函数"` |
| `cat file \| claude -p "问题"` | 管道输入 | `cat logs.txt \| claude -p "分析日志"` |
| `claude -c` | 继续当前目录最近的对话 | `claude -c` |
| `claude -r "<会话名>" "问题"` | 按 ID 或名称恢复会话 | `claude -r "auth-refactor" "完成这个PR"` |
| `claude update` | 更新到最新版本 | `claude update` |
| `claude auth login` | 登录 Anthropic 账户 | `claude auth login --console` |
| `claude auth logout` | 登出 | `claude auth logout` |
| `claude auth status` | 显示认证状态 | `claude auth status` |
| `claude agents` | 列出所有配置的子代理 | `claude agents` |
| `claude mcp` | 配置 MCP 服务器 | `claude mcp add server-name` |
| `claude plugin` | 管理插件 | `claude plugin install code-review@claude-plugins-official` |
| `claude setup-token` | 生成 CI/脚本用的长效 OAuth token | `claude setup-token` |

---

## 二、CLI 启动参数（Flags）

### 常用参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--print`, `-p` | 非交互打印模式（一次性问答） | `claude -p "解释这个文件"` |
| `--continue`, `-c` | 加载最近对话继续 | `claude -c` |
| `--resume`, `-r` | 恢复特定会话 | `claude -r "my-session" "继续"` |
| `--model` | 设置当前会话模型 | `claude --model claude-sonnet-4-6` |
| `--effort` | 设置努力级别：low/medium/high/xhigh/max | `claude --effort high` |
| `--worktree`, `-w` | 在隔离的 git worktree 中启动 | `claude -w feature-auth` |
| `--name`, `-n` | 设置会话显示名称 | `claude -n "my-feature"` |
| `--add-dir` | 添加额外工作目录供 Claude 读写 | `claude --add-dir ../apps ../lib` |
| `--allowedTools` | 免权限确认直接执行的工具 | `--allowedTools "Bash(git log *)" "Read"` |
| `--permission-mode` | 起始权限模式 | `claude --permission-mode plan` |
| `--dangerously-skip-permissions` | 跳过权限确认（慎用） | `claude --dangerously-skip-permissions` |
| `--bare` | 极简模式，跳过 hooks/skills/plugins/MCP 发现 | `claude --bare -p "query"` |
| `--chrome` | 启用 Chrome 浏览器集成 | `claude --chrome` |
| `--remote` | 创建 web 会话 | `claude --remote "Fix the bug"` |
| `--remote-control`, `--rc` | 启动带远程控制的会话 | `claude --rc "My Project"` |
| `--agent` | 指定当前会话使用的代理 | `claude --agent my-custom-agent` |
| `--version`, `-v` | 显示版本号 | `claude -v` |

### 进阶参数

| 参数 | 说明 | 场景 |
|------|------|------|
| `--max-budget-usd` | 最大花费上限（仅 print 模式） | 控制 API 消费 |
| `--max-turns` | 限制 agentic 轮数（仅 print 模式） | 防止无限循环 |
| `--output-format` | 输出格式：text/json/stream-json | 程序化调用 |
| `--system-prompt` | 替换整个系统提示 | 自定义角色 |
| `--system-prompt-file` | 从文件加载系统提示 | 复杂角色设定 |
| `--append-system-prompt` | 追加文本到默认系统提示 | 额外规则 |
| `--mcp-config` | 从 JSON 文件加载 MCP 服务器 | 批量 MCP 配置 |
| `--strict-mcp-config` | 仅使用 --mcp-config 指定的 MCP 服务器 | 严格 MCP 隔离 |
| `--debug` | 启用调试模式 | 排查问题 |
| `--debug-file <path>` | 指定调试日志输出文件 | 日志持久化 |
| `--fallback-model` | 模型过载时自动回退 | 高可用 |
| `--no-session-persistence` | 禁用会话持久化 | 无痕模式 |
| `--teleport` | 将 web 会话拉到本地终端 | web -> 本地切换 |

---

## 三、Slash 命令（会话内命令）

### 3.1 核心操作

| 命令 | 说明 | 适用场景 |
|------|------|----------|
| `/clear` | 清空上下文开始新对话（别名 `/reset`、`/new`） | 开始全新任务，不需要保留之前上下文 |
| `/compact [指令]` | 压缩上下文，总结当前对话 | 上下文快满了但需要继续同一对话 |
| `/exit` | 退出 CLI（别名 `/quit`） | 结束会话 |
| `/help` | 显示所有可用命令和帮助信息 | 查看当前可用的命令列表 |
| `/config` | 打开设置界面（别名 `/settings`） | 调整主题、模型、输出风格等偏好 |
| `/status` | 打开状态页（版本、模型、账户、连接） | 快速检查状态，不等当前响应结束 |
| `/statusline` | 配置终端状态栏 | 自定义终端状态栏显示内容 |

### 3.2 会话管理

| 命令 | 说明 | 适用场景 |
|------|------|----------|
| `/resume [会话]` | 按 ID 或名称恢复对话（别名 `/continue`） | 回到之前的工作 |
| `/rename [名称]` | 重命名当前会话，不传名称则自动生成 | 给会话起有意义的名字方便查找 |
| `/branch [名称]` | 在当前对话的此处分叉（别名 `/fork`） | 尝试不同方案但想保留原始对话 |
| `/rewind` | 回退到之前的状态（别名 `/checkpoint`、`/undo`） | 撤销 Claude 的操作，恢复到之前版本 |
| `/recap` | 生成当前会话一行总结 | 离开后回来快速了解刚才做了什么 |
| `/export [文件名]` | 导出当前对话为纯文本 | 保存对话记录到文件 |
| `/copy [N]` | 复制最后一条助手回复（传 N 复制第 N 条） | 快速复制代码或回复内容 |

### 3.3 模型与性能

| 命令 | 说明 | 适用场景 |
|------|------|----------|
| `/model [模型]` | 切换 AI 模型 | 在 Sonnet/Opus 等模型间切换 |
| `/effort [级别\|auto]` | 设置努力级别：low/medium/high/xhigh/max/auto | 需要更深思考或更快响应时调整 |
| `/fast [on\|off]` | 切换快速模式 | 需要快速简单回答时开启 |
| `/context` | 可视化当前上下文使用情况，显示优化建议 | 上下文不足时排查原因 |
| `/cost` | 显示 token 使用统计 | 查看当前会话花费 |
| `/usage` | 显示计划用量限制和速率限制状态 | 检查是否接近用量上限 |

### 3.4 代码与 Git 操作

| 命令 | 说明 | 适用场景 |
|------|------|----------|
| `/diff` | 打开交互式差异查看器，显示未提交变更和每轮差异 | 查看 Claude 改了什么 |
| `/review [PR]` | 在本地审查 Pull Request | Code Review |
| `/ultrareview [PR]` | 在云端沙箱中进行多代理深度代码审查 | 需要更深入的代码审查 |
| `/security-review` | 分析当前分支待提交变更的安全漏洞 | 提交前安全检查 |
| `/batch <指令>` | **[Skill]** 并行研究并大规模变更 | 大规模代码迁移/重构 |
| `/simplify [关注点]` | **[Skill]** 并行审查近期修改文件的代码质量 | 代码实现后的优化检查 |
| `/autofix-pr [提示]` | 启动 web 会话监控当前分支 PR，自动修复 | 自动化 PR 修复 |

### 3.5 MCP 与插件

| 命令 | 说明 | 适用场景 |
|------|------|----------|
| `/mcp` | 管理 MCP 服务器连接和 OAuth 认证 | 配置外部服务集成 |
| `/plugin` | 管理 Claude Code 插件 | 安装/卸载/管理插件 |
| `/reload-plugins` | 重新加载所有活动插件，无需重启 | 插件配置变更后生效 |
| `/hooks` | 查看 hook 配置 | 检查自动化钩子配置 |
| `/agents` | 管理子代理配置 | 查看和管理自定义子代理 |

### 3.6 项目与设置

| 命令 | 说明 | 适用场景 |
|------|------|----------|
| `/init` | 初始化项目，生成 CLAUDE.md 指南 | 新项目首次配置 |
| `/memory` | 编辑 CLAUDE.md 记忆文件，启用/禁用自动记忆 | 管理项目指令和记忆 |
| `/skills` | 列出可用 skills，按 `t` 可按 token 数排序 | 查看当前可用技能 |
| `/permissions` | 管理工具的 allow/ask/deny 规则（别名 `/allowed-tools`） | 配置工具权限 |
| `/add-dir <路径>` | 添加工作目录供当前会话访问 | 需要访问当前目录外的代码 |
| `/keybindings` | 打开或创建按键绑定配置文件 | 自定义快捷键 |
| `/theme` | 切换颜色主题 | 切换外观 |
| `/tui [default\|fullscreen]` | 设置终端 UI 渲染器 | 切换全屏/默认渲染模式 |

### 3.7 自动化与调度

| 命令 | 说明 | 适用场景 |
|------|------|----------|
| `/schedule [描述]` | 创建/更新/列出/运行定时任务（别名 `/routines`） | 设置定时任务如每日 PR 审查 |
| `/loop [间隔] [提示]` | **[Skill]** 在会话保持打开期间重复运行提示 | 轮询检查如部署状态 |

### 3.8 其他实用命令

| 命令 | 说明 | 适用场景 |
|------|------|----------|
| `/btw <问题>` | 快速侧问，不加入对话历史 | 快速查询不干扰主上下文 |
| `/doctor` | 诊断并验证安装和设置，按 `f` 可自动修复 | 环境排查 |
| `/debug [描述]` | **[Skill]** 启用调试日志并诊断问题 | 排查 Claude Code 故障 |
| `/insights` | 生成会话分析报告 | 了解使用模式 |
| `/stats` | 可视化每日用量、会话历史、连续使用天数 | 使用统计总览 |
| `/feedback [报告]` | 提交反馈（别名 `/bug`） | 报告问题或建议 |
| `/desktop` | 在桌面 App 中继续当前会话（别名 `/app`） | 转到桌面端查看 |
| `/remote-control` | 使会话可从 claude.ai 远程控制（别名 `/rc`） | 远程操控终端会话 |
| `/teleport` | 将 web 会话拉到本地（别名 `/tp`） | web -> 本地切换 |
| `/focus` | 切换聚焦视图（仅全屏渲染模式） | 简化界面只看关键信息 |
| `/powerup` | 通过交互式课程发现 Claude Code 功能 | 学习新功能 |
| `/color [颜色\|default]` | 设置提示栏颜色 | 个性化区分多个会话 |
| `/chrome` | 配置 Chrome 浏览器集成设置 | 配置浏览器自动化 |
| `/tasks` | 列出和管理后台任务（别名 `/bashes`） | 查看后台运行中的任务 |
| `/voice` | 切换语音输入 | 语音输入提示 |

### 3.9 认证与账户

| 命令 | 说明 | 适用场景 |
|------|------|----------|
| `/login` | 登录 Anthropic 账户 | 认证登录 |
| `/logout` | 登出 | 切换账户 |
| `/upgrade` | 打开升级页面 | 升级计划 |
| `/passes` | 分享一周免费 Claude Code | 推荐给朋友 |
| `/extra-usage` | 配置额外用量以在速率限制命中时继续工作 | 速率限制处理 |
| `/privacy-settings` | 查看和更新隐私设置 | 隐私管理 |

### 3.10 平台与集成

| 命令 | 说明 | 适用场景 |
|------|------|----------|
| `/ide` | 管理 IDE 集成并显示状态 | 检查 VS Code/JetBrains 连接 |
| `/terminal-setup` | 配置终端快捷键 | VS Code/Cursor 等终端配置 |
| `/mobile` | 显示二维码下载 Claude 手机 App | 移动端安装 |
| `/install-github-app` | 为仓库设置 Claude GitHub Actions | CI/CD 集成 |
| `/install-slack-app` | 安装 Claude Slack App | Slack 集成 |

### 3.11 供应商配置

| 命令 | 说明 | 适用场景 |
|------|------|----------|
| `/setup-bedrock` | 配置 Amazon Bedrock 认证 | AWS Bedrock 接入（需 `CLAUDE_CODE_USE_BEDROCK=1`） |
| `/setup-vertex` | 配置 Google Vertex AI 认证 | GCP Vertex AI 接入（需 `CLAUDE_CODE_USE_VERTEX=1`） |

---

## 四、键盘快捷键

### 4.1 通用控制

| 快捷键 | 说明 |
|--------|------|
| `Ctrl+C` | 取消当前输入或生成 |
| `Ctrl+D` | 退出 Claude Code 会话 |
| `Ctrl+G` 或 `Ctrl+X Ctrl+E` | 在默认文本编辑器中编辑提示 |
| `Ctrl+L` | 清空提示输入并重绘屏幕 |
| `Ctrl+O` | 切换转录查看器（显示详细工具使用和执行） |
| `Ctrl+R` | 反向搜索命令历史 |
| `Ctrl+V` | 从剪贴板粘贴图片 |
| `Ctrl+B` | 后台运行任务 |
| `Ctrl+T` | 切换任务列表显示 |
| `Shift+Tab` 或 `Alt+M` | 循环切换权限模式 |
| `Option+P`(macOS) / `Alt+P`(Windows) | 切换模型 |
| `Option+T`(macOS) / `Alt+T`(Windows) | 切换扩展思考模式 |
| `Option+O`(macOS) / `Alt+O`(Windows) | 切换快速模式 |
| `Esc` + `Esc` | 回退到之前的对话点 |
| `Ctrl+X Ctrl+K` | 终止所有后台代理 |

### 4.2 文本编辑

| 快捷键 | 说明 |
|--------|------|
| `Ctrl+A` | 光标移到行首 |
| `Ctrl+E` | 光标移到行尾 |
| `Ctrl+K` | 删除到行尾 |
| `Ctrl+U` | 从光标删到行首 |
| `Ctrl+W` | 删除前一个词 |
| `Ctrl+Y` | 粘贴已删除文本 |
| `Alt+B` | 光标后移一个词 |
| `Alt+F` | 光标前移一个词 |

### 4.3 快捷输入模式

| 快捷键 | 说明 |
|--------|------|
| `/` 开头 | 触发命令或 skill |
| `!` 开头 | Bash 模式：直接运行命令 |
| `@` | 触发文件路径自动补全 |
| `\` + `Enter` | 多行输入转义 |
| `Ctrl+J` | 多行输入 |

---

## 五、配置文件与权限模式

### 5.1 配置文件层级

| 文件 | 作用域 | 说明 |
|------|--------|------|
| `~/.claude/settings.json` | 用户级 | 全局配置（模型、权限、主题等） |
| `~/.claude/settings.local.json` | 用户本地 | 不提交到 git 的用户配置 |
| `.claude/settings.json` | 项目级 | 随项目提交 |
| `.claude/settings.local.json` | 项目本地 | 不提交到 git 的项目配置 |

### 5.2 权限模式（Permission Modes）

通过 `Shift+Tab` 循环切换，或用 `--permission-mode` 启动参数指定。

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| `default` | 默认模式，每个工具调用需要确认 | 日常使用 |
| `acceptEdits` | 文件读写免确认，Bash 仍需确认 | 信任 Claude 改代码 |
| `plan` | 只读模式，Claude 只能读取不能修改 | 代码审查/调研 |
| `auto` | Claude 自行判断是否需要确认 | 熟练使用者 |
| `dontAsk` | 只问需要拒绝权限的操作 | 高频操作场景 |
| `bypassPermissions` | 完全跳过权限检查 | CI/自动化脚本 |

---

## 六、扩展系统

| 特性 | 作用 | 何时使用 |
|------|------|----------|
| **CLAUDE.md** | 每次会话自动加载的持久化上下文 | 项目规范、构建命令、团队约定 |
| **Skill** | 可复用的知识、工作流，通过 `/名称` 调用 | API 文档、部署流程、代码审查清单 |
| **MCP** | 连接外部服务（数据库、浏览器、API 等） | 需要 Claude 操作外部系统 |
| **Subagent** | 隔离执行上下文，返回摘要 | 并行任务、专业工人 |
| **Hook** | 事件触发的确定性脚本 | 每次编辑后自动格式化、提交前 lint |
| **Plugin** | 打包分发上述所有特性 | 跨项目复用、团队共享 |

---

## 七、特殊功能

- **Prompt Suggestions**：会话初始和 Claude 回答后自动显示灰色建议文本，按 Tab 接受
- **Session Recap**：离开 3 分钟后返回时显示一行会话总结
- **PR Review Status**：有开放 PR 时在底部显示 PR 状态链接
- **Background Bash**：`Ctrl+B` 将长时间运行的命令放到后台
- **Voice Dictation**：按住空格键语音输入
- **Transcript Viewer**：`Ctrl+O` 打开详细工具调用记录
