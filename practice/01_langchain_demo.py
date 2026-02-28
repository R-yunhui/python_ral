"""
langchain 示例
"""

import os
import asyncio

from dotenv import load_dotenv

# langchain 基础组件
from langchain_community.chat_models import ChatTongyi

# 加载环境变量
load_dotenv()

# 创建模型实例
chat_model = ChatTongyi(
    model=os.getenv("QWEN_CHAT_MODEL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
)


def chat_with_model(query: str):
    """
    与模型进行对话
    """
    for chunk in chat_model.stream(query):
        print(chunk.content, end="", flush=True)
    print()
    

async def chat_with_model_async(query: str):
    """
    异步与模型进行对话
    因为 chat_model.astream() 返回的是异步生成器 (async generator)
    因此需要使用 async for 来遍历
    """
    async for chunk in chat_model.astream(query):
        print(chunk.content, end="", flush=True)
    print()


if __name__ == "__main__":
    while True:
        query = input("请输入问题: ").strip()
        if query.lower() in ["exit", "quit"]:
            break
        asyncio.run(chat_with_model_async(query))
    print("再见！欢迎下次使用！")
