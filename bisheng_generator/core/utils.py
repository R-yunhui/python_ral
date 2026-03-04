import json
import re
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Optional: httpx may be used by agents for HTTP calls
try:
    import httpx
except ImportError:
    httpx = None  # type: ignore


def is_retryable(e: Exception) -> bool:
    """
    判断异常是否可重试（网络、超时、解析等临时性错误）。
    用于容错降级：可重试则重试，否则由调用方决定是否降级或报错。
    """
    if isinstance(e, json.JSONDecodeError):
        return True
    if httpx is not None:
        if isinstance(e, (httpx.TimeoutException, httpx.RequestError)):
            return True
        if isinstance(e, httpx.HTTPStatusError):
            if e.response is not None and e.response.status_code >= 500:
                return True
    # 其他异常（如 LLM 返回异常、通用网络错误）视为可重试
    if isinstance(e, (KeyboardInterrupt, SystemExit)):
        return False
    return True


def extract_json(content: str) -> Optional[Dict[str, Any]]:
    """
    从字符串中提取并解析 JSON。
    支持从 ```json ... ``` 代码块中提取。
    """
    if not content or not content.strip():
        return None

    # 1. 尝试直接解析
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        pass

    # 2. 尝试正则提取代码块
    # 优先匹配 ```json ... ```
    json_block = re.search(r"```json\s*([\s\S]*?)```", content)
    if not json_block:
        # 尝试匹配普通的 ``` ... ```
        json_block = re.search(r"```\s*([\s\S]*?)```", content)

    if json_block:
        json_str = json_block.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning(f"从代码块提取的字符串解析 JSON 失败: {json_str[:100]}...")

    # 3. 实在没有匹配到，尝试查找第一个 { 和最后一个 }
    try:
        start_idx = content.find("{")
        end_idx = content.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = content[start_idx : end_idx + 1]
            return json.loads(json_str)
    except Exception:
        pass

    return None
