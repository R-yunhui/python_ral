import os

from dotenv import load_dotenv
from pathlib import Path

# langchain 相关
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_openai.chat_models import ChatOpenAI
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage

# mem0
from mem0 import Memory, AsyncMemory
from mem0.llms.configs import LlmConfig
from mem0.vector_stores.configs import VectorStoreConfig
from mem0.embeddings.configs import EmbedderConfig
from mem0.configs.base import MemoryConfig

# 加载环境变量
load_dotenv()

VECTOR_STORE_SAVE_DIR = "qdrant"

# chat_model
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
        "enable_thinking": True,
        "thinking_budget": 100,
    },
    max_tokens=None,
    temperature=0.7,
)

embedding_model = DashScopeEmbeddings(
    model=os.getenv("EMBEDDING_MODEL", "text-embedding-v3"),
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
)

# Memory
mem = AsyncMemory(
    config=MemoryConfig(
        embedder=EmbedderConfig(
            provider="langchain", config={"model": embedding_model}
        ),
        vector_store=VectorStoreConfig(
            provider="qdrant",
            config={
                "embedding_model_dims": 1024,  # embedding 模型向量维度
                "collection_name": "mem0",
                "path": str(
                    Path(__file__).parent / VECTOR_STORE_SAVE_DIR
                ),  # mem0 默认使用本地存储向量，路径为 /tmp/qdrant
            },
        ),
        llm=LlmConfig(provider="langchain", config={"model": chat_model}),
    ),
)


async def chat(query: str, user_id: str):
    import json 
    
    memories = await mem._search_vector_store(query, filters={"user_id": user_id}, limit=10)
    if memories:
        print(f"找到 {len(memories)} 条记忆, 记忆如下:")
        for memory in memories:
            print(f"记忆: {json.dumps(memory, ensure_ascii=False, indent=2)}")
    else:
        print("没有匹配到已有的记忆")
        memories = []

    chat_prompt_template =ChatPromptTemplate.from_messages([
        SystemMessage(content="你是一个助手，请根据用户的问题，给出回答。"),
        MessagesPlaceholder(variable_name="history"),
        HumanMessage(content=query),
    ])
    
    memory_messages = [
        HumanMessage(content=memory.get("memory", None)) for memory in memories
    ]

    formatted_messages = chat_prompt_template.format_messages(
        history=memory_messages,
    )
    
    chain = chat_prompt_template | chat_model
        
    ai_content = ""
    async for chunk in chain.astream(input=formatted_messages):
        ai_content += chunk.content
        print(chunk.content, end="", flush=True)
    print()

    # 存储记忆
    await mem.add(
        messages=[
                {
                    "role": "user",
                    "content": query,
                },
            ],
        user_id=user_id,
    )


if __name__ == "__main__":
    import asyncio
    import uuid

    user_id = str(uuid.uuid4())

    query = input("请输入问题: ").strip()
    while True:
        if query.lower() in ["exit", "quit"]:
            break
        asyncio.run(chat(query, user_id))
        query = input("请输入问题: ").strip()
    print("再见！欢迎下次使用！")
