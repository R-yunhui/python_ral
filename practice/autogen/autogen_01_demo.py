import os

from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import TextMessage, ThoughtEvent, ModelClientStreamingChunkEvent
from autogen_agentchat.tools import AgentTool
from autogen_agentchat.ui import Console
from dotenv import load_dotenv

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

# 加载环境变量
load_dotenv()


def build_openai_chat_client() -> OpenAIChatCompletionClient:
    return OpenAIChatCompletionClient(
        model=os.getenv("QWEN_CHAT_MODEL"),
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url=os.getenv("DASHSCOPE_BASE_URL"),
        max_retries=3,
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": False,
            "structured_output": False,
            "family": "unknown",
        },
    )


async def chat(query: str) -> None:
    model_client = build_openai_chat_client()

    try:
        agent = AssistantAgent(
            "assistant",
            model_client=model_client,
            model_client_stream=True,
            system_message="你是简洁友好的中文助手。",
        )

        # 官方内置的
        await Console(agent.run_stream(task=query))

        # async for item in agent.run_stream(task=query):
        #     if isinstance(item, ModelClientStreamingChunkEvent):
        #         print(item.content, end="", flush=True)
        #     elif isinstance(item, TextMessage):
        #         print(item.content, end="", flush=True)

        # result = await agent.run(task=query)
        # messages = result.messages
        # for message in messages:
        #     if isinstance(message, ThoughtEvent):
        #         print(f"思考内容：{message.content}")
        #     elif isinstance(message, TextMessage):
        #         print(f"最终回答：{message.content}")
    finally:
        await model_client.close()


async def chat_with_multiagent() -> None:
    model_client = build_openai_chat_client()
    try:
        math_agent = AssistantAgent(
            "math_expert",
            model_client=model_client,
            system_message="你是数学专家，回答要简洁。",
            description="数学专家。",
            model_client_stream=True,
        )
        math_tool = AgentTool(math_agent, return_value_as_last_message=True)
        chemistry_agent = AssistantAgent(
            "chemistry_expert",
            model_client=model_client,
            system_message="你是化学专家，回答要简洁。",
            description="化学专家。",
            model_client_stream=True,
        )
        chemistry_tool = AgentTool(chemistry_agent, return_value_as_last_message=True)
        coordinator = AssistantAgent(
            "coordinator",
            model_client=model_client,
            system_message="根据问题选择合适的专家工具，不要编造。",
            model_client_stream=True,
            tools=[math_tool, chemistry_tool],
            max_tool_iterations=10,
        )
        await Console(coordinator.run_stream(task="x^2 的不定积分？"))
        print()
        await Console(coordinator.run_stream(task="水的分子量大约多少？"))
    finally:
        await model_client.close()


if __name__ == "__main__":
    import asyncio

    # asyncio.run(chat("用一句话解释什么是多智能体（multi-agent）。"))

    asyncio.run(chat_with_multiagent())
