# langgraph demo
import os

from dotenv import load_dotenv

# langchain 相关
from langchain_openai.chat_models import ChatOpenAI


class ChatModelService:

    def __init__(self):

        self._chat_model = None

    @property
    def chat_model(self):
        if self._chat_model is None:
            self._chat_model = ChatOpenAI(
                model=os.getenv("QWEN_CHAT_MODEL"),
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                base_url=os.getenv("DASHSCOPE_BASE_URL"),
                streaming=True,
                temperature=0.7,
                max_tokens=None,
            )
        return self._chat_model


# 全局单例
chat_model_service = ChatModelService()
