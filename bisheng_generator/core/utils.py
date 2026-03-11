import json
import re
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _mermaid_sanitize_id(node_id: str) -> str:
    """将节点 ID 转为 Mermaid 可用的标识（字母数字下划线）。"""
    if not node_id:
        return "n"
    s = re.sub(r"[^a-zA-Z0-9_]", "_", str(node_id))
    return s if s else "n"


# Mermaid 11.x 在 flowchart 节点/边标签中会解析 ] [ | " 等，需替换为安全字符
_MERMAID_LABEL_UNSAFE = re.compile(r'[\]\[|"#;:{}\\]')
_MERMAID_BRANCH_UNSAFE = re.compile(r'[|\[\]#;:{}]')

# 控制字符与不可见字符（保留 \t \n \r，其余 strip 掉，避免渲染失败）
_MERMAID_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ufeff]")

# 各类引号、弯引号统一为单引号，避免破坏 "label" 边界
_MERMAID_QUOTE_CHARS = re.compile(r'["\u201c\u201d\u201e\u201f\u2039\u203a]')


def _mermaid_normalize_text(s: str) -> str:
    """去掉控制/不可见字符，弯引号统一为直单引号。"""
    s = _MERMAID_CONTROL_CHARS.sub("", str(s))
    s = _MERMAID_QUOTE_CHARS.sub("'", s)
    return s


def _mermaid_escape_label(text: str, max_len: int = 50) -> str:
    """将节点标签转为 Mermaid 安全文本（避免 Syntax error in text）。"""
    s = _mermaid_normalize_text(str(text)).strip() or ""
    s = s.replace("\\", "\\\\").replace('"', "'").replace("\n", " ").replace("\r", " ")
    s = _MERMAID_LABEL_UNSAFE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:max_len] if s else " "


def _mermaid_escape_branch(text: str, max_len: int = 30) -> str:
    """将边 branch 转为 Mermaid 安全文本（-->|...| 中不能含 | 等）。"""
    s = _mermaid_normalize_text(str(text)).strip() or ""
    s = s.replace('"', "'").replace("\n", " ").replace("\r", " ")
    s = _MERMAID_BRANCH_UNSAFE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:max_len] if s else " "


def sketch_to_mermaid(sketch: Dict[str, Any]) -> str:
    """
    将流程图草图（nodes + edges）转为 Mermaid flowchart 字符串，供前端渲染。
    失败时返回空字符串。
    """
    if not sketch or not isinstance(sketch, dict):
        return ""
    nodes = sketch.get("nodes")
    edges = sketch.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return ""
    id_to_safe: Dict[str, str] = {}
    for n in nodes:
        nid = n.get("id") if isinstance(n, dict) else None
        if nid is not None and nid not in id_to_safe:
            id_to_safe[nid] = _mermaid_sanitize_id(nid)
    lines: List[str] = ["flowchart TB"]
    for n in nodes:
        if not isinstance(n, dict):
            continue
        nid = n.get("id")
        if nid is None:
            continue
        safe = id_to_safe.get(nid, _mermaid_sanitize_id(nid))
        label = (n.get("label") or n.get("type") or nid).strip()
        if not label:
            label = nid
        label_esc = _mermaid_escape_label(label, 50)
        lines.append(f'    {safe}["{label_esc}"]')
    for e in edges:
        if not isinstance(e, dict):
            continue
        src = e.get("source")
        tgt = e.get("target")
        if not src or not tgt:
            continue
        safe_src = id_to_safe.get(src, _mermaid_sanitize_id(src))
        safe_tgt = id_to_safe.get(tgt, _mermaid_sanitize_id(tgt))
        branch = e.get("branch")
        if branch and str(branch).strip():
            branch_esc = _mermaid_escape_branch(branch, 30)
            lines.append(f"    {safe_src} -->|{branch_esc}| {safe_tgt}")
        else:
            lines.append(f"    {safe_src} --> {safe_tgt}")
    return "\n".join(lines)

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
    except json.JSONDecodeError as e:
        logger.debug("直接解析 JSON 失败: %s", e)

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
    except Exception as e:
        logger.debug("从首尾括号提取 JSON 失败: %s", e)

    return None
