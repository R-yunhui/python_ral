import json
import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai.chat_models import ChatOpenAI
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from mem0 import AsyncMemory
from mem0.llms.configs import LlmConfig
from mem0.vector_stores.configs import VectorStoreConfig
from mem0.embeddings.configs import EmbedderConfig
from mem0.configs.base import MemoryConfig

load_dotenv()

logger = logging.getLogger(__name__)

VECTOR_STORE_SAVE_DIR = "qdrant"

# 为 True 时每轮都检索长期记忆（忽略路由）；为 False 时用 LLM 路由或正则决定是否检索
ALWAYS_SEARCH_LONG_TERM = True

# 为 True 且 ALWAYS_SEARCH_LONG_TERM 为 False 时，用 quick_chat_model 判断是否检索；为 False 则用正则启发
USE_LLM_MEMORY_ROUTER = os.getenv("MEM0_USE_LLM_MEMORY_ROUTER", "true").lower() in (
    "1",
    "true",
    "yes",
)

# 长期记忆检索条数上限（越小噪声越少）
LONG_TERM_MEMORY_LIMIT = 5

# 短期会话保留最近多少条消息（user+assistant 各算一条）
MAX_SESSION_MESSAGES = 20


class MemorySearchRouterOutput(BaseModel):
    """路由模型输出：是否需要检索 mem0 长期记忆。"""

    need_long_term_memory_search: bool = Field(
        description=(
            "若回答需要依赖用户过往偏好、身份、长期约定、历史事实等则为 true；"
            "纯百科、解题、代码、与具体用户无关的通用问答则为 false"
        )
    )


MEMORY_ROUTER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是记忆检索路由。只根据用户问题判断：回答时是否需要查询「用户长期记忆库」。\n"
            "需要检索的情况举例：涉及用户偏好/习惯/身份、指代「上次/之前/我说过」、延续个人任务。\n"
            "不需要检索的情况举例：数学/物理题、通用知识、代码怎么写、与谁在说无关的客观问题。\n"
            "只输出结构化结果，不要解释。",
        ),
        (
            "human",
            "用户当前问题：\n{query}\n\n"
            "本轮之前是否已有对话（多轮会话）：{has_session}",
        ),
    ]
)


async def _should_search_long_term_llm(
    query: str,
    session_history: list[BaseMessage],
    router_model: ChatOpenAI,
) -> bool:
    structured = router_model.with_structured_output(MemorySearchRouterOutput)
    chain = MEMORY_ROUTER_PROMPT | structured
    result = await chain.ainvoke(
        {
            "query": query.strip(),
            "has_session": "是" if session_history else "否",
        }
    )
    return result.need_long_term_memory_search


async def should_search_long_term(
    query: str,
    session_history: list[BaseMessage],
    router_model: ChatOpenAI | None,
) -> bool:
    if ALWAYS_SEARCH_LONG_TERM:
        return True
    if USE_LLM_MEMORY_ROUTER and router_model is not None:
        try:
            return await _should_search_long_term_llm(
                query, session_history, router_model
            )
        except Exception as e:
            logger.warning("LLM 记忆路由失败，回退正则: %s", e)
    return True


# chat_model（主对话，可流式）
chat_model = ChatOpenAI(
    model=os.getenv("QWEN_CHAT_MODEL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    streaming=True,
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

# 快速模型：用于记忆检索路由（非流式、低温度、短输出）
_quick_model_name = os.getenv("QWEN_CHAT_MODEL_QUICK")
quick_chat_model: ChatOpenAI | None
if _quick_model_name:
    quick_chat_model = ChatOpenAI(
        model=_quick_model_name,
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url=os.getenv("DASHSCOPE_BASE_URL"),
        streaming=False,
        extra_body={"enable_thinking": False},
        max_tokens=256,
        temperature=0,
    )
else:
    quick_chat_model = None

mem = AsyncMemory(
    config=MemoryConfig(
        embedder=EmbedderConfig(
            provider="langchain", config={"model": embedding_model}
        ),
        vector_store=VectorStoreConfig(
            provider="qdrant",
            config={
                "embedding_model_dims": 1024,
                "collection_name": "mem0",
                "path": str(Path(__file__).parent / VECTOR_STORE_SAVE_DIR),
            },
        ),
        llm=LlmConfig(provider="langchain", config={"model": chat_model}),
    ),
)

CHAT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是一个助手，请根据用户的问题与上下文作答。\n\n"
            "【与用户相关的长期记忆】（可能不完整，仅作参考）\n{long_term_context}",
        ),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ]
)


def _format_long_term(memories: list) -> str:
    if not memories:
        return "（暂无）"
    lines = []
    for i, m in enumerate(memories, 1):
        text = m.get("memory") if isinstance(m, dict) else str(m)
        if text:
            lines.append(f"{i}. {text}")
    return "\n".join(lines) if lines else "（暂无）"


async def chat(
    query: str,
    user_id: str,
    session_history: list[BaseMessage],
) -> None:
    need_search = await should_search_long_term(
        query, session_history, quick_chat_model
    )

    memories: list = []
    if need_search:
        search_result = await mem.search(
            query,
            user_id=user_id,
            limit=LONG_TERM_MEMORY_LIMIT,
        )
        memories = search_result.get("results") or []

    if memories:
        print(f"找到 {len(memories)} 条长期记忆:")
        for memory in memories:
            print(f"记忆: {json.dumps(memory, ensure_ascii=False, indent=2)}")
    else:
        if need_search:
            print("没有匹配到已有的长期记忆")
        else:
            print("本轮跳过长期记忆检索（路由判断为不需要）")

    long_term_context = _format_long_term(memories)

    chain = CHAT_PROMPT | chat_model
    ai_content = ""
    async for chunk in chain.astream(
        {
            "long_term_context": long_term_context,
            "history": session_history,
            "input": query,
        }
    ):
        ai_content += chunk.content
        print(chunk.content, end="", flush=True)
    print()

    await mem.add(
        messages=[
            {"role": "user", "content": query},
            {"role": "assistant", "content": ai_content},
        ],
        user_id=user_id,
    )

    session_history.append(HumanMessage(content=query))
    session_history.append(AIMessage(content=ai_content))
    if len(session_history) > MAX_SESSION_MESSAGES:
        del session_history[:-MAX_SESSION_MESSAGES]


if __name__ == "__main__":
    import asyncio

    if USE_LLM_MEMORY_ROUTER and quick_chat_model is None:
        print(
            "警告: 已开启 MEM0_USE_LLM_MEMORY_ROUTER，但未设置 QWEN_CHAT_MODEL_QUICK，"
            "将仅使用正则启发式判断。"
        )

    user_id = os.getenv("MEM0_DEMO_USER_ID", "demo-user")
    session_history: list[BaseMessage] = []

    query = input("请输入问题: ").strip()
    while True:
        if query.lower() in ["exit", "quit"]:
            break
        asyncio.run(chat(query, user_id, session_history))
        query = input("请输入问题: ").strip()
    print("再见！欢迎下次使用！")
