# langgraph 演示
import os
from dotenv import load_dotenv

# langchain 相关
from langchain_core.callbacks.usage import UsageMetadataCallbackHandler
from langchain_openai import ChatOpenAI
from langchain.messages import HumanMessage, SystemMessage
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.runnables.config import RunnableConfig


# 加载环境变量
load_dotenv()

chat_model = ChatOpenAI(
    model=os.getenv("QWEN_CHAT_MODEL"),
    temperature=0.7,
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    # 不限制 token
    max_tokens=None,
    streaming=True,
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

checkpointer = InMemorySaver()

agent = create_agent(
    model=chat_model,
    tools=[],
    system_prompt=SystemMessage(content="你是一个助手，请根据用户的问题，给出回答。"),
    debug=True,
    checkpointer=checkpointer,
)

usage_callback = UsageMetadataCallbackHandler()


async def chat(query: str):
    print("开始进行 agent 的调用")

    async for chunk, metadata in agent.astream(
        input={"messages": [HumanMessage(content=query)]},
        stream_mode="messages",
        config=RunnableConfig(
            configurable={"thread_id": "thread-1"},
            callbacks=[usage_callback],
        ),
    ):
        print(chunk.content, end="", flush=True)

    usage_metadata = usage_callback.usage_metadata.get(os.getenv("QWEN_CHAT_MODEL"))
    print(f"输入 tokens: {usage_metadata.get('input_tokens')}")
    print(f"输出 tokens: {usage_metadata.get('output_tokens')}")
    print(f"总计 tokens: {usage_metadata.get('total_tokens')}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(chat("你好，请介绍一下你自己"))
