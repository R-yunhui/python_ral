# 实时进度推送功能使用说明

## 功能概述

实时进度推送功能允许前端实时查看工作流生成过程中每个 Agent 的执行情况，包括：
- ✅ 意图理解进度
- ✅ 工具选择进度
- ✅ 知识库匹配进度
- ✅ 工作流生成进度

## 技术实现

### 后端（Python）

#### 1. 进度事件模型
文件：`models/progress.py`

```python
from models.progress import ProgressEvent, ProgressEventType, AgentName

# 创建进度事件
event = ProgressEvent.create_agent_complete_event(
    agent_name=AgentName.INTENT_UNDERSTANDING,
    data={"workflow_type": "工具调用"},
    duration_ms=2100.5
)
```

#### 2. 编排器支持事件回调
文件：`core/graph.py`

```python
# 创建带进度回调的编排器
async def progress_callback(event: ProgressEvent):
    await send_to_frontend(event)

orchestrator = WorkflowOrchestrator(
    config_obj=config,
    progress_callback=progress_callback
)

# 使用流式生成
result = await orchestrator.generate_with_progress(
    user_input=query,
    progress_callback=progress_callback
)
```

#### 3. SSE 流式 API
文件：`api.py`

```python
@app.post("/api/generate/stream")
async def generate_workflow_stream(request: GenerateRequest):
    """SSE 流式生成接口"""
    # 实现见 api.py
```

### 前端（JavaScript）

#### 1. 使用 EventSource 连接 SSE

```javascript
async function generateWithSSE(query) {
    return new Promise((resolve, reject) => {
        const eventSource = new EventSource('/api/generate/stream');
        
        // 监听进度事件
        eventSource.addEventListener('progress', (event) => {
            const data = JSON.parse(event.data);
            handleProgressEvent(data);
        });
        
        // 监听最终结果
        eventSource.addEventListener('final_result', (event) => {
            const data = JSON.parse(event.data);
            eventSource.close();
            showResult(data);
            resolve();
        });
        
        // 监听错误
        eventSource.addEventListener('error', (event) => {
            const data = JSON.parse(event.data);
            eventSource.close();
            showError(data);
            reject(new Error(data.message));
        });
        
        // 发送生成请求
        fetch('/api/generate/stream', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ query })
        });
    });
}
```

#### 2. 处理进度事件

```javascript
function handleProgressEvent(data) {
    const { event_type, agent_name, message, progress, data: eventData } = data;
    
    // 更新进度条
    updateProgressBar(progress);
    
    // 添加日志
    if (event_type === 'agent_complete') {
        addSuccessLog(message, eventData);
    } else if (event_type === 'agent_error') {
        addErrorLog(message, eventData);
    }
}
```

## API 接口

### 传统接口（保留）

**POST** `/api/generate`

- 一次性返回最终结果
- 适合不需要实时进度的场景

### 流式接口（新增）

**POST** `/api/generate/stream`

- 返回 SSE 事件流
- 实时推送每个 Agent 的执行进度
- 最后返回最终结果

#### SSE 事件类型

| 事件类型 | 说明 | 数据内容 |
|---------|------|---------|
| `progress` | 进度事件 | ProgressEvent 对象 |
| `final_result` | 最终结果 | 完整生成结果 |
| `error` | 错误事件 | 错误信息 |

#### ProgressEvent 结构

```typescript
interface ProgressEvent {
    event_type: "start" | "agent_start" | "agent_complete" | "agent_error" | "complete" | "error";
    timestamp: string;  // ISO 8601 格式
    agent_name?: "intent_understanding" | "tool_selection" | "knowledge_matching" | "workflow_generation";
    message: string;  // 人类可读的描述
    data?: any;  // 事件数据
    progress?: number;  // 0-100 的进度百分比
    duration_ms?: number;  // Agent 执行耗时
    error?: string;  // 错误信息
}
```

## 使用示例

### 后端调用示例

```python
from core.graph import WorkflowOrchestrator
from models.progress import ProgressEvent

# 定义回调函数
async def my_progress_callback(event: ProgressEvent):
    print(f"[{event.progress}%] {event.message}")
    if event.data:
        print(f"  数据：{event.data}")

# 创建编排器
orchestrator = WorkflowOrchestrator(
    config_obj=config,
    progress_callback=my_progress_callback
)

# 生成工作流
result = await orchestrator.generate_with_progress(
    user_input="创建一个天气查询助手",
    progress_callback=my_progress_callback
)
```

### 前端调用示例

```javascript
// 使用新的流式接口
async function generateWorkflow() {
    const query = document.getElementById('queryInput').value;
    
    try {
        await generateWithSSE(query);
        console.log('生成成功');
    } catch (error) {
        console.error('生成失败:', error);
    }
}
```

## 前端 UI 效果

```
┌─────────────────────────────────────────┐
│  📊 执行进度                    75%     │
├─────────────────────────────────────────┤
│ ████████████████████████░░░░░░░░░░░░░░  │
├─────────────────────────────────────────┤
│                                         │
│  ✅ 意图理解完成              耗时:2.1s │
│     工作流类型：工具调用 + 知识库检索    │
│                                         │
│  ✅ 工具选择完成              耗时:1.8s │
│     选中 3 个工具：天气 API、政策搜索...   │
│                                         │
│  ⚙️ 正在执行：知识库匹配                │
│                                         │
└─────────────────────────────────────────┘
```

## 事件推送时机

```mermaid
sequenceDiagram
    participant 前端
    participant API
    participant Orchestrator
    participant Agents

    前端->>API: POST /api/generate/stream
    API-->>前端：SSE 连接建立
    
    API->>Orchestrator: generate_with_progress()
    Orchestrator-->>API: 开始事件
    API-->>前端：推送：开始生成 (0%)
    
    Orchestrator->>Agents: 执行意图理解
    Agents-->>Orchestrator: 完成
    Orchestrator-->>API: 意图理解完成 (25%)
    API-->>前端：推送：意图理解完成
    
    Orchestrator->>Agents: 执行工具选择
    Agents-->>Orchestrator: 完成
    Orchestrator-->>API: 工具选择完成 (50%)
    API-->>前端：推送：工具选择完成
    
    Orchestrator->>Agents: 执行知识库匹配
    Agents-->>Orchestrator: 完成
    Orchestrator-->>API: 知识库匹配完成 (75%)
    API-->>前端：推送：知识库匹配完成
    
    Orchestrator->>Agents: 执行工作流生成
    Agents-->>Orchestrator: 完成
    Orchestrator-->>API: 工作流生成完成 (100%)
    API-->>前端：推送：工作流生成完成
    
    Orchestrator-->>API: 返回最终结果
    API-->>前端：推送：final_result
    API-->>前端：关闭连接
```

## 错误处理

### 前端错误处理

```javascript
eventSource.addEventListener('error', (event) => {
    const data = JSON.parse(event.data);
    
    // 显示错误信息
    showError(data.message || '生成失败');
    
    // 清理 UI
    hideProgress();
    enableGenerateButton();
});

// 连接错误
eventSource.onerror = () => {
    showError('连接服务器失败');
    eventSource.close();
};
```

### 后端错误处理

```python
try:
    result = await orchestrator.generate_with_progress(...)
except Exception as e:
    await progress_callback(
        ProgressEvent.create_error_event(str(e))
    )
    return {"status": "error", "message": str(e)}
```

## 性能优化

### 1. 禁用 Nginx 缓冲

如果使用 Nginx 部署，需要禁用缓冲：

```nginx
location /api/generate/stream {
    proxy_pass http://backend;
    proxy_buffering off;
    proxy_cache off;
    proxy_connect_timeout 60s;
    proxy_read_timeout 60s;
}
```

### 2. 前端节流

如果事件推送频率过高，可以在前端进行节流：

```javascript
// 使用 lodash 的 throttle
const updateProgress = throttle((data) => {
    // 更新 UI
}, 100);

eventSource.addEventListener('progress', (event) => {
    updateProgress(JSON.parse(event.data));
});
```

## 兼容性说明

### 浏览器兼容性

- ✅ Chrome/Edge: 完全支持
- ✅ Firefox: 完全支持
- ✅ Safari: 完全支持
- ⚠️ IE11: 需要 polyfill

### 降级方案

对于不支持 SSE 的浏览器，可以：
1. 使用传统的 `/api/generate` 接口
2. 使用轮询方案（不推荐）

## 测试方法

### 1. 手动测试

```bash
# 启动服务
cd bisheng_generator
python api.py

# 访问 http://localhost:8000
# 输入需求，点击生成
# 观察进度条和日志更新
```

### 2. API 测试

```bash
# 使用 curl 测试 SSE
curl -N http://localhost:8000/api/generate/stream \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query":"创建一个天气查询助手"}'
```

### 3. 单元测试

```python
import pytest
from models.progress import ProgressEvent

def test_progress_event_creation():
    event = ProgressEvent.create_agent_complete_event(
        agent_name=AgentName.INTENT_UNDERSTANDING,
        data={"workflow_type": "工具调用"},
        duration_ms=1000
    )
    assert event.event_type == ProgressEventType.AGENT_COMPLETE
    assert event.progress == 25.0
```

## 常见问题

### Q: SSE 和 WebSocket 有什么区别？

A: 
- SSE 是单向的（服务器→客户端），WebSocket 是双向的
- SSE 更简单，原生支持，自动重连
- WebSocket 更复杂，需要额外库
- 本场景只需要单向推送，SSE 更合适

### Q: 为什么有时候收不到事件？

A: 可能的原因：
1. Nginx 缓冲未禁用
2. 防火墙拦截长连接
3. 浏览器兼容性问
