# 毕昇工作流生成器 - Web 版

基于 FastAPI 的毕昇工作流生成器 Web 界面，支持工作流生成、查看和下载。

## 功能特性

- ✨ 美观的现代化 UI 界面
- 🚀 一键生成毕昇工作流
- 📄 实时查看生成的 JSON 工作流
- 💾 下载工作流文件
- 📋 复制 JSON 到剪贴板
- 📜 查看历史工作流记录
- 🔍 支持查看任意历史工作流

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

确保已配置以下环境变量（或在项目根目录创建 `.env` 文件）：

```bash
# LLM 配置（以 DashScope 为例）
LLM_PROVIDER=dashscope
LLM_MODEL=qwen3.5-plus
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_TEMPERATURE=0.7

# Embedding 配置
EMBEDDING_MODEL=text-embedding-v3

# 日志配置
LOG_LEVEL=INFO
```

### 3. 启动服务

```bash
cd bisheng_generator
python api.py
```

### 4. 访问应用

打开浏览器访问：http://localhost:8000

API 文档：http://localhost:8000/docs

## 项目结构

```
bisheng_generator/
├── api.py              # FastAPI 后端服务
├── main.py             # 命令行入口
├── static/             # 前端静态文件
│   ├── index.html      # 主页面
│   ├── style.css       # 样式文件
│   └── app.js          # 前端交互逻辑
├── config/             # 配置模块
├── core/               # 核心编排模块
├── agents/             # Agent 模块
├── models/             # 数据模型
└── output/             # 工作流输出目录（自动生成）
```

## API 接口

### 生成工作流

**POST** `/api/generate`

请求体：
```json
{
  "query": "创建一个深汕招商政策查询助手"
}
```

响应：
```json
{
  "status": "success",
  "message": "工作流生成成功",
  "workflow": {...},
  "metadata": {
    "intent": {...},
    "tools_count": 0,
    "knowledge_count": 0
  },
  "file_path": "output/workflow_xxx.json"
}
```

### 获取工作流列表

**GET** `/api/workflows`

返回所有已生成的工作流列表。

### 获取工作流详情

**GET** `/api/workflow/{filename}`

返回指定工作流的详细内容。

### 下载工作流

**GET** `/api/download/{filename}`

下载指定工作流文件（JSON 格式）。

### 健康检查

**GET** `/api/health`

检查服务运行状态。

## 使用示例

### 1. 生成工作流

在页面输入框中输入您的需求，例如：

- "创建一个深汕招商政策查询助手"
- "帮我做一个海洋政策咨询工作流"
- "生成一个简单问答助手，支持天气查询"

点击"生成工作流"按钮，等待生成完成。

### 2. 查看结果

生成成功后，页面会显示：

- 工作流类型
- 选中工具数
- 匹配知识库数
- 完整的 JSON 工作流

### 3. 下载或复制

- 点击"下载 JSON"按钮保存文件
- 点击"复制 JSON"按钮复制到剪贴板

### 4. 查看历史

页面底部会显示所有历史工作流，可以：

- 点击"查看"按钮查看详细内容
- 点击"下载"按钮下载文件

## 开发说明

### 前端技术栈

- 原生 HTML5 + CSS3 + JavaScript
- 无需构建工具，开箱即用
- 响应式设计，支持移动端

### 后端技术栈

- FastAPI：高性能 Web 框架
- Uvicorn：ASGI 服务器
- LangGraph：工作流编排
- Pydantic：数据验证

### 添加新功能

1. 在 `api.py` 中添加新的 API 接口
2. 在 `static/app.js` 中添加前端交互逻辑
3. 在 `static/index.html` 中添加 UI 元素
4. 在 `static/style.css` 中添加样式

## 注意事项

1. 首次运行需要配置 LLM API Key
2. 工作流文件保存在 `output/` 目录
3. 生产环境部署时请修改 CORS 配置
4. 建议使用反向代理（如 Nginx）部署

## 故障排查

### 无法启动服务

检查依赖是否安装完整：
```bash
pip install -r requirements.txt --upgrade
```

### LLM 初始化失败

检查环境变量配置是否正确，API Key 是否有效。

### 前端页面无法访问

确保服务启动成功，访问 http://localhost:8000

### 工作流生成失败

查看后端日志输出，确认错误信息。

## 许可证

MIT License
