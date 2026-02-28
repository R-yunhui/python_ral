"""
LangChain Skills 集成示例

演示如何使用 agentskills-langchain 包加载本地 skills 并集成到 LangChain agent 中。
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from agentskills_core import SkillRegistry
from agentskills_fs import LocalFileSystemSkillProvider
from agentskills_langchain import get_tools, get_tools_usage_instructions

from langchain.agents import create_agent
from langchain_community.chat_models import ChatTongyi

# 加载环境配置
load_dotenv()

# 创建模型
model = ChatTongyi(model=os.getenv("QWEN_CHAT_MODEL"), api_key=os.getenv("DASHSCOPE_API_KEY"))


async def main():
    # 1. 设置 skills 路径
    skills_path = Path(__file__).parent.parent / "skills"
    print(f"Skills 目录: {skills_path}")

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
    print(f"\n生成的工具: {[t.name for t in tools]}")

    # 5. 生成系统提示
    catalog = await registry.get_skills_catalog(format="xml")
    instructions = get_tools_usage_instructions()
    system_prompt = f"""你是一个有帮助的AI助手，可以使用以下技能来完成任务。

{catalog}

{instructions}
"""
    print(f"\n系统提示已生成，长度: {len(system_prompt)} 字符")

    # 6. 创建 Agent（示例使用 OpenAI，可根据需要更换模型）
    # 注意：需要设置 OPENAI_API_KEY 环境变量
    try:
        agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
        )
        print("\nAgent 创建成功!")

        # 7. 运行 Agent 示例
        result = agent.invoke({
            "messages": [{"role": "user", "content": "帮我查看有哪些可用的技能"}]
        })
        print(f"\nAgent 响应: {result}")
    except Exception as e:
        print(f"\n创建 Agent 时出错 (可能需要设置 API Key): {e}")
        print("\n以下是使用原生工具的示例代码...")

        # 直接使用工具示例
        print("\n--- 直接使用工具示例 ---")
        for tool in tools:
            if tool.name == "get_skill_metadata":
                # 获取 skill 元数据
                metadata = await tool.coroutine(skill_id="code-review")
                print(f"code-review 元数据:\n{metadata}\n")

            if tool.name == "get_skill_body":
                # 获取 skill 完整内容
                body = await tool.coroutine(skill_id="code-review")
                print(f"code-review 内容:\n{body[:200]}...\n")


if __name__ == "__main__":
    asyncio.run(main())