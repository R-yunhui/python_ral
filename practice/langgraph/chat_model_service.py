# langgraph demo
import os

from dotenv import load_dotenv

# langchain 相关
from langchain_openai.chat_models import ChatOpenAI


class ChatModelService:

    def __init__(self):

        self._chat_model = None

        self._chat_model_flash = None

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
                extra_body={
                    "enable_thinking": True,
                    "thinking_budget": 500,
                },
                model_kwargs={
                    "stream_options": {
                        "include_usage": True,
                    },
                },
            )
        return self._chat_model

    @property
    def chat_model_flash(self):
        if self._chat_model_flash is None:
            self._chat_model_flash = ChatOpenAI(
                model=os.getenv("QWEN_CHAT_MODEL_QUICK"),
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                base_url=os.getenv("DASHSCOPE_BASE_URL"),
                streaming=True,
                temperature=0.7,
                max_tokens=None,
                extra_body={
                    "enable_thinking": False,
                },
                model_kwargs={
                    "stream_options": {
                        "include_usage": True,
                    },
                },
            )
        return self._chat_model_flash


# 全局单例
chat_model_service = ChatModelService()
