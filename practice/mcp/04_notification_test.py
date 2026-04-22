import asyncio

import httpx
import mcp.types

from fastmcp import Client
from fastmcp.client.messages import MessageHandler
from fastmcp.client.transports import StreamableHttpTransport


# 自定义消息处理器，监听工具列表变化
class ToolChangeHandler(MessageHandler):
    def __init__(self):
        self.change_count = 0

    async def on_tool_list_changed(
        self, notification: mcp.types.ToolListChangedNotification
    ) -> None:
        self.change_count += 1
        print(f"  [收到通知 #{self.change_count}] tools/list_changed")


def _make_httpx_client(**kwargs):
    """创建 httpx 客户端，忽略系统代理配置"""
    return httpx.AsyncClient(trust_env=False, **kwargs)


async def main():
    handler = ToolChangeHandler()
    transport = StreamableHttpTransport(
        url="http://127.0.0.1:10010/mcp",
        httpx_client_factory=_make_httpx_client,
    )

    async with Client(transport, message_handler=handler) as client:
        print("=" * 60)
        print("步骤 1: 初始工具列表")
        tools = await client.list_tools()
        print(f"  {[t.name for t in tools]}")
        print(f"  已收到通知次数: {handler.change_count}")

        print("\n" + "=" * 60)
        print("步骤 2: 注册 weather 工具（server 会推送通知）")
        await client.call_tool("register_weather", {})
        print(f"  已收到通知次数: {handler.change_count}")

        if handler.change_count > 0:
            print("\n" + "=" * 60)
            print("步骤 3: 收到通知，自动刷新工具列表")
            tools = await client.list_tools()
            print(f"  {[t.name for t in tools]}")

        print("\n" + "=" * 60)
        print("步骤 4: 使用 weather 工具")
        result = await client.call_tool("weather", {"city": "Beijing"})
        print(f"  {result.data}")

        print("\n" + "=" * 60)
        print("步骤 5: 移除 weather 工具（server 会推送通知）")
        prev_count = handler.change_count
        await client.call_tool("remove_tool", {"name": "weather"})
        print(f"  已收到通知次数: {handler.change_count}")

        if handler.change_count > prev_count:
            print("\n" + "=" * 60)
            print("步骤 6: 收到通知，刷新工具列表")
            tools = await client.list_tools()
            print(f"  {[t.name for t in tools]}")

        print("\n" + "=" * 60)
        print("步骤 7: 测试 echo toggle")
        await client.call_tool("toggle_echo", {})
        print(f"  已收到通知次数: {handler.change_count}")

        print("\n" + "=" * 60)
        print("演示完成!")


if __name__ == "__main__":
    asyncio.run(main())
