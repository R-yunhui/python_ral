import os
import sys

from pathlib import Path

from dotenv import load_dotenv
from snowflake import SnowflakeGenerator, Snowflake

# 三方 langchain
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.agents import create_agent
from langchain_core.runnables import RunnableConfig

# langfuse
from langchain_core.tools import tool
from langfuse.langchain import CallbackHandler

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 本地
from practice.langgraph.chat_model_service import ChatModelService

# 加载环境变量
load_dotenv()

# 创建模型实例
chat_model = ChatModelService().chat_model


@tool
def calculate(a: int, b: int) -> int:
    """计算两个数的和"""
    return a + b


# langfuse
agent = create_agent(
    model=chat_model,
    tools=[calculate],
    system_prompt=SystemMessage(content="你是一个助手，请根据用户的问题，给出回答。"),
    debug=False,
)


async def chat(query: str, user_id: str, trace_id: int):
    """
    聊天函数

    Args:
        query: 用户的问题
        user_id: 用户 ID
        trace_id: 追踪 ID
    """
    async for chunk, metadata in agent.astream(
        input={"messages": [HumanMessage(content=query)]},
        stream_mode="messages",
        config=RunnableConfig(
            configurable={"thread_id": user_id},
            callbacks=[CallbackHandler(trace_context={"trace_id": trace_id})],
        ),
    ):
        print(chunk.content, end="", flush=True)


gen = SnowflakeGenerator(42)

if __name__ == "__main__":
    import asyncio
    import uuid

    trace_id = uuid.uuid4().hex
    
    print(f"trace_id: {trace_id}")

    user_id = str(uuid.uuid4())

    asyncio.run(chat("计算 1 + 1 的结果", user_id, trace_id))
