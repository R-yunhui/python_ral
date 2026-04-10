import os

from dotenv import load_dotenv

# 使用 chain 进行调用
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai.chat_models import ChatOpenAI

load_dotenv()

chat_model = ChatOpenAI(
    model=os.getenv("QWEN_CHAT_MODEL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    streaming=True,
)


async def chat(query: str):

    rewrite_prompt = ChatPromptTemplate.from_template(
        "把用户问题改写成适合检索的一句话，只输出改写结果：\n{query}"
    )

    answer_prompt = ChatPromptTemplate.from_template(
        "根据检索改写：{rewritten}\n\n请直接回答用户原始问题。"
    )

    # LCEL 链式编排：query -> 改写 -> 回答
    chain = (
        {"rewritten": rewrite_prompt | chat_model, "query": lambda x: x["query"]}
        | answer_prompt
        | chat_model
    )

    # 同步调用
    result = chain.invoke({"query": query})
    print(f"[同步] {query} => {result.content}")


async def chat_stream(query: str):
    """流式输出 demo"""

    prompt = ChatPromptTemplate.from_template(
        "你是一位知识渊博的助手。请用中文回答用户的问题。\n\n" "用户问题：{query}"
    )

    chain = prompt | chat_model | (lambda msg: msg.content)

    async for chunk in chain.astream({"query": query}):
        print(chunk, end="", flush=True)
    print()


if __name__ == "__main__":
    import asyncio

    question = "什么是 LangChain 的 LCEL？"

    print("=== 同步链式调用 ===")
    asyncio.run(chat(question))

    print("\n=== 流式调用 ===")
    asyncio.run(chat_stream(question))
