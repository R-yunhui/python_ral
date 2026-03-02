"""
MCP (Model Context Protocol) 服务
通过 langchain-mcp-adapters 接入外部 MCP 服务器，获取 tools

功能：
1. 支持连接多个 MCP 服务器（stdio, http, websocket 等）
2. 加载 MCP 工具为 LangChain 工具
3. 提供工具调用接口
4. 支持动态添加/移除 MCP 服务器连接
"""

import os
import sys
import asyncio
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool

from rag.utils.logger import get_logger

logger = get_logger(__name__)
load_dotenv()


class MCPService:
    """
    MCP 服务类

    用于管理 MCP 服务器连接和工具加载
    """

    def __init__(self):
        """初始化 MCP 服务"""
        self.client: Optional[MultiServerMCPClient] = None
        self.tools: List[BaseTool] = []
        self.server_configs: Dict[str, Dict[str, Any]] = {}
        logger.info("MCP 服务初始化完成")

    def add_server(
        self,
        name: str,
        transport: str = "stdio",
        url: Optional[str] = None,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        添加 MCP 服务器连接配置

        Args:
            name: 服务器名称标识
            transport: 传输方式 ('stdio', 'http', 'sse', 'websocket', 'streamable_http')
            url: HTTP 传输时的服务器 URL
            command: stdio 传输时的命令
            args: stdio 传输时的命令参数
            headers: HTTP headers（用于认证等）
        """
        config = {
            "transport": transport,
        }

        if transport in ["http", "sse", "websocket", "streamable_http"]:
            if not url:
                raise ValueError(f"HTTP 传输需要提供 URL")
            config["url"] = url
            if headers:
                config["headers"] = headers

        elif transport == "stdio":
            if not command:
                raise ValueError(f"stdio 传输需要提供 command")
            config["command"] = command
            if args:
                config["args"] = args

        self.server_configs[name] = config
        logger.info(f"添加 MCP 服务器配置：{name}, transport={transport}")

    def remove_server(self, name: str):
        """
        移除 MCP 服务器连接

        Args:
            name: 服务器名称标识
        """
        if name in self.server_configs:
            del self.server_configs[name]
            logger.info(f"移除 MCP 服务器：{name}")
        else:
            logger.warning(f"MCP 服务器不存在：{name}")

    async def connect(self):
        """
        连接到所有配置的 MCP 服务器并加载工具

        Returns:
            加载的工具列表
        """
        if not self.server_configs:
            logger.warning("没有配置的 MCP 服务器")
            return []

        try:
            logger.info(f"开始连接 {len(self.server_configs)} 个 MCP 服务器...")

            # 创建 MultiServerMCPClient
            self.client = MultiServerMCPClient(self.server_configs)

            # 加载所有工具
            self.tools = await self.client.get_tools()

            logger.info(f"成功加载 {len(self.tools)} 个 MCP 工具")
            for tool in self.tools:
                logger.info(f"  - {tool.name}: {tool.description[:100]}")

            return self.tools

        except Exception as e:
            logger.error(f"连接 MCP 服务器失败：{e}", exc_info=True)
            raise

    async def disconnect(self):
        """断开与所有 MCP 服务器的连接"""
        if self.client:
            # 注意：langchain-mcp-adapters 的 MultiServerMCPClient
            # 可能需要手动清理资源
            logger.info("断开 MCP 服务器连接")
            self.client = None
            self.tools = []

    def get_tools(self) -> List[BaseTool]:
        """
        获取已加载的工具列表

        Returns:
            工具列表
        """
        return self.tools

    def get_tool_by_name(self, name: str) -> Optional[BaseTool]:
        """
        根据名称获取工具

        Args:
            name: 工具名称

        Returns:
            工具对象，如果不存在则返回 None
        """
        for tool in self.tools:
            if tool.name == name:
                return tool
        logger.warning(f"工具不存在：{name}")
        return None

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        列出所有可用工具的信息

        Returns:
            工具信息列表
        """
        tool_info = []
        for tool in self.tools:
            info = {
                "name": tool.name,
                "description": tool.description,
                "args_schema": tool.args_schema.schema() if tool.args_schema else None,
            }
            tool_info.append(info)
        return tool_info


# ==================== 全局服务实例 ====================

# 创建全局 MCP 服务实例
mcp_service = MCPService()


# ==================== 便捷函数 ====================


async def init_mcp_service():
    """
    初始化 MCP 服务（从环境变量加载配置）

    环境变量格式:
    - MCP_SERVER_1_NAME: 服务器 1 名称
    - MCP_SERVER_1_TRANSPORT: 传输方式
    - MCP_SERVER_1_URL: HTTP 传输的 URL
    - MCP_SERVER_1_COMMAND: stdio 传输的命令
    - MCP_SERVER_1_ARGS: stdio 传输的参数（JSON 数组）
    """
    logger.info("初始化 MCP 服务...")

    # 从环境变量加载配置
    # 示例：配置 Bocha 网络搜索
    bocha_api_key = os.getenv("BOCHA_WEB_SEARCH_API_KEY")
    if bocha_api_key:
        mcp_service.add_server(
            name="bocha_web_search",
            transport="streamable_http",
            url="https://mcp.bochaai.com/mcp",
            headers={
                "Authorization": f"Bearer {bocha_api_key}",
            },
        )
        logger.info("添加 Bocha 网络搜索 MCP 服务器")

    # 连接并加载工具
    try:
        await mcp_service.connect()
        logger.info(f"MCP 服务初始化完成，加载了 {len(mcp_service.tools)} 个工具")
    except Exception as e:
        logger.error(f"MCP 服务初始化失败：{e}")
        raise


async def get_mcp_tools() -> List[BaseTool]:
    """
    获取 MCP 工具列表

    Returns:
        工具列表
    """
    if not mcp_service.tools:
        await init_mcp_service()
    return mcp_service.tools


# ==================== 使用示例 ====================


async def example_usage():

    # 示例 1: 使用全局服务
    print("\n=== 示例 1: 使用全局服务 ===")

    # 初始化全局服务（从环境变量加载）
    await init_mcp_service()

    # 获取工具
    tools = await get_mcp_tools()
    logger.info(f"本次加载了 {len(tools)} 个 MCP 工具")
    for tool in tools:
        logger.info(f"工具名称: {tool.name}")
        logger.info(f"工具描述: {tool.description}")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())
