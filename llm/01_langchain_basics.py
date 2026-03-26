"""LangChain 最小示例：Prompt -> Model -> Parser."""

from __future__ import annotations

import os

from langchain.chat_models import init_chat_model
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


def build_model():
    """默认离线假模型；设置 USE_REAL_LLM=1 后切到 OpenAI."""
    if os.getenv("USE_REAL_LLM") == "1":
        return init_chat_model("openai:gpt-4.1-mini", temperature=0)
    return FakeListChatModel(
        responses=[
            "LangChain 可以把 Prompt、模型、工具、记忆等模块像积木一样组合起来。",
        ]
    )


def main() -> None:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "你是一个简洁、友好的 AI 助手。"),
            ("human", "请用两句话解释什么是 {topic}。"),
        ]
    )
    model = build_model()
    parser = StrOutputParser()

    chain = prompt | model | parser
    result = chain.invoke({"topic": "LangChain"})

    print("=== LangChain 基础链路 ===")
    print(result)


if __name__ == "__main__":
    main()
