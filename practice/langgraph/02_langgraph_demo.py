import os
import logging
import asyncio

from typing import Any, Callable, Literal
from dotenv import load_dotenv

# langchain 相关
from langchain.agents.middleware.types import after_model, wrap_tool_call
from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables.config import RunnableConfig
from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentState,
    SummarizationMiddleware,
    ToolCallRequest,
)

# langgraph 相关
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.runtime import Runtime
from langgraph.types import Command

# 模型服务
from chat_model_service import chat_model_service

# 加载环境变量
load_dotenv()

# 暂定内存记忆
checkpointer = InMemorySaver()

# 使用 token 计数回调
usage_callback = UsageMetadataCallbackHandler()

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format=_LOG_FORMAT,
    datefmt=_LOG_DATEFMT,
)
logger = logging.getLogger(__name__)

# 定义一些 middleware
summarization_middleware = SummarizationMiddleware(
    # 摘要模型
    model=chat_model_service.chat_model_flash,
    # 摘要触发点：当消息数达到 30 条或 token 数达到 3000 时，触发摘要
    trigger=[("messages", 10), ("tokens", 3000)],
    # 摘要保留：保留最近 10 条消息
    keep=("messages", 5),
    # 摘要长度：摘要长度为 500 个 token，超过 500 个 token 的摘要将被截断
    trim_tokens_to_summarize=500,
)


@after_model
def after_model_middleware(state: AgentState, runtime: Runtime) -> dict | None:
    """每次调用模型后打印消息数和 token 数"""
    messages = state.get("messages", [])
    n = len(messages)
    
    
    model_name = messages[-1].response_metadata.get("model_name", None)
    usage_metadata = usage_callback.usage_metadata.get(model_name)
    total_tokens = usage_metadata.get("total_tokens", 0)
    input_tokens = usage_metadata.get("input_tokens", 0)
    output_tokens = usage_metadata.get("output_tokens", 0)

    logger.info(
        "模型调用完成，当前消息数: %s, 使用 %s 模型，消耗总token: %s, 消耗输入token: %s, 消耗输出token: %s",
        n,
        model_name,
        total_tokens,
        input_tokens,
        output_tokens,
    )
    return None


@wrap_tool_call
async def awrap_tool_call_middleware(
    request: ToolCallRequest,
    handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
) -> ToolMessage | Command:
    tool = request.tool
    logger.info(f"awrap_tool_call_middleware 即将调用工具: {tool.name}")
    logger.info(f"awrap_tool_call_middleware 工具描述: {tool.description}")
    logger.info(f"awrap_tool_call_middleware 工具参数: {tool.args_schema}")
    result = await handler(request)
    logger.info(f"awrap_tool_call_middleware 工具调用完成，返回结果: {result}")
    return result


@tool
async def calculate(
    operation: Literal["+", "-", "*", "/"], a: float, b: float
) -> float:
    """
    计算两个数的四则运算
    Args:
        operation: 运算符 + - * /
        a: 第一个数
        b: 第二个数
    Returns:
        float: 计算结果
    """
    if operation == "+":
        return a + b
    elif operation == "-":
        return a - b
    elif operation == "*":
        return a * b
    elif operation == "/":
        return a / b
    else:
        raise ValueError(f"calculate 工具参数错误: {operation}")


# 创建 agent
agent = create_agent(
    model=chat_model_service.chat_model,
    tools=[calculate],
    system_prompt=SystemMessage(content="你是一个助手，请根据用户的问题，给出回答。"),
    debug=False,
    checkpointer=checkpointer,
    middleware=[
        summarization_middleware,
        after_model_middleware,
        awrap_tool_call_middleware,
    ],
    name="test_agent",
)


async def chat(query: str, user_id: str):
    async for chunk, _ in agent.astream(
        input={"messages": [HumanMessage(content=query)]},
        stream_mode="messages",
        config=RunnableConfig(
            configurable={"thread_id": user_id},
            callbacks=[usage_callback],
        ),
    ):
        print(chunk.content, end="", flush=True)


if __name__ == "__main__":
    import uuid

    user_id = str(uuid.uuid4())

    while True:
        query = input("请输入问题: ").strip()
        if query.lower() in ["exit", "quit"]:
            break
        asyncio.run(chat(query, user_id))
        print()
    print("再见！欢迎下次使用！")
