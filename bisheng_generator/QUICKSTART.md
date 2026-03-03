# 实时进度推送功能 - 快速启动指南

## 🚀 5 分钟快速体验

### 步骤 1: 检查环境

确保已安装 Python 3.8+ 和以下依赖：

```bash
pip install fastapi uvicorn sse-starlette pydantic langchain langchain-openai langgraph
```

### 步骤 2: 配置 API Key

在项目根目录创建 `.env` 文件：

```bash
# DashScope (通义千问)
LLM_PROVIDER=dashscope
LLM_MODEL=qwen3.5-plus
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_TEMPERATURE=0.7

# 或使用 OpenAI
# LLM_PROVIDER=openai
# LLM_MODEL=gpt-4
# LLM_API_KEY=sk-xxx
# LLM_BASE_URL=https://api.openai.com/v1
```

### 步骤 3: 启动服务

```bash
cd bisheng_generator
python api.py
```

看到以下输出表示成功：

```
============================================================
毕昇工作流生成器 API 服务 v0.2.0
============================================================
访问地址：http://localhost:8000
API 文档：http://localhost:8000/docs
============================================================
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 步骤 4: 访问前端

打开浏览器访问：http://localhost:8000

### 步骤 5: 测试功能

1. 在输入框中输入：`创建一个天气查询助手`
2. 点击"生成工作流"按钮
3. 观察实时进度条和日志更新
4. 等待生成完成，查看最终结果

## 📊 预期效果

### 前端展示

```
┌─────────────────────────────────────────┐
│  📊 执行进度                    50%     │
├─────────────────────────────────────────┤
│ ████████████████░░░░░░░░░░░░░░░░░░░░░░  │
├─────────────────────────────────────────┤
│                                         │
│  ✅ 意图理解完成              耗时:2.1s │
│     工作流类型：工具调用                │
│                                         │
│  ⚙️ 正在执行：工具选择                  │
│                                         │
└─────────────────────────────────────────┘
```

### 控制台输出

```
INFO: 收到流式生成请求：创建一个天气查询助手...
INFO: 收到用户输入（流式模式）：创建一个天气查询助手
INFO: 运行意图理解：创建一个天气查询助手
INFO: 意图理解完成：工具调用
INFO: 运行工具选择
INFO: 工具选择完成：选中 1 个工具
INFO: 运行知识库匹配
INFO: 知识库匹配完成：匹配到 0 个知识库
INFO: 运行工作流生成
INFO: 工作流生成完成
INFO: 工作流已保存：output/workflow_1772544161.json
```

## 🔧 故障排查

### 问题 1: 无法启动服务

**症状**: 运行 `python api.py` 报错

**解决方案**:
```bash
# 检查 Python 版本
python --version  # 需要 3.8+

# 重新安装依赖
pip install -r requirements.txt --upgrade
```

### 问题 2: LLM 初始化失败

**症状**: 显示 "LLM API Key 未配置"

**解决方案**:
1. 检查 `.env` 文件是否存在
2. 检查 `LLM_API_KEY` 是否正确
3. 重启服务

### 问题 3: 前端无法连接 SSE

**症状**: 进度条一直显示 0%

**解决方案**:
1. 打开浏览器开发者工具 (F12)
2. 查看 Console 是否有错误
3. 检查 Network 标签中的 SSE 连接状态
4. 确保没有防火墙拦截

### 问题 4: Nginx 部署后 SSE 不工作

**症状**: 本地正常，部署后无法接收事件

**解决方案**:
```nginx
# 在 Nginx 配置中添加
location /api/generate/stream {
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header Connection '';
    proxy_http_version 1.1;
}
```

## 📱 浏览器兼容性

| 浏览器 | 版本 | 支持情况 |
|--------|------|---------|
| Chrome | 60+ | ✅ 完全支持 |
| Edge | 79+ | ✅ 完全支持 |
| Firefox | 44+ | ✅ 完全支持 |
| Safari | 11+ | ✅ 完全支持 |
| IE11 | - | ⚠️ 需要 polyfill |

## 🧪 测试命令

### 1. 使用 curl 测试

```bash
curl -N http://localhost:8000/api/generate/stream \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query":"创建一个天气查询助手"}'
```

### 2. 使用 Python 测试

```bash
cd bisheng_generator
python test_progress.py
```

### 3. 使用浏览器测试

访问：http://localhost:8000/docs

在 Swagger UI 中测试 `/api/generate/stream` 接口。

## 📚 更多信息

- `PROGRESS_FEATURE.md` - 详细功能说明
- `REALTIME_PROGRESS_SUMMARY.md` - 实现总结
- `test_progress.py` - 测试脚本

## ✅ 验证清单

- [ ] 服务成功启动
- [ ] 前端页面正常访问
- [ ] 输入需求后能看到进度条
- [ ] 每个 Agent 执行完成都有日志更新
- [ ] 最终生成工作流 JSON
- [ ] 可以下载 JSON 文件
- [ ] 可以复制 JSON 到剪贴板

全部勾选表示功能正常！🎉

---

**最后更新**: 2026-03-03  
**版本**: v0.3.0
