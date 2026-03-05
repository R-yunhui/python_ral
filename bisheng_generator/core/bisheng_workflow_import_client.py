#!/usr/bin/env python3
"""
毕昇工作流导入客户端 — 从外部 Python 服务调用毕昇 API，将 JSON 工作流导入并发布上线。

用法一（已有 token，如从 cookie 获取）:
    from bisheng_workflow_import_client import create_workflow_from_json

    token = "从 cookie 里取到的 access_token"
    result = create_workflow_from_json(
        base_url="http://localhost:7860",
        token=token,
        flow_data="/path/to/workflow.json",  # 或 flow_data=flow_dict
        name="我的工作流",   # 可选
        publish=True,
    )
    print(result["flow_id"], result["version_id"])

用法二（用账号密码先登录）:
    from bisheng_workflow_import_client import import_workflow_and_publish
    result = import_workflow_and_publish(base_url=..., user_name=..., password=..., flow_data=...)
"""

from __future__ import annotations
from datetime import datetime

import hashlib
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any


def _md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


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


def login(base_url: str, user_name: str, password: str) -> str:
    """
    登录毕昇，获取 access_token。
    若毕昇未配置 RSA 加密，可直接传明文密码，后端会做 MD5。
    """
    url = base_url.rstrip("/") + "/api/v1/user/login"
    # 毕昇后端在无 RSA 时会对密码做 MD5，这里传明文即可
    payload = {"user_name": user_name, "password": password}
    out = _request("POST", url, data=payload)
    data = out.get("data") or out
    token = data.get("access_token")
    if not token:
        raise RuntimeError("登录响应中无 access_token")
    return token


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
    与前端导出格式一致：顶层可有 nodes, edges, viewport, name, description。
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
    """
    将指定版本设为上线。status=2 表示上线，1 表示下线。
    """
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
    用已有 token（如从 cookie 里取的）直接创建毕昇工作流，无需登录。

    :param base_url: 毕昇服务地址，如 http://localhost:7860
    :param token: 从 cookie 或其它方式拿到的 access_token（Bearer 用的那个）
    :param flow_data: 完整工作流 JSON 字典，或 .json 文件路径。需含 nodes、edges，可选 viewport、name、description
    :param name: 工作流名称，不传则用 flow_data 里的 name 或默认「导入的工作流」
    :param description: 工作流描述
    :param logo: 工作流 logo 相对路径，可选
    :param publish: 是否创建后立即上线
    :return: {"flow_id": "...", "version_id": int, "published": bool}
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


def import_workflow_and_publish(
    base_url: str,
    user_name: str,
    password: str,
    flow_data: dict | str | Path,
    name: str | None = None,
    description: str = "",
    publish: bool = True,
) -> dict:
    """
    从 JSON 导入工作流并可选发布上线。供其它 Python 服务调用。

    :param base_url: 毕昇服务地址，如 http://localhost:7860
    :param user_name: 登录用户名
    :param password: 登录密码（明文，后端无 RSA 时会做 MD5）
    :param flow_data: 工作流 JSON 字典，或 JSON 文件路径。需含 nodes、edges，可选 viewport、name、description
    :param name: 工作流名称，不传则用 flow_data 中的 name 或默认「导入的工作流」
    :param description: 工作流描述
    :param publish: 是否创建后立即上线
    :return: {"flow_id": "...", "version_id": int, "published": bool}
    """
    if not isinstance(flow_data, dict):
        with open(flow_data, "r", encoding="utf-8") as f:
            flow_data = json.load(f)
    name = name or flow_data.get("name") or "导入的工作流"
    description = description or flow_data.get("description") or ""
    token = login(base_url, user_name, password)
    created = create_workflow(
        base_url=base_url,
        token=token,
        name=name,
        flow_data=flow_data,
        description=description,
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


def main():
    output_dir = Path(__file__).parent.parent.parent / "output"
    workflow_files = sorted(
        output_dir.glob("workflow_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not workflow_files:
        raise FileNotFoundError(
            f"未找到工作流 JSON，请先在 {output_dir} 下放置 workflow_*.json"
        )
    workflow_json = workflow_files[0]

    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ7XCJ1c2VyX2lkXCI6IDEsIFwidXNlcl9uYW1lXCI6IFwiYWRtaW5cIn0iLCJleHAiOjE3NzI3NjU2NDIsImlzcyI6ImJpc2hlbmcifQ.zL9wMJPK4gXHhUy9JxwBe7xcQvpQNTSibfTmSvEcjc8"
    result = create_workflow_from_json(
        base_url="http://192.168.2.137:3001",
        token=token,
        flow_data=workflow_json,  # 或 flow_data=flow_dict
        name=f"测试工作流 {datetime.now().strftime('%Y%m%d%H%M%S')}",  # 可选
        publish=True,
    )
    print(result["flow_id"], result["version_id"])

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
