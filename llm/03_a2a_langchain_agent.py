"""
A2A 协议 - 结合 LangChain 的 Agent 示例
展示如何将 LangChain Agent 包装为 A2A Agent

运行方式:
    uv run llm/03_a2a_langchain_agent.py

测试:
    uv run llm/02_a2a_client.py
"""

import asyncio
import os
import uvicorn

from dotenv import load_dotenv
from pathlib import Path

# A2A 相关
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils import new_agent_text_message
from a2a.utils.parts import get_text_parts

# LangChain 相关
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import create_react_agent
from langchain_core.prompts import PromptTemplate

# 加载环境变量
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# ============ 定义工具 ============
@tool
def get_current_time() -> str:
    """获取当前时间和日期"""
    import datetime
    now = datetime.datetime.now()
    return f"当前时间: {now.strftime('%Y年%m月%d日 %H:%M:%S')}"


@tool
def calculate(expression: str) -> str:
    """
    计算数学表达式

    Args:
        expression: 数学表达式，如 "2 + 3 * 4"
    """
    try:
        result = eval(expression)
        return f"计算结果: {expression} = {result}"
    except Exception as e:
        return f"计算错误: {e}"


@tool
def get_weather(city: str) -> str:
    """
    获取城市天气（模拟）

    Args:
        city: 城市名称
    """
    # 模拟天气数据
    weather_data = {
        "北京": "晴天，温度 15°C，空气质量良好",
        "上海": "多云，温度 18°C，有轻微雾霾",
        "深圳": "晴天，温度 25°C，空气质量优",
        "广州": "阴天，温度 22°C，可能有小雨",
    }
    return weather_data.get(city, f"{city}: 晴天，温度 20°C")


# ============ LangChain Agent ============
class LangChainAgent:
    """将 LangChain Agent 包装为可调用的 Agent"""

    def __init__(self):
        # 创建 LLM
        self.llm = ChatOpenAI(
            model=os.getenv("QWEN_CHAT_MODEL", "qwen-plus"),
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url=os.getenv("DASHSCOPE_BASE_URL"),
            temperature=0.7,
        )

        # 绑定工具
        self.tools = [get_current_time, calculate, get_weather]
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    def invoke(self, user_message: str) -> str:
        """
        执行 Agent

        Args:
            user_message: 用户消息

        Returns:
            Agent 响应
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        # 系统提示
        system_prompt = """你是一个有用的 AI 助手，可以使用以下工具来帮助用户：

1. get_current_time: 获取当前时间和日期
2. calculate: 计算数学表达式
3. get_weather: 获取城市天气信息

请根据用户的问题选择合适的工具，并用中文回答。"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]

        # 第一次调用 - 可能触发工具
        response = self.llm_with_tools.invoke(messages)

        # 处理工具调用
        while response.tool_calls:
            # 将 AI 响应添加到消息历史
            messages.append(response)

            # 执行每个工具调用
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                # 找到对应的工具并执行
                for tool_func in self.tools:
                    if tool_func.name == tool_name:
                        try:
                            tool_result = tool_func.invoke(tool_args)
                            messages.append({
                                "role": "tool",
                                "content": tool_result,
                                "tool_call_id": tool_call["id"]
                            })
                        except Exception as e:
                            messages.append({
                                "role": "tool",
                                "content": f"工具执行错误: {e}",
                                "tool_call_id": tool_call["id"]
                            })
                        break

            # 再次调用 LLM 处理工具结果
            response = self.llm_with_tools.invoke(messages)

        # 返回最终响应
        return response.content


# ============ A2A Agent Executor ============
class LangChainA2AExecutor(AgentExecutor):
    """将 LangChain Agent 包装为 A2A Agent Executor"""

    def __init__(self):
        self.agent = LangChainAgent()

    async def execute(
        self,
        request_context: RequestContext,
        event_queue: EventQueue
    ) -> None:
        """执行 Agent"""
        user_message = ""
        if request_context.message and request_context.message.parts:
            user_message = "\n".join(get_text_parts(request_context.message.parts)) or ""

        result = await asyncio.to_thread(self.agent.invoke, user_message)
        await event_queue.enqueue_event(new_agent_text_message(result))

    async def cancel(
        self,
        request_context: RequestContext,
        event_queue: EventQueue
    ) -> None:
        """取消任务"""
        raise Exception("Cancel operation is not supported")


# ============ 创建 Agent Card ============
def create_agent_card() -> AgentCard:
    """创建 Agent Card"""

    skills = [
        AgentSkill(
            id="general_qa",
            name="智能问答",
            description="回答各种问题，支持时间查询、计算、天气查询等",
            tags=["问答", "助手"],
            examples=["现在几点了", "帮我算一下 23 * 45", "北京天气怎么样"],
        ),
        AgentSkill(
            id="time_query",
            name="时间查询",
            description="获取当前时间和日期",
            tags=["时间", "日期"],
            examples=["现在几点了", "今天是几号"],
        ),
        AgentSkill(
            id="calculator",
            name="数学计算",
            description="计算数学表达式",
            tags=["计算", "数学"],
            examples=["算一下 123 + 456", "计算 2 的 10 次方"],
        ),
        AgentSkill(
            id="weather",
            name="天气查询",
            description="查询城市天气信息",
            tags=["天气", "城市"],
            examples=["北京天气", "深圳天气怎么样"],
        ),
    ]

    return AgentCard(
        name="LangChain 智能助手",
        description="一个集成了时间查询、数学计算、天气查询等能力的 AI 助手",
        url="http://localhost:9998/",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=skills,
    )


def main():
    """启动服务"""

    print("=" * 60)
    print("正在初始化 LangChain Agent...")
    print("=" * 60)

    # 测试 LLM 连接
    try:
        agent = LangChainAgent()
        test_result = agent.invoke("你好")
        print(f"LLM 测试成功: {test_result[:50]}...")
    except Exception as e:
        print(f"LLM 初始化失败: {e}")
        print("请检查 .env 文件中的 API 配置")
        return

    # 创建 Agent Card
    agent_card = create_agent_card()

    # 创建请求处理器
    request_handler = DefaultRequestHandler(
        agent_executor=LangChainA2AExecutor(),
        task_store=InMemoryTaskStore(),
    )

    # 创建 A2A 服务器
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    print("\n" + "=" * 60)
    print("A2A LangChain Agent Server")
    print("=" * 60)
    print(f"Agent 名称: {agent_card.name}")
    print(f"Agent URL: {agent_card.url}")
    print(f"可用技能: {[s.name for s in agent_card.skills]}")
    print("=" * 60)
    print("Server starting on http://localhost:9998")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    # 启动服务
    uvicorn.run(server.build(), host="0.0.0.0", port=9998)


if __name__ == "__main__":
    main()