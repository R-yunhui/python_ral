"""
langchain 创建 agent
"""

import os
import asyncio

from dotenv import load_dotenv

# langchain 基础组件
from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import HumanMessage
from langchain.agents import create_agent

# 加载环境变量
load_dotenv()

# 创建模型实例
chat_model = ChatTongyi(
    model=os.getenv("QWEN_CHAT_MODEL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    streaming=True,
)

# 创建 agent
agent = create_agent(
    model=chat_model,
    tools=[],
    debug=False,
    system_prompt="你是一个助手，请根据用户的问题，给出回答。",
)


def chat_with_agent(query: str):
    """
    与 agent 进行对话
    """
    response = agent.invoke(input={"messages": [HumanMessage(content=query)]})
    return response["messages"][-1].content


def chat_with_agent_stream(query: str):
    """
    与 agent 进行流式对话
    """
    for mode, _ in agent.stream(
        {"messages": [HumanMessage(content=query)]}, stream_mode="messages"
    ):
        print(mode.content, end="", flush=True)


async def async_chat_with_agent_stream(query: str):
    """
    与 agent 进行异步流式对话
    """
    async for mode, _ in agent.astream(
        {"messages": [HumanMessage(content=query)]}, stream_mode="messages"
    ):
        print(mode.content, end="", flush=True)


if __name__ == "__main__":
    while True:
        query = input("请输入问题: ").strip()
        if query.lower() in ["exit", "quit"]:
            break
        # chat_with_agent_stream(query)
        asyncio.run(async_chat_with_agent_stream(query))
        print()
    print("再见！欢迎下次使用！")
