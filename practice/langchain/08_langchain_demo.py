import os

from dotenv import load_dotenv


from langchain_openai.chat_models import ChatOpenAI
from langchain_community.chat_models import ChatTongyi

load_dotenv()

chat_model = ChatOpenAI(
    model=os.getenv("QWEN_CHAT_MODEL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    streaming=True,
    extra_body={
        "enable_thinking": True,
        "thinking_budget": 100,
    },
)

qwen_model = ChatTongyi(
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
        "thinking_budget": 100,
    },
)

def chat_with_model(query: str):
    print("--- 开始请求 ---")
    for chunk in qwen_model.stream(query):
        # 1. 打印思考过程 (Reasoning)
        # 检查是否在 additional_kwargs 中有 reasoning_content
        reasoning = chunk.additional_kwargs.get("reasoning_content")
        if reasoning:
            print(reasoning, end="", flush=True)

        # 2. 检查 Qwen 模型特有的 'thought' 字段 (有些版本会放在这里)
        thought = chunk.additional_kwargs.get("thought")
        if thought:
            print(thought, end="", flush=True)

        # 3. 打印最终回答 (Content)
        if chunk.content:
            print(chunk.content, end="", flush=True)

    print("\n--- 请求结束 ---")


if __name__ == "__main__":
    chat_with_model("你好，我是小明，请介绍一下你自己。")
