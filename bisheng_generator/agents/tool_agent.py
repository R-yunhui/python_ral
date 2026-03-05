"""
工具选择 Agent

职责：
1. 调用 mcp-search 接口检索匹配的 MCP 工具（接口已封装大模型筛选 + 向量检索）
2. 将接口返回的工具转换为 ToolDefinition
3. 生成 ToolPlan 供下游工作流生成使用
"""

import logging
from typing import List, Dict, Any, Optional

import httpx
from pydantic import BaseModel, Field

from models.intent import EnhancedIntent

logger = logging.getLogger(__name__)


class ToolDefinition(BaseModel):
    """工具定义"""

    id: Optional[int] = Field(default=None, description="工具 ID")
    name: str = Field(..., description="工具名称")
    tool_key: str = Field(..., description="工具唯一标识")
    desc: str = Field(..., description="工具描述")
    logo: Optional[str] = Field(default=None, description="工具 logo")
    parameters: List[Dict[str, Any]] = Field(
        default_factory=list, description="工具参数列表"
    )
    extra: Optional[Dict[str, Any]] = Field(default=None, description="额外配置信息")

    def to_schema(self) -> Dict[str, Any]:
        """转换为 LLM 可调用的 schema 格式"""
        return {
            "name": self.tool_key,
            "description": self.desc,
            "parameters": {
                "type": "object",
                "properties": {
                    param.get("name", ""): {
                        "type": param.get("type", "string"),
                        "description": param.get("description", ""),
                    }
                    for param in self.parameters
                },
                "required": [
                    p.get("name") for p in self.parameters if p.get("required", False)
                ],
            },
        }


class ToolPlan(BaseModel):
    """工具选择计划"""

    selected_tools: List[ToolDefinition] = Field(
        default_factory=list, description="选中的工具列表"
    )
    parameters_mapping: Dict[str, str] = Field(
        default_factory=dict, description="参数映射：工具参数 -> 节点变量"
    )
    dependencies: List[tuple] = Field(default_factory=list, description="工具依赖关系")
    execution_order: List[str] = Field(default_factory=list, description="执行顺序")
    reasoning: str = Field(default="", description="选择这些工具的理由")


class ToolAgent:
    """工具选择专家 —— 通过 mcp-search 接口检索工具"""

    def __init__(self, mcp_search_url: str, mcp_search_top_k: int = 10):
        self.mcp_search_url = mcp_search_url.rstrip("/")
        self.mcp_search_top_k = mcp_search_top_k

    async def select_tools(self, intent: EnhancedIntent) -> ToolPlan:
        """
        根据意图调用 mcp-search 接口检索匹配的工具

        Args:
            intent: 用户意图描述

        Returns:
            ToolPlan: 工具选择计划
        """
        if not intent.needs_tool:
            logger.info("工具选择跳过，needs_tool=false")
            return ToolPlan(selected_tools=[], reasoning="用户需求不需要调用外部工具")

        query = intent.rewritten_input or intent.original_input
        tools = await self._search_mcp_tools(query)

        if not tools:
            logger.info("工具选择完成，mcp-search 返回 0 个匹配工具")
            return ToolPlan(selected_tools=[], reasoning="未找到与用户需求匹配的工具")

        execution_order = [t.tool_key for t in tools]
        logger.info("工具选择完成，count=%s, keys=%s", len(tools), execution_order)

        return ToolPlan(
            selected_tools=tools,
            parameters_mapping={},
            dependencies=[],
            execution_order=execution_order,
            reasoning=f"mcp-search 接口返回 {len(tools)} 个匹配工具",
        )

    async def _search_mcp_tools(self, query: str) -> List[ToolDefinition]:
        """
        调用 mcp-search 接口

        Args:
            query: 搜索关键词

        Returns:
            匹配的工具列表
        """
        payload = {"query": query, "top_k": str(self.mcp_search_top_k)}
        logger.info("调用 mcp-search，url=%s, query=%s, top_k=%s",
                     self.mcp_search_url, query, self.mcp_search_top_k)

        try:
            async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
                resp = await client.post(self.mcp_search_url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("mcp-search 请求失败，status=%s, body=%s",
                         e.response.status_code, e.response.text[:500], exc_info=True)
            return []
        except Exception as e:
            logger.error("mcp-search 请求异常: %s", e, exc_info=True)
            return []

        servers = data if isinstance(data, list) else data.get("value", [])
        logger.info("mcp-search 返回工具列表数量: %s", len(servers))
        return self._parse_servers(servers)

    @staticmethod
    def _parse_servers(servers: List[Dict[str, Any]]) -> List[ToolDefinition]:
        """
        将 mcp-search 返回的 server 列表（含 children 工具）转换为 ToolDefinition 列表
        """
        tools: List[ToolDefinition] = []

        for server in servers:
            server_id = server.get("server_id", "")
            openapi_schema = server.get("openapi_schema", "")
            connection_type = server.get("connection_type", "")
            server_name = server.get("name", "")
            score = server.get("score", 0.0)

            for child in server.get("children", []):
                params = _convert_api_params(child.get("api_params", []))

                tool = ToolDefinition(
                    id=child.get("id"),
                    name=child.get("name", ""),
                    tool_key=child.get("tool_key", ""),
                    desc=child.get("desc", ""),
                    logo=child.get("logo"),
                    parameters=params,
                    extra={
                        "server_id": server_id,
                        "server_name": server_name,
                        "openapi_schema": openapi_schema,
                        "connection_type": connection_type,
                        "score": score,
                        "child_extra": child.get("extra"),
                    },
                )
                tools.append(tool)

        return tools


def _convert_api_params(api_params: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """将 mcp-search 返回的 api_params 格式转换为 ToolDefinition.parameters 格式"""
    result = []
    for p in api_params:
        schema = p.get("schema", {})
        result.append({
            "name": p.get("name", ""),
            "type": schema.get("type", "string") if isinstance(schema, dict) else "string",
            "description": p.get("description", ""),
            "required": p.get("required", False),
        })
    return result
