import os

from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

# langchain
from langchain_core.runnables import RunnableConfig
from langchain_openai.chat_models import ChatOpenAI
from langchain.messages import HumanMessage, SystemMessage

# deepagents
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.local_shell import LocalShellBackend
from deepagents.backends.composite import CompositeBackend


# langgraph
from langgraph.checkpoint.memory import InMemorySaver

# 加载 env
load_dotenv()

chat_model = ChatOpenAI(
    model=os.getenv("QWEN_CHAT_MODEL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    streaming=True,
    temperature=0.7,
    max_tokens=None,
    model_kwargs={
        "stream_options": {
            "include_usage": True,
        },
    },
    extra_body={
        "enable_thinking": True,
        "thinking_budget": 100,
    },
)

# 统一工作目录 —— shell 执行和文件读写都在这里
WORK_DIR = Path(__file__).parent / "workspace"
WORK_DIR.mkdir(exist_ok=True)

local_shell_backend = LocalShellBackend(
    root_dir=str(WORK_DIR),   # shell 工作目录也在 workspace
    virtual_mode=False,
    env=os.environ.copy(),
)

deep_agent = create_deep_agent(
    model=chat_model,
    system_prompt=SystemMessage(
        content=f"""
        你是一个助手，请根据用户的问题，给出回答。
        当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

        【重要规则】
        1. 所有文件的创建、读取、修改，必须在当前工作目录下进行，
        2. 执行脚本时使用相对路径，例如：python quick_sort.py
           而不是 python /quick_sort.py 或 python D:\\quick_sort.py
        3. 当前工作目录：{WORK_DIR}
        """
    ),
    debug=False,
    checkpointer=InMemorySaver(),
    backend=local_shell_backend,
)


async def chat(query: str, thread_id: str):
    async for event in deep_agent.astream_events(
        input={"messages": [HumanMessage(content=query)]},
        config=RunnableConfig(
            configurable={"thread_id": thread_id}, recursion_limit=50
        ),
        version="v1",
    ):
        kind = event.get("event")
        if kind == "on_chain_start":
            print(f"开始执行链式调用, 链式调用名称: {event['name']}")
        elif kind == "on_chain_end":
            print(f"完成执行链式调用, 链式调用名称: {event['name']}")
        elif kind == "on_tool_start":
            print(
                f"开始调用工具, 工具名称: {event['name']}, 工具输入: {event['data']['input']}"
            )
        elif kind == "on_tool_end":
            print(
                f"完成调用工具, 工具名称: {event['name']}, 工具输出: {event['data']['output']}"
            )
        elif kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and chunk.content:
                print(chunk.content, end="", flush=True)
    print()


if __name__ == "__main__":
    import asyncio
    import uuid

    thread_id = str(uuid.uuid4())
    while True:
        query = input("请输入问题, 输入 exit 或 quit 退出: ").strip()
        if query.lower() in ["exit", "quit"]:
            break
        asyncio.run(chat(query, thread_id))
    print("再见!")
