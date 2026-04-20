import os
from typing import Any, override

from dotenv import load_dotenv

# langchain 相关
from langchain_community.chat_models import ChatTongyi
from langchain_core.outputs import LLMResult
from langchain_core.runnables import RunnableConfig
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import UsageMetadataCallbackHandler, BaseCallbackHandler
from langchain.agents import create_agent

# langgraph
from langgraph.checkpoint.memory import InMemorySaver

# 加载环境变量
load_dotenv()


class ChatOpenAIWithThinking(ChatOpenAI):
    """
    支持提取 Qwen 系列模型 thinking/reasoning_content 的 ChatOpenAI 子类。

    langchain-openai 的 _convert_delta_to_message_chunk 不处理
    delta.reasoning_content 字段（这是 DashScope Qwen 系列模型的扩展），
    所以需要覆盖 _convert_chunk_to_generation_chunk 来手动提取。
    """

    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: type,
        base_generation_info: dict | None,
    ):
        result = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info
        )
        if result is None:
            return None

        # 从原始 chunk 的 delta 中提取 reasoning_content
        choices = chunk.get("choices", [])
        if choices:
            delta = choices[0].get("delta", {})
            reasoning_content = delta.get("reasoning_content")
            if reasoning_content:
                result.message.additional_kwargs["reasoning_content"] = (
                    reasoning_content
                )
        return result

usage_callback = UsageMetadataCallbackHandler()

in_memory = InMemorySaver()

chat_model = ChatOpenAIWithThinking(
    model=os.getenv("QWEN_CHAT_MODEL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    streaming=True,
    extra_body={
        "enable_thinking": True,
        "thinking_budget": None,
    },
    model_kwargs={
        "stream_options": {
            "include_usage": True,
        },
    },
)

chat_ty = ChatTongyi(
    model=os.getenv("QWEN_CHAT_MODEL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    streaming=True,
    model_kwargs={
        "stream_options": {
            "include_usage": True,
        },
    },
    extra_body={
        "enable_thinking": True,
        "thinking_budget": None,
    },
)

openai_agent = create_agent(
    model=chat_model,
    system_prompt=SystemMessage(content="你是一个专业的聊天助手"),
    checkpointer=in_memory,
    tools=[],
)


async def chat(query: str) -> None:
    first_thinking = True
    first_content = True

    async for chunk, meta in openai_agent.astream(
        input={"messages": [HumanMessage(content=query)]},
        config=RunnableConfig(
            callbacks=[usage_callback], configurable={"thread_id": "001"}
        ),
        stream_mode="messages",  # 用 messages 模式
    ):
        # chunk 是 AIMessageChunk
        # 从 additional_kwargs 提取 reasoning_content
        reasoning_content = chunk.additional_kwargs.get("reasoning_content", "")
        if reasoning_content:
            if first_thinking:
                print("思考内容：\n")
                first_thinking = False
            print(reasoning_content, end="", flush=True)

        if chunk.content:
            if first_content:
                print("\n正文内容：\n")
                first_content = False
            print(chunk.content, end="", flush=True)


if __name__ == "__main__":
    import asyncio

    asyncio.run(chat("qwen3.6-plus 一个中文占用多少token"))

    print(f"\n {usage_callback.usage_metadata}")
