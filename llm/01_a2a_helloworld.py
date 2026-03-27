"""
A2A 协议 - HelloWorld 示例
最简单的 A2A Agent 服务端实现

运行方式:
    uv run llm/01_a2a_helloworld.py

测试:
    uv run llm/02_a2a_client.py
"""

import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils import new_agent_text_message
from a2a.utils.parts import get_text_parts


class HelloWorldAgent:
    """简单的 Agent 实现 - 返回 Hello World"""

    def invoke(self, request_context: RequestContext) -> str:
        """
        执行 Agent 逻辑

        Args:
            request_context: 请求上下文，包含用户消息等信息

        Returns:
            Agent 的响应文本
        """
        # 从请求上下文获取用户消息
        user_message = ""
        if request_context.message and request_context.message.parts:
            user_message = "\n".join(get_text_parts(request_context.message.parts)) or ""

        # 简单的响应逻辑
        if "hello" in user_message.lower():
            return f"Hello! You said: '{user_message}'"
        elif "time" in user_message.lower():
            import datetime
            return f"Current time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            return f"Hello World! You said: '{user_message}'"


class HelloWorldAgentExecutor(AgentExecutor):
    """
    A2A Agent 执行器

    实现 A2A 协议要求的 execute 和 cancel 方法
    """

    def __init__(self):
        self.agent = HelloWorldAgent()

    async def execute(
        self,
        request_context: RequestContext,
        event_queue: EventQueue
    ) -> None:
        """
        执行 Agent 并将结果放入事件队列

        Args:
            request_context: 请求上下文
            event_queue: 事件队列，用于返回结果
        """
        result = self.agent.invoke(request_context)
        await event_queue.enqueue_event(new_agent_text_message(result))

    async def cancel(
        self,
        request_context: RequestContext,
        event_queue: EventQueue
    ) -> None:
        """取消任务（本示例不支持）"""
        raise Exception("Cancel operation is not supported")


def create_agent_card() -> AgentCard:
    """创建 Agent Card（能力描述）"""

    # 定义技能
    hello_skill = AgentSkill(
        id="hello_world",
        name="Hello World",
        description="Returns a friendly greeting message",
        tags=["greeting", "hello"],
        examples=["hello", "hi there", "greet me"],
    )

    time_skill = AgentSkill(
        id="get_time",
        name="Get Current Time",
        description="Returns the current date and time",
        tags=["time", "date"],
        examples=["what time is it", "current time", "时间"],
    )

    # 创建 Agent Card
    return AgentCard(
        name="Hello World Agent",
        description="A simple A2A agent that demonstrates basic functionality",
        url="http://localhost:9999/",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[hello_skill, time_skill],
    )


def main():
    """启动 A2A Agent 服务"""

    # 1. 创建 Agent Card
    agent_card = create_agent_card()

    # 2. 创建请求处理器
    request_handler = DefaultRequestHandler(
        agent_executor=HelloWorldAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    # 3. 创建 A2A 服务器
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    print("=" * 60)
    print("A2A HelloWorld Agent Server")
    print("=" * 60)
    print(f"Agent Name: {agent_card.name}")
    print(f"Agent URL: {agent_card.url}")
    print(f"Skills: {[s.name for s in agent_card.skills]}")
    print("=" * 60)
    print("Server starting on http://localhost:9999")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    # 4. 启动服务
    uvicorn.run(server.build(), host="0.0.0.0", port=9999)


if __name__ == "__main__":
    main()