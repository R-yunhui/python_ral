"""deepagents 最小示例：主代理 + 子代理 + 工具."""

from __future__ import annotations

import os

from deepagents import SubAgent, create_deep_agent
from langchain_core.tools import tool


@tool
def calc_sum(a: int, b: int) -> str:
    """Return the sum of two integers."""
    return f"{a + b}"


def ensure_online_mode() -> bool:
    """deepagents 需要支持 tool calling 的真实模型。"""
    if os.getenv("USE_REAL_LLM") != "1":
        print("请先设置 USE_REAL_LLM=1 再运行此示例。")
        return False
    if not os.getenv("OPENAI_API_KEY"):
        print("请先设置 OPENAI_API_KEY 再运行此示例。")
        return False
    return True


def main() -> None:
    if not ensure_online_mode():
        return

    math_subagent: SubAgent = {
        "name": "math-specialist",
        "description": "处理简单数学与数字核对任务。",
        "system_prompt": "你是数学助理。优先调用工具计算，再用一句话解释结果。",
        "tools": [calc_sum],
        "model": "openai:gpt-4.1-mini",
    }

    agent = create_deep_agent(
        model="openai:gpt-4.1-mini",
        tools=[calc_sum],
        subagents=[math_subagent],
        system_prompt="你是一个中文助手。需要精确计算时优先使用工具。",
    )

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "请计算 19+23，并告诉我为什么在复杂任务里子代理有帮助。",
                }
            ]
        }
    )

    print("=== deepagents 结果 ===")
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
