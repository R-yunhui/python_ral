import os
from dotenv import load_dotenv

import langsmith as ls
from langsmith import traceable
from langchain_openai import ChatOpenAI

# 加载环境变量
load_dotenv()

# 创建模型实例
llm = ChatOpenAI(
    model=os.getenv("QWEN_CHAT_MODEL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
)


@traceable
def my_llm_call(prompt: str):
    # 此处的逻辑会自动被追踪
    response = llm.invoke(prompt)
    return response.content


if __name__ == "__main__":
    content = my_llm_call("你好，请介绍一下你自己")
    print(content)
