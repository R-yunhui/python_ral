"""
A2A 协议 - 多 Agent 协作示例
展示两个 A2A Agent 之间的协作

场景：
- Researcher Agent: 研究员，负责信息收集
- Writer Agent: 写作者，负责内容创作
- Orchestrator: 协调器，负责调度两个 Agent

运行方式:
    # 终端1: 启动研究 Agent
    uv run llm/04_a2a_multi_agent.py --agent researcher

    # 终端2: 启动写作 Agent
    uv run llm/04_a2a_multi_agent.py --agent writer

    # 终端3: 启动协调器
    uv run llm/04_a2a_multi_agent.py --orchestrator
"""

import os
import sys
import asyncio
import uvicorn
import httpx
import argparse

from dotenv import load_dotenv
from pathlib import Path
from typing import Optional

# A2A 相关
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils import new_agent_text_message
from a2a.utils.message import get_message_text
from a2a.utils.parts import get_text_parts
from a2a.client import ClientFactory, ClientConfig, create_text_message_object
from a2a.types import Message, Task

# LangChain 相关
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# 加载环境变量
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# 协调器走 blocking message/send，需等对端 Agent 内 LLM 跑完；60s 易触发 httpx 读超时
_ORCH_HTTP_TIMEOUT = float(os.getenv("A2A_ORCHESTRATOR_HTTP_TIMEOUT", "600"))


def _a2a_reply_text(yielded: Message | tuple) -> str:
    """从 Client.send_message 的 yield 结果中取出文本（Message 或 (Task, update)）。"""
    if isinstance(yielded, Message):
        return get_message_text(yielded)
    if not isinstance(yielded, tuple) or not yielded:
        return str(yielded)
    task = yielded[0]
    if isinstance(task, Task):
        if task.status and task.status.message:
            return get_message_text(task.status.message)
        if task.artifacts:
            for art in task.artifacts:
                chunks = get_text_parts(art.parts)
                if chunks:
                    return "\n".join(chunks)
    return str(yielded)


# ============ 工具函数 ============
def create_llm():
    """创建 LLM 实例"""
    return ChatOpenAI(
        model=os.getenv("QWEN_CHAT_MODEL", "qwen-plus"),
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url=os.getenv("DASHSCOPE_BASE_URL"),
        temperature=0.7,
    )


# ============ Researcher Agent ============
class ResearcherAgent:
    """研究员 Agent - 负责信息收集和分析"""

    def __init__(self):
        self.llm = create_llm()

    def invoke(self, topic: str) -> str:
        """研究指定主题"""
        system_prompt = """你是一个专业的研究员。你的任务是：
1. 对给定的主题进行深入分析
2. 收集关键信息和要点
3. 以结构化的方式呈现研究结果

请用中文回答，格式清晰。"""

        response = self.llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"请研究以下主题并提供详细分析：\n\n{topic}"),
            ]
        )
        return response.content


class ResearcherExecutor(AgentExecutor):
    def __init__(self):
        self.agent = ResearcherAgent()

    async def execute(
        self, request_context: RequestContext, event_queue: EventQueue
    ) -> None:
        user_message = ""
        if request_context.message and request_context.message.parts:
            user_message = "\n".join(get_text_parts(request_context.message.parts))
        result = await asyncio.to_thread(self.agent.invoke, user_message)
        await event_queue.enqueue_event(new_agent_text_message(result))

    async def cancel(
        self, request_context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception("Cancel not supported")


def create_researcher_card() -> AgentCard:
    return AgentCard(
        name="Researcher Agent",
        description="专业研究员，负责信息收集和主题分析",
        url="http://localhost:10001/",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[
            AgentSkill(
                id="research",
                name="主题研究",
                description="对指定主题进行深入研究和分析",
                tags=["研究", "分析"],
                examples=["研究人工智能发展趋势", "分析区块链应用场景"],
            )
        ],
    )


# ============ Writer Agent ============
class WriterAgent:
    """写作者 Agent - 负责内容创作"""

    def __init__(self):
        self.llm = create_llm()

    def invoke(self, content: str, style: str = "专业") -> str:
        """基于素材创作内容"""
        system_prompt = f"""你是一个专业的内容创作者。你的任务是：
1. 基于提供的研究素材创作高质量内容
2. 风格要求：{style}
3. 结构清晰，逻辑严谨

请用中文创作，注意文笔流畅。"""

        response = self.llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"请基于以下素材创作内容：\n\n{content}"),
            ]
        )
        return response.content


class WriterExecutor(AgentExecutor):
    def __init__(self):
        self.agent = WriterAgent()

    async def execute(
        self, request_context: RequestContext, event_queue: EventQueue
    ) -> None:
        user_message = ""
        if request_context.message and request_context.message.parts:
            user_message = "\n".join(get_text_parts(request_context.message.parts))
        result = await asyncio.to_thread(self.agent.invoke, user_message)
        await event_queue.enqueue_event(new_agent_text_message(result))

    async def cancel(
        self, request_context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception("Cancel not supported")


def create_writer_card() -> AgentCard:
    return AgentCard(
        name="Writer Agent",
        description="内容创作者，基于研究素材撰写高质量内容",
        url="http://localhost:10002/",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[
            AgentSkill(
                id="write",
                name="内容创作",
                description="基于素材创作高质量内容",
                tags=["写作", "创作"],
                examples=["写一篇技术文章", "创作产品介绍"],
            )
        ],
    )


# ============ Orchestrator ============
class Orchestrator:
    """协调器 - 调度多个 Agent 协作"""

    def __init__(self):
        self.researcher_url = "http://localhost:10001"
        self.writer_url = "http://localhost:10002"
        self.llm = create_llm()

    async def call_agent(self, base_url: str, message: str) -> str:
        """调用指定的 Agent（JSON-RPC transport，blocking message/send）。"""
        # trust_env=False：避免系统 HTTP 代理把 localhost 转发成 502
        http_client = httpx.AsyncClient(timeout=_ORCH_HTTP_TIMEOUT, trust_env=False)
        try:
            client = await ClientFactory.connect(
                base_url,
                client_config=ClientConfig(
                    httpx_client=http_client,
                    streaming=False,
                ),
            )
        except BaseException:
            await http_client.aclose()
            raise
        async with client:
            msg = create_text_message_object(content=message)
            async for item in client.send_message(msg):
                return _a2a_reply_text(item)
        return ""

    async def orchestrate(self, topic: str) -> str:
        """
        协调多个 Agent 完成任务

        流程：
        1. 调用 Researcher Agent 进行研究
        2. 调用 Writer Agent 基于研究结果创作内容
        3. 整合并返回最终结果
        """
        print(f"\n{'='*60}")
        print(f"开始处理任务: {topic}")
        print(f"{'='*60}")

        # Step 1: 调用研究员
        print("\n[Step 1] 调用 Researcher Agent...")
        research_result = await self.call_agent(self.researcher_url, topic)
        print(f"研究结果:\n{research_result[:200]}...\n")

        # Step 2: 调用写作者
        print("[Step 2] 调用 Writer Agent...")
        write_prompt = f"主题：{topic}\n\n研究素材：\n{research_result}"
        article = await self.call_agent(self.writer_url, write_prompt)
        print(f"创作结果:\n{article[:200]}...\n")

        # Step 3: 整合结果
        print("[Step 3] 整合最终结果...")
        final_result = f"""# 研究报告: {topic}

## 研究分析
{research_result}

## 最终文章
{article}
"""
        return final_result


async def run_orchestrator_demo():
    """运行协调器演示"""
    orchestrator = Orchestrator()

    print("\n" + "=" * 60)
    print("A2A 多 Agent 协作演示")
    print("=" * 60)
    print("请确保已启动:")
    print("  - Researcher Agent: uv run llm/04_a2a_multi_agent.py --agent researcher")
    print("  - Writer Agent: uv run llm/04_a2a_multi_agent.py --agent writer")
    print("=" * 60)

    topics = [
        "人工智能在医疗领域的应用",
        "可持续发展的商业机会",
    ]

    for topic in topics:
        try:
            result = await orchestrator.orchestrate(topic)
            print("\n" + "=" * 60)
            print("最终结果:")
            print("=" * 60)
            print(result)
            print("\n" + "=" * 60)
        except Exception as e:
            print(f"处理失败: {e}")

        await asyncio.sleep(1)


# ============ 服务器启动函数 ============
def run_researcher_server():
    """启动研究员 Agent 服务"""
    agent_card = create_researcher_card()
    request_handler = DefaultRequestHandler(
        agent_executor=ResearcherExecutor(),
        task_store=InMemoryTaskStore(),
    )
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    print(f"\nResearcher Agent 启动中...")
    print(f"URL: {agent_card.url}")
    uvicorn.run(server.build(), host="0.0.0.0", port=10001)


def run_writer_server():
    """启动写作者 Agent 服务"""
    agent_card = create_writer_card()
    request_handler = DefaultRequestHandler(
        agent_executor=WriterExecutor(),
        task_store=InMemoryTaskStore(),
    )
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    print(f"\nWriter Agent 启动中...")
    print(f"URL: {agent_card.url}")
    uvicorn.run(server.build(), host="0.0.0.0", port=10002)


# ============ 主函数 ============
def main():
    parser = argparse.ArgumentParser(description="A2A 多 Agent 协作示例")
    parser.add_argument(
        "--agent", choices=["researcher", "writer"], help="启动指定的 Agent 服务"
    )
    parser.add_argument("--orchestrator", action="store_true", help="运行协调器演示")

    args = parser.parse_args()

    if args.agent == "researcher":
        run_researcher_server()
    elif args.agent == "writer":
        run_writer_server()
    elif args.orchestrator:
        asyncio.run(run_orchestrator_demo())
    else:
        print("使用方法:")
        print("  启动研究员 Agent: uv run llm/04_a2a_multi_agent.py --agent researcher")
        print("  启动写作者 Agent: uv run llm/04_a2a_multi_agent.py --agent writer")
        print("  运行协调器:       uv run llm/04_a2a_multi_agent.py --orchestrator")


if __name__ == "__main__":
    main()
