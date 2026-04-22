import os
import json
import asyncio
import re
from typing import Any, Callable, Dict, List, Set

from dotenv import load_dotenv

from fastmcp import Client, FastMCP
from fastmcp.client.transports import NpxStdioTransport

# langchain 相关
from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallRequest
from langchain.agents.middleware.types import before_model, wrap_tool_call
from langchain.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.callbacks import UsageMetadataCallbackHandler

# langgraph
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

checkpointer = InMemorySaver()

usage_callback = UsageMetadataCallbackHandler()

# 加载环境变量
load_dotenv()

ALI_YUNXIAO_ACCESS_TOKEN = os.getenv("ALI_YUNXIAO_ACCESS_TOKEN")


@wrap_tool_call
async def awrap_tool_call_middleware(
    request: ToolCallRequest,
    handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
) -> ToolMessage | Command:
    tool = request.tool
    print(f"awrap_tool_call_middleware 即将调用工具: {tool.name}")
    result = await handler(request)
    print(f"awrap_tool_call_middleware 工具调用完成，返回结果: {result}")
    return result


transport = NpxStdioTransport(
    package="alibabacloud-devops-mcp-server",
    args=["-y"],
    env_vars={"YUNXIAO_ACCESS_TOKEN": ALI_YUNXIAO_ACCESS_TOKEN},
)

server_configs = {
    "yunxiao": {
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "alibabacloud-devops-mcp-server"],
        "env": {"YUNXIAO_ACCESS_TOKEN": ALI_YUNXIAO_ACCESS_TOKEN},
    }
}

# async def get_yunxiao_mcp():
#     async with Client(transport) as client:
#         tools = await client.list_tools()
#         json_list = [json.dumps(tool.model_dump(), indent=2, ensure_ascii=False) for tool in tools]
#         with open("yunxiao_mcp_tools.json", "w", encoding="utf-8") as f:
#             f.write("\n".join(json_list))
#         print(f"写入文件成功: yunxiao_mcp_tools.json")


async def get_yunxiao_mcp_tools() -> List[BaseTool]:
    mcp_client = MultiServerMCPClient(server_configs)
    tools = await mcp_client.get_tools()
    print(f"已经加载到的工具数量: {len(tools)}")
    return tools


chat_model = ChatOpenAI(
    model=os.getenv("QWEN_CHAT_MODEL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    streaming=True,
    extra_body={
        "enable_thinking": True,
        "thinking_budget": 100,
    },
    model_kwargs={
        "stream_options": {
            "include_usage": True,
        },
    },
)

agent = None


REQUIREMENT_TEXT = (
    "我主要是为了查询我当前都有哪些项目，并且项目里面有哪些迭代，"
    "还要查询相应的需求，以及需求下面的任务，并且可以新增、编辑、删除我自己的任务。"
)


def _tool_to_meta(tool: BaseTool) -> dict:
    """提取工具关键信息，避免把完整对象直接塞给 LLM。"""
    schema = getattr(tool, "args_schema", None)
    required_fields: List[str] = []
    all_fields: List[str] = []
    if schema and hasattr(schema, "model_json_schema"):
        schema_json = schema.model_json_schema()
        required_fields = list(schema_json.get("required", []) or [])
        all_fields = list((schema_json.get("properties") or {}).keys())

    return {
        "name": tool.name,
        "description": tool.description or "",
        "required_fields": required_fields,
        "all_fields": all_fields,
    }


def _normalize_name(raw: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", raw.lower())


def _dependency_expand(selected: Set[str], tool_metas: List[dict]) -> Set[str]:
    """
    根据工具必填参数进行依赖补全：
    - 例如需要 projectId 时，补全 project 查询类工具。
    """
    field_to_resource = {
        "projectid": ["project", "projects"],
        "iterationid": ["iteration", "sprint"],
        "workitemid": ["workitem", "requirement", "story", "task"],
        "taskid": ["task"],
        "userid": ["user", "member", "me"],
    }

    def find_provider_tools(resource_keywords: List[str]) -> List[str]:
        providers: List[str] = []
        for meta in tool_metas:
            normalized_name = _normalize_name(meta["name"])
            desc = (meta["description"] or "").lower()
            if any(
                k in normalized_name or k in desc for k in resource_keywords
            ) and any(
                t in normalized_name for t in ("list", "get", "query", "search", "find")
            ):
                providers.append(meta["name"])
        return providers

    all_selected = set(selected)
    changed = True
    while changed:
        changed = False
        current_selected = list(all_selected)
        for selected_name in current_selected:
            selected_meta = next(
                (m for m in tool_metas if m["name"] == selected_name),
                None,
            )
            if not selected_meta:
                continue
            for required in selected_meta.get("required_fields", []):
                required_norm = _normalize_name(required)
                for field_pattern, resources in field_to_resource.items():
                    if field_pattern in required_norm:
                        for provider in find_provider_tools(resources):
                            if provider not in all_selected:
                                all_selected.add(provider)
                                changed = True
    return all_selected


async def _llm_pick_tools(tool_metas: List[dict], requirement_text: str) -> List[str]:
    """首轮：让 LLM 从结构化工具列表中挑选候选工具。"""
    messages = [
        SystemMessage(
            content="你是工具规划助手。只返回 JSON 数组，不要返回任何额外文本。"
        ),
        HumanMessage(
            content=(
                "请从以下工具中选择满足需求的全部工具，宁多勿漏，并考虑参数依赖链。\n\n"
                f"需求:\n{requirement_text}\n\n"
                f"工具列表(JSON):\n{json.dumps(tool_metas, ensure_ascii=False)}\n\n"
                '返回格式示例: ["tool_a", "tool_b"]'
            )
        ),
    ]
    result = await chat_model.ainvoke(
        input=messages,
        config=RunnableConfig(callbacks=[usage_callback]),
    )
    content = (result.content or "").strip() if isinstance(result.content, str) else ""
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return [x for x in parsed if isinstance(x, str)]
    except Exception:
        pass
    return re.findall(r'"([^"]+)"', content)


async def _llm_find_missing(
    tool_metas: List[dict], requirement_text: str, selected_tools: List[str]
) -> List[str]:
    """二轮：让 LLM 在已选结果基础上只返回遗漏工具。"""
    messages = [
        SystemMessage(
            content="你是工具审查助手。只返回 JSON 数组，不要返回任何额外文本。"
        ),
        HumanMessage(
            content=(
                "请检查下面的已选工具是否有遗漏，只返回漏掉的工具名；若无遗漏返回 []。\n\n"
                f"需求:\n{requirement_text}\n\n"
                f"已选工具:\n{json.dumps(selected_tools, ensure_ascii=False)}\n\n"
                f"全量工具(JSON):\n{json.dumps(tool_metas, ensure_ascii=False)}\n\n"
                '返回格式示例: ["tool_c"] 或 []'
            )
        ),
    ]
    result = await chat_model.ainvoke(
        input=messages,
        config=RunnableConfig(callbacks=[usage_callback]),
    )
    content = (result.content or "").strip() if isinstance(result.content, str) else ""
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return [x for x in parsed if isinstance(x, str)]
    except Exception:
        pass
    return re.findall(r'"([^"]+)"', content)


async def get_need_tools(tools: List[BaseTool]) -> List[str]:
    tool_metas = [_tool_to_meta(tool) for tool in tools]
    all_tool_names = {meta["name"] for meta in tool_metas}

    first_selected = await _llm_pick_tools(tool_metas, REQUIREMENT_TEXT)
    selected = {name for name in first_selected if name in all_tool_names}

    # 用规则做一次依赖闭包补全，降低模型漏选概率
    selected = _dependency_expand(selected, tool_metas)

    missing = await _llm_find_missing(tool_metas, REQUIREMENT_TEXT, sorted(selected))
    selected.update(name for name in missing if name in all_tool_names)

    usage_metadata = (
        usage_callback.usage_metadata.get(os.getenv("QWEN_CHAT_MODEL")) or {}
    )
    print(f"输入 tokens: {usage_metadata.get('input_tokens')}")
    print(f"输出 tokens: {usage_metadata.get('output_tokens')}")
    print(f"总计 tokens: {usage_metadata.get('total_tokens')}")
    print(f"筛选出的工具数量: {len(selected)}")
    print(f"筛选出的工具名称: {sorted(selected)}")

    return sorted(selected)


async def create_yunxiao_agent():
    tools = await get_yunxiao_mcp_tools()

    need_tools = await get_need_tools(tools)

    need_tools_list = [tool for tool in tools if tool.name in need_tools]

    print(f"需要使用的工具: {need_tools_list}")
    return create_agent(
        model=chat_model,
        tools=need_tools_list,
        system_prompt=SystemMessage(
            content="你是一个助手，请根据用户的问题，给出回答。"
        ),
        debug=False,
        checkpointer=checkpointer,
        middleware=[awrap_tool_call_middleware],
    )


async def chat(query: str, user_id: str) -> None:
    try:
        async for chunk, metadata in agent.astream(
            input={"messages": [HumanMessage(content=query)]},
            stream_mode="messages",
            config=RunnableConfig(
                configurable={"thread_id": user_id},
                callbacks=[usage_callback],
            ),
        ):
            print(chunk.content, end="", flush=True)
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        usage_metadata = usage_callback.usage_metadata.get(os.getenv("QWEN_CHAT_MODEL"))
        print(f"输入 tokens: {usage_metadata.get('input_tokens')}")
        print(f"输出 tokens: {usage_metadata.get('output_tokens')}")
        print(f"总计 tokens: {usage_metadata.get('total_tokens')}")
        print()


async def main():
    global agent

    if agent is None:
        agent = await create_yunxiao_agent()

    print
    while True:
        query = input("请输入问题: ").strip()
        if query.lower() in ["exit", "quit"]:
            break
        await chat(query, "user-1")


if __name__ == "__main__":

    asyncio.run(main())
