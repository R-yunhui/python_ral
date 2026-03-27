"""
A2A 协议 - 客户端示例
用于测试 A2A Agent 服务端

运行方式（需要先启动服务端）:
    uv run llm/02_a2a_client.py
"""

import asyncio
import httpx

from a2a.client import (
    A2ACardResolver,
    Client,
    ClientFactory,
    ClientConfig,
    create_text_message_object,
)
from a2a.types import AgentCard, Message, Task
from a2a.utils.message import get_message_text
from a2a.utils.parts import get_text_parts


def _a2a_reply_text(yielded: Message | tuple) -> str:
    if isinstance(yielded, Message):
        return get_message_text(yielded)
    if isinstance(yielded, tuple) and yielded and isinstance(yielded[0], Task):
        task = yielded[0]
        if task.status and task.status.message:
            return get_message_text(task.status.message)
        if task.artifacts:
            for art in task.artifacts:
                chunks = get_text_parts(art.parts)
                if chunks:
                    return "\n".join(chunks)
    return str(yielded)


async def fetch_agent_card(base_url: str) -> AgentCard:
    """获取 Agent Card"""
    async with httpx.AsyncClient(trust_env=False) as http_client:
        resolver = A2ACardResolver(http_client, base_url)
        agent_card = await resolver.get_agent_card()
        return agent_card


async def send_message(client: Client, text: str) -> None:
    """发送消息给 Agent"""
    print(f"\n>>> 发送消息: {text}")
    print("-" * 40)

    msg = create_text_message_object(content=text)
    async for item in client.send_message(msg):
        print(f"<<< Agent 响应: {_a2a_reply_text(item)}")
        return
    print("<<< 响应: (无内容)")


async def interactive_chat(base_url: str) -> None:
    """交互式聊天"""
    print("正在获取 Agent Card...")
    http_client = httpx.AsyncClient(timeout=30.0, trust_env=False)
    try:
        resolver = A2ACardResolver(http_client, base_url)
        agent_card = await resolver.get_agent_card()
        client = await ClientFactory.connect(
            agent_card,
            client_config=ClientConfig(
                httpx_client=http_client,
                streaming=False,
            ),
        )
    except BaseException:
        await http_client.aclose()
        raise

    async with client:
        print("\n" + "=" * 60)
        print(f"Agent 名称: {agent_card.name}")
        print(f"Agent 描述: {agent_card.description}")
        print(f"Agent 版本: {agent_card.version}")
        print(f"可用技能: {[s.name for s in agent_card.skills]}")
        print("=" * 60)

        print("\n开始聊天 (输入 'quit' 或 'exit' 退出)")
        print("-" * 40)

        while True:
            try:
                user_input = input("\n你: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["quit", "exit"]:
                    print("再见!")
                    break

                await send_message(client, user_input)

            except KeyboardInterrupt:
                print("\n再见!")
                break
            except Exception as e:
                print(f"错误: {e}")


async def demo_messages(base_url: str) -> None:
    """演示发送多条消息"""
    http_client = httpx.AsyncClient(timeout=30.0, trust_env=False)
    try:
        resolver = A2ACardResolver(http_client, base_url)
        agent_card = await resolver.get_agent_card()
        client = await ClientFactory.connect(
            agent_card,
            client_config=ClientConfig(
                httpx_client=http_client,
                streaming=False,
            ),
        )
    except BaseException:
        await http_client.aclose()
        raise

    async with client:
        print(f"\n已连接到 Agent: {agent_card.name}")
        print("=" * 60)

        test_messages = [
            "Hello!",
            "What time is it?",
            "你好，世界！",
        ]

        for msg in test_messages:
            await send_message(client, msg)
            await asyncio.sleep(0.5)


def main():
    """主函数"""
    BASE_URL = "http://localhost:9999"

    print("=" * 60)
    print("A2A Client Demo")
    print("=" * 60)
    print("请确保服务端已启动: uv run llm/01_a2a_helloworld.py")
    print("=" * 60)

    # 选择模式
    print("\n选择模式:")
    print("1. 交互式聊天")
    print("2. 演示模式（自动发送测试消息）")

    choice = input("\n请选择 (1/2): ").strip()

    if choice == "2":
        asyncio.run(demo_messages(BASE_URL))
    else:
        asyncio.run(interactive_chat(BASE_URL))


if __name__ == "__main__":
    main()