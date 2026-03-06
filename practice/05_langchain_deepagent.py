import os

from dotenv import load_dotenv

from pathlib import Path

# langchain 相关
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_openai.chat_models import ChatOpenAI

from langgraph.checkpoint.memory import InMemorySaver

# deepagents
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

# 项目根目录（用于 .env 和 skills 路径）
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 加载环境变量（从项目根目录的 .env）
load_dotenv(PROJECT_ROOT / ".env")

checkpointer = InMemorySaver()

# 确保 model 不为 None，避免 ChatOpenAI 校验报错
_model_name = os.getenv("QWEN_CHAT_MODEL") or "qwen-plus"
chat_model = ChatOpenAI(
    model=_model_name,
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    streaming=True,
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    model_kwargs={
        "stream_options": {
            "include_usage": True,
        },
    },
    extra_body={
        "enable_thinking": True,
        "thinking_budget": 100,
    },
)

# deepagents 的 skills 约定（见 https://docs.langchain.com/oss/python/deepagents/skills）：
# - 默认 StateBackend 不读磁盘，需通过 invoke(files={...}) 注入
# - 用本地目录时需 FilesystemBackend(root_dir=..., virtual_mode=True)，skills 为 POSIX 虚拟路径（相对 root_dir）
# 本仓库的 skills 在 .cursor/skills/ 下，每个子目录需有 SKILL.md（YAML frontmatter + 说明）
SKILLS_SOURCE = "/.cursor/skills/"
CURSOR_SKILLS_PATH = Path(__file__).parent.parent / "skills/"
print(f"Skills 目录：{PROJECT_ROOT / '.cursor' / 'skills'}")

deep_agent = create_deep_agent(
    model=chat_model,
    system_prompt=SystemMessage(content="你是助手，请根据用户的问题，给出回答。"),
    debug=False,
    checkpointer=checkpointer,
    backend=FilesystemBackend(root_dir=str(PROJECT_ROOT), virtual_mode=True),
    skills=[SKILLS_SOURCE, CURSOR_SKILLS_PATH.__str__()],
)


async def chat(query: str):
    print("开始进行 deepagent 的调用")

    result = deep_agent.invoke(
        input={"messages": [HumanMessage(content=query)]},
        config=RunnableConfig(
            configurable={"thread_id": "thread-1"},
        ),
    )
    print(result["messages"][-1].content)


if __name__ == "__main__":
    import asyncio

    asyncio.run(chat("有哪些 skills 可以使用"))
