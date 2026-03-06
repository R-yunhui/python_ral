"""
毕昇工作流 API 客户端：用已有 token 将 JSON 工作流导入并发布。

用法:
    from core.bisheng_client import create_workflow_from_json

    result = create_workflow_from_json(
        base_url="http://localhost:3001",
        token=token,
        flow_data=flow_dict,  # 或 .json 文件路径
        name="我的工作流",
        publish=True,
    )
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any


def _request(
    method: str,
    url: str,
    data: dict | None = None,
    token: str | None = None,
    json_body: bool = True,
) -> dict:
    headers = {"Content-Type": "application/json"} if json_body else {}
    if token:
        headers["Cookie"] = f"lang=zh-Hans; access_token_cookie={token}"
    body = json.dumps(data).encode("utf-8") if (data and json_body) else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            out = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        try:
            err = json.loads(body)
            msg = err.get("status_message") or err.get("detail") or body
        except Exception:
            msg = body
        raise RuntimeError(f"HTTP {e.code}: {msg}") from e
    if out.get("status_code") != 200:
        raise RuntimeError(
            out.get("status_message") or out.get("detail") or json.dumps(out)
        )
    return out


def create_workflow(
    base_url: str,
    token: str,
    name: str,
    flow_data: dict,
    description: str = "",
    logo: str = "",
) -> dict:
    """
    创建工作流。flow_data 需包含 nodes、edges，可选 viewport。
    """
    url = base_url.rstrip("/") + "/api/v1/workflow/create"
    nodes = flow_data.get("nodes")
    edges = flow_data.get("edges")
    if not nodes or not isinstance(nodes, list):
        raise ValueError("flow_data 必须包含 nodes 数组")
    if not edges or not isinstance(edges, list):
        raise ValueError("flow_data 必须包含 edges 数组")
    viewport = flow_data.get("viewport")
    payload = {
        "name": name,
        "description": description or "",
        "logo": logo or "",
        "data": {
            "nodes": nodes,
            "edges": edges,
        },
    }
    if viewport is not None:
        payload["data"]["viewport"] = viewport
    out = _request("POST", url, data=payload, token=token)
    data = out.get("data") or out
    return {"id": data["id"], "version_id": data.get("version_id")}


def publish_workflow(
    base_url: str,
    token: str,
    flow_id: str,
    version_id: int,
    status: int = 2,
) -> None:
    """将指定版本设为上线。status=2 表示上线，1 表示下线。"""
    url = base_url.rstrip("/") + "/api/v1/workflow/status"
    payload = {
        "flow_id": flow_id,
        "version_id": version_id,
        "status": status,
    }
    _request("PATCH", url, data=payload, token=token)


def create_workflow_from_json(
    base_url: str,
    token: str,
    flow_data: dict | str | Path,
    name: str | None = None,
    description: str = "",
    logo: str = "",
    publish: bool = True,
) -> dict:
    """
    用已有 token 直接创建毕昇工作流，可选发布上线。

    :param base_url: 毕昇服务地址
    :param token: access_token（如从 cookie 获取）
    :param flow_data: 工作流 JSON 字典或 .json 文件路径，需含 nodes、edges
    :param name: 工作流名称，不传则用 flow_data 里的 name 或默认「导入的工作流」
    :param description: 工作流描述
    :param logo: 工作流 logo，可选
    :param publish: 是否创建后立即上线
    :return: {"flow_id": str, "version_id": int | None, "published": bool}
    """
    if not isinstance(flow_data, dict):
        with open(flow_data, "r", encoding="utf-8") as f:
            flow_data = json.load(f)
    name = name or flow_data.get("name") or "导入的工作流"
    description = description or flow_data.get("description") or ""
    logo = logo or flow_data.get("logo") or ""
    created = create_workflow(
        base_url=base_url,
        token=token,
        name=name,
        flow_data=flow_data,
        description=description,
        logo=logo,
    )
    flow_id = created["id"]
    version_id = created.get("version_id")
    if publish and version_id is not None:
        publish_workflow(base_url, token, flow_id, version_id, status=2)
    return {
        "flow_id": flow_id,
        "version_id": version_id,
        "published": publish and version_id is not None,
    }
