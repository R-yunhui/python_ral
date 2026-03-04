import json
import re
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


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
