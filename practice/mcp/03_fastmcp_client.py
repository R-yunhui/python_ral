import asyncio

import httpx

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


def _make_httpx_client(**kwargs):
    """创建 httpx 客户端，忽略系统代理配置"""
    return httpx.AsyncClient(trust_env=False, **kwargs)


def print_tool_names(tools):
    """打印工具名称列表"""
    names = [t.name for t in tools]
    print(f"  可用工具: {names}")


async def main():
    transport = StreamableHttpTransport(
        url="http://127.0.0.1:10010/mcp",
        httpx_client_factory=_make_httpx_client,
    )

    async with Client(transport) as client:
        # === 步骤 1: 列出初始工具 ===
        print("=" * 50)
        print("步骤 1: 列出初始工具")
        tools = await client.list_tools()
        print_tool_names(tools)

        # === 步骤 2: 动态注册 weather 工具 ===
        print("\n" + "=" * 50)
        print("步骤 2: 注册 weather 工具")
        result = await client.call_tool("register_weather", {})
        print(f"  {result.data}")

        # === 步骤 3: 验证 weather 已出现 ===
        print("\n" + "=" * 50)
        print("步骤 3: 重新列出工具，验证 weather 已出现")
        tools = await client.list_tools()
        print_tool_names(tools)

        # === 步骤 4: 使用新注册的 weather 工具 ===
        print("\n" + "=" * 50)
        print("步骤 4: 调用 weather 工具")
        result = await client.call_tool("weather", {"city": "Beijing"})
        print(f"  结果: {result.data}")

        # === 步骤 5: 动态注册 converter 工具 ===
        print("\n" + "=" * 50)
        print("步骤 5: 注册 unit_converter 工具")
        result = await client.call_tool("register_converter", {})
        print(f"  {result.data}")

        # === 步骤 6: 使用 converter 工具 ===
        print("\n" + "=" * 50)
        print("步骤 6: 调用 unit_converter 工具")
        result = await client.call_tool(
            "unit_converter", {"value": 36.5, "from_unit": "celsius", "to_unit": "fahrenheit"}
        )
        print(f"  结果: {result.data}")

        # === 步骤 7: 移除 weather 工具 ===
        print("\n" + "=" * 50)
        print("步骤 7: 移除 weather 工具")
        result = await client.call_tool("remove_tool", {"name": "weather"})
        print(f"  {result.data}")

        # === 步骤 8: 验证 weather 已消失 ===
        print("\n" + "=" * 50)
        print("步骤 8: 重新列出工具，验证 weather 已消失")
        tools = await client.list_tools()
        print_tool_names(tools)

        # === 步骤 9: 测试 echo 工具的 disable/enable ===
        print("\n" + "=" * 50)
        print("步骤 9: 切换 echo 工具状态")
        result = await client.call_tool("toggle_echo", {})
        print(f"  {result.data}")

        # 测试被禁用的 echo
        try:
            result = await client.call_tool("echo", {"message": "hello"})
            print(f"  echo 调用结果: {result.data}")
        except Exception as e:
            print(f"  echo 调用失败 (已禁用): {e}")

        # 再次切换回来
        result = await client.call_tool("toggle_echo", {})
        print(f"  {result.data}")
        result = await client.call_tool("echo", {"message": "hello"})
        print(f"  echo 调用结果: {result.data}")

        print("\n" + "=" * 50)
        print("演示完成!")


if __name__ == "__main__":
    asyncio.run(main())
