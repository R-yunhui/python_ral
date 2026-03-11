"""LangGraph MySQL Checkpointer 连接与 URI 构建

当 config.is_mysql_configured() 为真时，使用 langgraph-checkpoint-mysql 的
AsyncMySaver 持久化 checkpoint；未配置时由调用方回退到 InMemorySaver。
"""

import logging
from typing import TYPE_CHECKING, Optional, Sequence, Tuple
from urllib.parse import quote_plus

if TYPE_CHECKING:
    from config.config import Config

logger = logging.getLogger(__name__)

# JSON 反序列化：value["id"] 为 (module_parts..., class_name)
ALLOWED_JSON_MODULES: Sequence[Tuple[str, ...]] = (
    ("models", "intent", "EnhancedIntent"),
    ("agents", "tool_agent", "ToolPlan"),
    ("agents", "knowledge_agent", "KnowledgeMatch"),
)

# Msgpack 反序列化：_check_allowed(module, name) 使用 (dotted_module, class_name) 二元组
ALLOWED_MSGPACK_MODULES: Sequence[Tuple[str, str]] = (
    ("models.intent", "EnhancedIntent"),
    ("agents.tool_agent", "ToolPlan"),
    ("agents.knowledge_agent", "KnowledgeMatch"),
)


def make_checkpoint_serde():
    """创建用于 AsyncMySaver 的 JsonPlusSerializer，注册本应用在 checkpoint 中使用的类型，消除反序列化警告。"""
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
    return JsonPlusSerializer(
        allowed_json_modules=list(ALLOWED_JSON_MODULES),
        allowed_msgpack_modules=list(ALLOWED_MSGPACK_MODULES),
    )


def build_mysql_checkpoint_uri(config: "Config") -> Optional[str]:
    """
    从 Config 构建 langgraph-checkpoint-mysql 使用的 MySQL URI。

    格式：mysql://{user}:{password}@{host}:{port}/{database}
    注意：不要加 pymysql 等驱动前缀，langgraph-checkpoint-mysql 内部按 extra 选择驱动。

    Returns:
        已配置 MySQL 时返回 URI，否则返回 None。
    """
    if not config.is_mysql_configured():
        return None
    password = quote_plus(config.mysql_password) if config.mysql_password else ""
    return (
        f"mysql://{config.mysql_user}:{password}"
        f"@{config.mysql_host}:{config.mysql_port}/{config.mysql_database}"
    )
