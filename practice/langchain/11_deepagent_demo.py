import os

from dotenv import load_dotenv
from pathlib import Path

# langchain
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

# deepagents
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.local_shell import LocalShellBackend
from deepagents.backends.composite import CompositeBackend

# langgraph
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

chat_model = ChatOpenAI(
    model=os.getenv("QWEN_CHAT_MODEL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    streaming=True,
    extra_body={
        "enable_thinking": True,
        "thinking_budget": 100,
    },
    model_kwargs={
        "stream_options": {
            "include_usage": True,
        },
    },
)

checkpointer = InMemorySaver()

env = dict(os.environ)

# 自定义 bakcend, 组装多个
local_shell_backend = LocalShellBackend(
    root_dir=str(Path(__file__).parent),
    virtual_mode=True,
    env=env,
)
composite_backend = CompositeBackend(
    default=local_shell_backend,
    routes={"/local_shell/": local_shell_backend},
)

deep_agent = create_deep_agent(
    model=chat_model,
    backend=composite_backend,
    system_prompt=SystemMessage(content="你是一个助手，请根据用户的问题，给出回答。"),
    checkpointer=checkpointer,
)


def test_filesystem_backend():
    backend = FilesystemBackend(root_dir=str(Path(__file__).parent), virtual_mode=True)
    backend.write("test.txt", "Hello, world!")
    print(backend.read("test.txt"))


async def chat_with_deepagent(query: str):

    async for event in deep_agent.astream_events(
        input={"messages": [HumanMessage(content=query)]},
        stream_mode="messages",
        config=RunnableConfig(
            configurable={"thread_id": "thread-1"},
        ),
        version="v1",
    ):
        kind = event.get("event")

        # 处理工具调用流
        if kind == "on_tool_start":
            print(f"开始调用工具, 工具名称: {event['name']}")
        elif kind == "on_tool_end":
            print(
                f"完成工具调用, 工具名称: {event['name']}, 工具执行结果: {event['data']['output']}"
            )
        # 处理 LLM 对话内容流
        elif kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and chunk.content:
                print(chunk.content, end="", flush=True)


if __name__ == "__main__":
    import asyncio

    print(f"当前系统环境变量: {env}")

    query = input("请输入问题, 输入 exit 或 quit 退出: ").strip()
    while query not in ["exit", "quit"]:
        asyncio.run(chat_with_deepagent(query))
        print()
        query = input("请输入问题, 输入 exit 或 quit 退出: ").strip()
    print("再见!")
