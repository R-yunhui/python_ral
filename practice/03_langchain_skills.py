"""
LangChain Skills 集成示例

演示如何使用 agentskills-langchain 包加载本地 skills 并集成到 LangChain agent 中。
支持可靠的 JSON 结构化输出。
"""

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv

from agentskills_core import SkillRegistry
from agentskills_fs import LocalFileSystemSkillProvider
from agentskills_langchain import get_tools, get_tools_usage_instructions

from langchain.agents import create_agent
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser


# 加载环境配置
load_dotenv()

# 使用通义千问模型
model = ChatOpenAI(
    model=os.getenv("QWEN_CHAT_MODEL"), 
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    streaming=True,
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
)

def extract_json_from_content(content: str) -> Optional[Dict[str, Any]]:
    """
    从 markdown 格式的内容中提取 JSON 数据

    Args:
        content: 包含 JSON 的字符串（可能包含 markdown 代码块）

    Returns:
        解析后的 JSON 字典，如果解析失败则返回 None
    """
    if not content.strip():
        return None

    # 尝试 1: 提取 ```json 代码块
    json_block = re.search(r"```json\s*([\s\S]*?)```", content)
    if json_block:
        json_str = json_block.group(1).strip()
    else:
        # 尝试 2: 提取任意 ``` 代码块
        code_block = re.search(r"```\s*([\s\S]*?)```", content)
        if code_block:
            json_str = code_block.group(1).strip()
        else:
            # 尝试 3: 查找第一个 { 到最后一个 }
            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                json_str = json_match.group(0)
            else:
                # 尝试 4: 直接解析整个内容
                json_str = content.strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"\nJSON 解析失败：{e}")
        print(f"尝试解析的内容：{json_str[:200]}...")
        return None


async def main(query: str, expect_json: bool = True):
    """
    主函数 - 支持可靠的 JSON 输出

    Args:
        query: 用户查询
        expect_json: 是否期望 JSON 格式输出（默认 True）
    """
    # 1. 设置 skills 路径
    skills_path = Path(__file__).parent.parent / "skills"
    print(f"Skills 目录：{skills_path}")

    # 2. 创建 Provider 和 Registry
    provider = LocalFileSystemSkillProvider(skills_path)
    registry = SkillRegistry()

    # 3. 注册所有 skills
    # 遍历 skills 目录，注册每个 skill
    for skill_dir in skills_path.iterdir():
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            skill_name = skill_dir.name
            await registry.register(skill_name, provider)
            print(f"已注册 skill: {skill_name}")

    # 4. 生成 LangChain 工具
    tools = get_tools(registry)
    print(f"\n生成的工具：{[t.name for t in tools]}")

    # 5. 生成系统提示
    catalog = await registry.get_skills_catalog(format="xml")
    instructions = get_tools_usage_instructions()

    # 添加 JSON 输出要求
    json_instruction = (
        """
【重要输出格式要求】
- 你必须始终以 JSON 格式返回最终结果
- JSON 必须使用 ```json 代码块包裹
- 确保 JSON 格式正确，可以被 json.loads() 解析
- 如果任务有结构化数据，请放在 JSON 对象中
"""
        if expect_json
        else ""
    )

    system_prompt = f"""你是一个有帮助的 AI 助手，可以使用以下技能来完成任务。

{catalog}

{instructions}

{json_instruction}
"""
    print(f"\n系统提示已生成，长度：{len(system_prompt)} 字符")

    # 6. 创建 Agent
    try:
        agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
            debug=True,
        )
        print("\nAgent 创建成功!")
        print()

        # 7. 运行 Agent 示例
        content = ""
        print("Agent 响应：")
        print("-" * 50)
        async for chunk, _ in agent.astream(
            {"messages": [{"role": "user", "content": query}]}, stream_mode="messages"
        ):
            content += chunk.content
            print(chunk.content, end="", flush=True)
        print("\n" + "-" * 50)

        # 8. 提取并验证 JSON 数据
        if expect_json:
            print("\n\n正在提取 JSON 数据...")
            json_data = extract_json_from_content(content)

            if json_data:
                print("✓ JSON 提取成功!")
                print(
                    f"\n解析后的数据：{json.dumps(json_data, ensure_ascii=False, indent=2)}"
                )
                
                # 将 JSON 结果写入到同层文件
                output_file = Path(__file__).parent / "output.json"
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                print(f"\n✓ JSON 结果已写入：{output_file}")
                
                return json_data
            else:
                print("✗ JSON 提取失败，请检查模型输出格式")
                return None
        else:
            return content

    except Exception as e:
        print(f"\n创建 Agent 时出错：{e}")
        return None


async def main_with_structured_output(query: str):
    """
    使用结构化输出的高级版本（如果模型支持）

    注意：需要模型支持 structured output 功能
    """
    # 1-6 步与 main 相同
    skills_path = Path(__file__).parent.parent / "skills"
    provider = LocalFileSystemSkillProvider(skills_path)
    registry = SkillRegistry()

    for skill_dir in skills_path.iterdir():
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            skill_name = skill_dir.name
            await registry.register(skill_name, provider)
            print(f"已注册 skill: {skill_name}")

    tools = get_tools(registry)
    catalog = await registry.get_skills_catalog(format="xml")
    instructions = get_tools_usage_instructions()

    system_prompt = f"""你是一个有帮助的 AI 助手，可以使用以下技能来完成任务。

{catalog}

{instructions}

【输出要求】请始终以纯 JSON 格式返回结果，不要包含其他解释性文字。
"""

    try:
        # 创建 JSON 解析器
        parser = JsonOutputParser()

        agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
            debug=False,
        )
        print("\nAgent 创建成功 (带 JSON 解析器)!")

        # 执行并自动解析 JSON
        result = await agent.ainvoke({"messages": [{"role": "user", "content": query}]})

        # 提取最后一条消息的内容
        content = result["messages"][-1].content

        # 使用解析器提取 JSON
        json_data = extract_json_from_content(content)

        if json_data:
            print(
                f"\n✓ 结构化输出成功：{json.dumps(json_data, ensure_ascii=False, indent=2)}"
            )
            
            # 将 JSON 结果写入到同层文件
            output_file = Path(__file__).parent / "output.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            print(f"\n✓ JSON 结果已写入：{output_file}")
            
            return json_data
        else:
            print("✗ 结构化输出失败")
            return None

    except Exception as e:
        print(f"\n出错：{e}")
        return None


if __name__ == "__main__":
    # 示例 1: 普通 JSON 输出
    # asyncio.run(main("你好，请用 JSON 格式介绍你自己"))

    # 示例 2: 不使用 JSON 输出
    # asyncio.run(main("你好", expect_json=False))

    # 示例 3: 使用结构化输出版本
    asyncio.run(main_with_structured_output("创建一个毕升的工作流，用于一个简单的天气查询助手"))
