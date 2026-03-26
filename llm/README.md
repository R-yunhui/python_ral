# LLM 学习示例（LangChain / LangGraph / deepagents）

这组示例按学习顺序组织：

1. `01_langchain_basics.py`：最小 LangChain 链式调用
2. `02_langgraph_state_flow.py`：最小 LangGraph 状态图与分支
3. `03_deepagents_quickstart.py`：最小 deepagents 智能体（需要可调用工具的在线模型）
4. `04_langgraph_with_tools.py`：LangGraph 状态图内调用工具并按条件路由

## 运行方式

在项目根目录执行：

```powershell
.\.venv\Scripts\python .\llm\01_langchain_basics.py
.\.venv\Scripts\python .\llm\02_langgraph_state_flow.py
.\.venv\Scripts\python .\llm\03_deepagents_quickstart.py
.\.venv\Scripts\python .\llm\04_langgraph_with_tools.py
```

## 可选：切换到真实模型

默认是离线演示（前两个脚本）。如果你要让前两个脚本也连真实模型：

```powershell
$env:USE_REAL_LLM="1"
$env:OPENAI_API_KEY="你的key"
.\.venv\Scripts\python .\llm\01_langchain_basics.py
```

`03_deepagents_quickstart.py` 默认要求：

- `USE_REAL_LLM=1`
- `OPENAI_API_KEY` 已配置

因为 deepagents 依赖可调用工具（tool calling）模型，离线假模型不支持该能力。
