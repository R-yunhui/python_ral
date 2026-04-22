"""将 FastMCP Client 获取的工具转换为 LangChain BaseTool"""
import asyncio
import json
from typing import Any

import httpx
from langchain_core.tools import BaseTool

from fastmcp import Client
from fastmcp.client.messages import MessageHandler
from fastmcp.client.transports import StreamableHttpTransport


def _make_httpx_client(**kwargs):
    return httpx.AsyncClient(trust_env=False, **kwargs)


class MCPToolAdapter(BaseTool):
    """将单个 MCP 工具包装为 LangChain BaseTool"""

    def __init__(self, client: Client, mcp_tool):
        super().__init__(
            name=mcp_tool.name,
            description=mcp_tool.description or "",
            args_schema=mcp_tool.inputSchema,
        )
        self._client = client
        self._mcp_tool = mcp_tool

    def _run(self, **kwargs: Any) -> str:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self._arun(**kwargs))

    async def _arun(self, **kwargs: Any) -> str:
        result = await self._client.call_tool(self._mcp_tool.name, kwargs)
        if hasattr(result, "data"):
            return str(result.data)
        if hasattr(result, "content"):
            return "".join(
                c.text for c in result.content if hasattr(c, "text")
            )
        return str(result)


async def main():
    transport = StreamableHttpTransport(
        url="http://127.0.0.1:10010/mcp",
        httpx_client_factory=_make_httpx_client,
    )

    async with Client(transport, message_handler=MessageHandler()) as client:
        # 1. 获取 MCP 工具列表
        mcp_tools = await client.list_tools()
        print(f"MCP Server 提供 {len(mcp_tools)} 个工具:")
        for t in mcp_tools:
            print(f"  - {t.name}: {t.description or '无描述'}")

        # 2. 转换为 LangChain BaseTool
        langchain_tools = [MCPToolAdapter(client, t) for t in mcp_tools]
        print(f"\n转换为 {len(langchain_tools)} 个 LangChain 工具:")
        for t in langchain_tools:
            print(f"  - {t.name} (type={type(t).__name__})")

        # 3. 测试：通过 LangChain 接口调用 calculator
        print("\n--- 测试调用 calculator ---")
        calc_tool = next(t for t in langchain_tools if t.name == "calculator")
        result = await calc_tool.ainvoke({"a": 10, "b": 3, "operation": "multiply"})
        print(f"10 * 3 = {result}")

        # 4. 测试：通过 LangChain 接口调用 echo
        print("\n--- 测试调用 echo ---")
        echo_tool = next(t for t in langchain_tools if t.name == "echo")
        result = await echo_tool.ainvoke({"message": "Hello from LangChain!"})
        print(f"Result: {result}")

        # 5. 集成 LangGraph Agent 示例
        print("\n--- 集成 LangGraph create_react_agent ---")
        try:
            from langchain.chat_models import init_chat_model
            from langgraph.prebuilt import create_react_agent

            # 只选几个简单工具给 Agent
            useful_tools = [
                t for t in langchain_tools
                if t.name in ("calculator", "echo")
            ]
            model = init_chat_model("claude-sonnet-4-6")
            agent = create_react_agent(model, useful_tools)

            result = await agent.ainvoke({
                "messages": [{"role": "user", "content": "计算 100 乘以 25 等于多少？"}]
            })
            print(f"Agent 回复: {result['messages'][-1].content}")
        except Exception as e:
            print(f"LangGraph Agent 跳过 (可能缺少依赖或 API Key): {e}")


if __name__ == "__main__":
    asyncio.run(main())
