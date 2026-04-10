import json
import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from assistant.backend.model.schemas import LLMPlan

logger = logging.getLogger(__name__)

INTENT_SYSTEM = """你是一个财务助手意图识别器。将用户输入拆解为：
- store_intents: 需要存储的意图列表（记账）
- query_intent: 需要查询的意图（查账/查预算），可为 null
- reply_strategy: 回复策略，固定 "concise_cn"

存储意图示例: amount=300, category=餐饮, description=吃饭
查询意图示例: date_range=last_week, category=餐饮, operation=sum

输出合法 JSON，不要有其他内容。"""

INTENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", INTENT_SYSTEM),
    ("user", "{message}"),
])


async def plan_from_message(message: str, llm_client: Any) -> LLMPlan:
    """调用 LLM 结构化输出双意图"""
    prompt = INTENT_PROMPT.format(message=message)
    try:
        result = await llm_client.invoke(prompt, max_tokens=500)
        data = json.loads(result)
        return LLMPlan(
            store_intents=data.get("store_intents", []),
            query_intent=data.get("query_intent"),
            reply_strategy=data.get("reply_strategy", "concise_cn"),
        )
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"LLM intent parsing failed: {e}")
        # 降级：简单规则判断
        has_query = any(k in message for k in ["看", "查询", "多少", "超预算", "总结", "分析"])
        return LLMPlan(
            store_intents=[{"type": "structured", "raw": message}] if not has_query else [],
            query_intent={"type": "structured", "raw": message} if has_query else None,
            reply_strategy="concise_cn",
        )
