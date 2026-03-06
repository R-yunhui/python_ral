"""
毕昇工作流导入服务：封装名称生成、导入调用，并返回 flow_id、chat_url、flow_edit_url。
"""

import asyncio
import logging
import secrets
from datetime import datetime
from typing import Any

from core.bisheng_client import create_workflow_from_json

logger = logging.getLogger(__name__)

# 工作流在毕昇前端的 type 固定值
BISHENG_WORKFLOW_CHAT_TYPE = 10


def generate_chat_id() -> str:
    """生成 32 位十六进制 chat_id，与前端 generateUUID(32) 一致。"""
    return secrets.token_hex(16)  # 16 bytes -> 32 hex chars


def _import_name_with_timestamp(
    workflow: dict,
    explicit_name: str | None = None,
    metadata: dict | None = None,
) -> str:
    """生成导入用名称（带时间戳）。优先：显式名称 > workflow.name > metadata.intent.rewritten_input > 默认。"""
    base = explicit_name or workflow.get("name")
    if not base and metadata and isinstance(metadata, dict):
        intent = metadata.get("intent")
        if isinstance(intent, dict) and intent.get("rewritten_input"):
            base = (intent["rewritten_input"] or "")[:50]
    base = base or "导入的工作流"
    return f"{base}_{datetime.now().strftime('%Y%m%d%H%M%S')}"


async def _import_workflow_to_bisheng(
    base_url: str,
    token: str,
    workflow: dict,
    name: str | None = None,
    description: str = "",
    publish: bool = True,
) -> dict:
    """
    将工作流 JSON 导入到毕昇平台（异步封装）。
    返回 dict 包含 flow_id, version_id, published, chat_url, flow_edit_url。
    """
    if not token:
        raise ValueError("无法导入：请在前端登录或携带 Cookie access_token_cookie")
    name = name or workflow.get("name") or "导入的工作流"
    description = description or workflow.get("description") or ""

    def _do_import() -> dict:
        return create_workflow_from_json(
            base_url=base_url,
            token=token,
            flow_data=workflow,
            name=name,
            description=description,
            publish=publish,
        )

    result: dict[str, Any] = await asyncio.to_thread(_do_import)
    flow_id = result.get("flow_id")
    if flow_id:
        base = base_url.rstrip("/")
        result["flow_edit_url"] = f"{base}/flow/{flow_id}"
        chat_id = generate_chat_id()
        result["chat_url"] = f"{base}/workspace/chat/{chat_id}/{flow_id}/{BISHENG_WORKFLOW_CHAT_TYPE}"
    return result


async def do_import_workflow(
    workflow: dict,
    base_url: str,
    token: str,
    *,
    explicit_name: str | None = None,
    metadata: dict | None = None,
    publish: bool = True,
) -> dict:
    """
    统一执行导入：计算名称（带时间戳）并调用毕昇导入。
    返回 dict 包含 flow_id, version_id, published, chat_url, flow_edit_url。
    失败抛异常。
    """
    name = _import_name_with_timestamp(
        workflow, explicit_name=explicit_name, metadata=metadata
    )
    logger.info("导入工作流名称：%s", name)
    return await _import_workflow_to_bisheng(
        base_url=base_url,
        token=token,
        workflow=workflow,
        name=name,
        publish=publish,
    )
