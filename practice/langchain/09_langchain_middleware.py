"""
langchain 中间件

演示如何使用 langchain 中间件来实现自定义的中间件。

中间件是一种机制，用于在 LangChain 的执行过程中插入自定义逻辑。

中间件可以用于实现各种功能，例如：

- 记录请求和响应
"""

import os
import logging

from dotenv import load_dotenv
from typing import Any, Awaitable
from collections.abc import Callable

# langchain 相关
from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ExtendedModelResponse,
    ModelRequest,
    ModelResponse,
    ResponseT,
)
from langchain_core import tools
from langchain_core.runnables.config import RunnableConfig
from langchain_openai.chat_models import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage

# langgraph 相关
from langgraph.runtime import Runtime
from langgraph.types import Command
from langgraph.typing import ContextT, StateT
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt.tool_node import ToolCallRequest, ToolCallWrapper

# 加载环境变量
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

chat_model = ChatOpenAI(
    model=os.getenv("QWEN_CHAT_MODEL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    streaming=True,
    model_kwargs={
        "stream_options": {
            "include_usage": True,
        },
    },
    extra_body={
        "enable_thinking": False,
        # "thinking_budget": 100,
    },
    temperature=0.7,
    max_tokens=None,
)


class CustomMiddlerWare(AgentMiddleware):

    async def abefore_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        """每次调用模型前打印消息数"""
        n = len(state.get("messages", []))
        logger.info(f"[CustomMiddleware] 即将调用模型，当前消息数: {n}")
        return None  # 不更新 state

    async def aafter_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        """每次调用模型后执行"""
        print()
        logger.info("[CustomMiddleware] 模型调用完成")
        return None

    async def abefore_agent(
            self, state: StateT, runtime: Runtime[ContextT]
    ) -> dict[str, Any] | None:
        """每次代理执行开始"""
        logger.info("[CustomMiddleware] 代理执行开始")
        return None

    async def aafter_agent(
            self, state: StateT, runtime: Runtime[ContextT]
    ) -> dict[str, Any] | None:
        """每次代理执行完成"""
        logger.info("[CustomMiddleware] 代理执行完成")
        return None

    async def awrap_tool_call(
            self,
            request: ToolCallRequest,
            handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        """每次调用工具前打印工具名称"""
        logger.info(f"[CustomMiddleware] 即将调用工具: {request.tool.get_name()}")
        return await handler(request)

    async def awrap_model_call(
            self,
            request: ModelRequest[ContextT],
            handler: Callable[
                [ModelRequest[ContextT]], Awaitable[ModelResponse[ResponseT]]
            ],
    ) -> ModelResponse[ResponseT] | AIMessage | ExtendedModelResponse[ResponseT]:
        """每次调用模型前打印模型名称"""
        logger.info(f"[CustomMiddleware] 即将调用模型: {request.model.model}")
        return await handler(request)


# 暂时使用内存记忆
saver = InMemorySaver()


@tools.tool
def calculate(a: int, b: int, operation: str) -> int:
    """
    计算两个数的四则运算
    Args:
        a: 第一个数
        b: 第二个数
        operation: 运算符 + - * /
    Returns:
        int: 计算结果
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
        raise ValueError(f"Invalid operation: {operation}")


agent = create_agent(
    model=chat_model,
    system_prompt=SystemMessage(content="你是一个助手，请根据用户的问题，给出回答。"),
    debug=False,
    middleware=[CustomMiddlerWare()],
    checkpointer=saver,
    tools=[calculate],
)


async def chat(query: str, chat_id: str):
    async for chunk, _ in agent.astream(
            input={"messages": [HumanMessage(content=query)]},
            stream_mode="messages",
            config=RunnableConfig(
                configurable={"thread_id": chat_id},
            ),
    ):
        print(chunk.content, end="", flush=True)
    logger.info("流式问答完成")


if __name__ == "__main__":
    import asyncio

    while True:
        query = input("请输入问题: ")
        if query.lower() in ["exit", "quit"]:
            break
        asyncio.run(chat(query, "thread-1"))

    print("程序结束")
