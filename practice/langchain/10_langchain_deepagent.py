import os
import json

from pathlib import Path
from typing import Any
from dotenv import load_dotenv

# langchain 相关
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai.chat_models import ChatOpenAI

# langgraph 相关
from langgraph.checkpoint.memory import InMemorySaver

# deepagents 相关
from deepagents import create_deep_agent

# 加载环境变量
load_dotenv()

chat_model = ChatOpenAI(
    model=os.getenv("QWEN_CHAT_MODEL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    streaming=True,
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    model_kwargs={
        "stream_options": {
            "include_usage": True,
        },
    },
    extra_body={
        "enable_thinking": True,
        "thinking_budget": 200,
    },
)


@tool(
    description="windows 系统下在当前文件的同一个目录下创建一个文件，并写入内容",
    args_schema={
        "file_name": {
            "type": "string",
            "description": "文件名",
        },
        "content": {
            "type": "string | dict[str, Any]",
            "description": "文件内容",
        },
    },
)
def win_create_file(file_name: str, content: str | dict[str, Any]) -> None:
    path = Path(__file__).parent
    file_path = path / file_name
    # 中文乱码问题，使用 utf-8 编码
    if file_path.exists():
        return f"文件 {file_name} 已存在"
    else:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content if isinstance(content, str) else json.dumps(content))


@tool(
    description="windows 系统下在当前文件的同一个目录下列出所有文件",
)
def win_list_files(path: str) -> list[str]:
    path = Path(__file__).parent
    return [file.name for file in path.iterdir()]


@tool(
    description="windows 系统下获取当前文件的目录",
)
def win_get_current_path() -> str:
    return Path(__file__).parent.as_posix()


memory = InMemorySaver()


deep_agent = create_deep_agent(
    model=chat_model,
    debug=False,
    tools=[win_create_file, win_list_files, win_get_current_path],
    system_prompt="你是一个助手，请根据用户的问题，给出回答。",
    checkpointer=memory,
)


def _stream_chunk_text(chunk) -> str:
    """从 Chat 流式 chunk 中取出完整可打印文本（含 Qwen thinking 的 reasoning）。"""
    if chunk is None:
        return ""
    parts: list[str] = []
    ak = getattr(chunk, "additional_kwargs", None) or {}
    if isinstance(ak, dict):
        reasoning = ak.get("reasoning_content") or ak.get("thought")
        if reasoning:
            parts.append(str(reasoning))
    content = getattr(chunk, "content", None)
    if content:
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict) and block.get("text"):
                    parts.append(str(block["text"]))
    return "".join(parts)


async def chat(query: str):
    print("开始进行 deepagent 的调用")

    async for event in deep_agent.astream_events(
        input={"messages": [HumanMessage(content=query)]},
        config=RunnableConfig(
            configurable={"thread_id": "thread-1"},
        ),
        version="v2",
    ):
        kind = event.get("event")
        if kind == "on_chain_start":
            print(f"[Chain 开始] {event.get('name')}")
        elif kind == "on_chain_end":
            print(f"[Chain 结束] {event.get('name')}")
        elif kind == "on_tool_start":
            data = event.get("data", {}) or {}
            print(
                f"[Tool 开始] 工具名称: {event.get('name')} 输入: {data.get('input')}"
            )
        elif kind == "on_tool_end":
            data = event.get("data", {}) or {}
            print(
                f"[Tool 结束] 工具名称: {event.get('name')} 输出: {data.get('output')}"
            )
        elif kind == "on_chat_model_stream":
            chunk = (event.get("data") or {}).get("chunk")
            text = _stream_chunk_text(chunk)
            if text:
                print(text, end="", flush=True)

    print()


if __name__ == "__main__":
    import asyncio

    query = input("请输入问题: ").strip()
    while query.lower() not in ["exit", "quit"]:
        asyncio.run(chat(query))
        query = input("请输入问题: ").strip()
    print("再见！欢迎下次使用！")
