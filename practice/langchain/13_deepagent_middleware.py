import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Any

from dotenv import load_dotenv

from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai.chat_models import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from deepagents import create_deep_agent

load_dotenv()

checkpointer = InMemorySaver()

chat_model = ChatOpenAI(
    model=os.getenv("QWEN_CHAT_MODEL"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    streaming=True,
    temperature=0.7,
    max_tokens=None,
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


@tool(description="获取联系人邮箱")
def get_contact_email(name: str) -> str:
    """获取联系人邮箱"""
    return f"{name}@example.com"


@tool(description="给指定用户的邮箱发送邮件")
def send_email(email: str) -> str:
    """给指定用户的邮箱发送邮件"""
    return f"邮件发送成功: {email}"


@tool(description="获取可用时间槽")
def get_available_time_slots(name: str) -> list[str]:
    """获取指定用户的可用时间槽"""
    return ["16:00", "17:00", "18:00"]


@tool(description="创建预约")
def create_appointment(name: str, time_slot: str) -> str:
    """创建预约"""
    return f"预约创建成功: {name}, {time_slot}"


deep_agent = create_deep_agent(
    model=chat_model,
    tools=[
        get_contact_email,
        send_email,
        get_available_time_slots,
        create_appointment,
    ],
    system_prompt=SystemMessage(
        content=(
            "你是一个能力出众的个人助手,当前日期是:"
            f"{datetime.now().strftime('%Y-%m-%d')}"
        )
    ),
    debug=False,
    checkpointer=checkpointer,
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "send_email": {
                    "allowed_decisions": ["approve", "edit", "reject"],
                    "description": "确认是否要发送邮件?",
                },
                "create_appointment": {
                    "allowed_decisions": ["approve", "edit", "reject"],
                    "description": "确认是否要创建预约?",
                },
            },
        )
    ],
)


def _stream_chunk_text(chunk: Any) -> str:
    """从 Chat 流式 chunk 取可打印文本（含 Qwen thinking 的 reasoning）。"""
    if chunk is None:
        return ""
    parts: list[str] = []
    ak = getattr(chunk, "additional_kwargs", None) or {}
    if isinstance(ak, dict):
        reasoning = ak.get("reasoning_content") or ak.get("thought")
        if reasoning:
            parts.append(str(reasoning))
    content = getattr(chunk, "content", None)
    if content:
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict) and block.get("text"):
                    parts.append(str(block["text"]))
    return "".join(parts)


def _hitl_payload_from_state(st: Any) -> dict[str, Any] | None:
    """astream_events 结束后，从 checkpointer 状态取出 HumanInTheLoop 的 request。"""
    for task in getattr(st, "tasks", None) or ():
        interrupts = getattr(task, "interrupts", None) or ()
        if interrupts:
            val = interrupts[0].value
            if isinstance(val, dict) and "action_requests" in val:
                return val
    return None


def _collect_hitl_decisions(hitl: dict[str, Any]) -> list[dict[str, Any]]:
    """根据控制台输入生成 HumanInTheLoopMiddleware 所需的 decisions 列表。"""
    action_requests = hitl["action_requests"]
    review_configs = hitl["review_configs"]
    decisions: list[dict[str, Any]] = []

    for ar, rc in zip(action_requests, review_configs, strict=True):
        name = ar["name"]
        args = ar["args"]
        desc = ar.get("description") or f"工具 {name}"
        allowed: list[str] = list(rc["allowed_decisions"])

        print(f"\n{'=' * 50}")
        print(f"【需确认】{desc}")
        print(f"  工具: {name}")
        print(f"  参数: {json.dumps(args, ensure_ascii=False, indent=2)}")
        print(f"  允许操作: {allowed}")

        options: list[tuple[str, str]] = []
        if "approve" in allowed:
            options.append(("y", "approve"))
        if "reject" in allowed:
            options.append(("n", "reject"))
        if "edit" in allowed:
            options.append(("e", "edit"))

        hint = " / ".join(f"{key}={label}" for key, label in options)
        keys_display = "/".join(o[0] for o in options)
        choice = input(f"请选择 [{keys_display}] ({hint}): ").strip().lower()

        decision_key = None
        for key, label in options:
            if choice in (key, label):
                decision_key = label
                break
        if decision_key is None and options:
            decision_key = options[0][1]

        if decision_key == "approve":
            decisions.append({"type": "approve"})
        elif decision_key == "reject":
            reason = input("可选：拒绝原因（直接回车使用默认）: ").strip()
            d: dict[str, Any] = {"type": "reject"}
            if reason:
                d["message"] = reason
            decisions.append(d)
        elif decision_key == "edit":
            print("请输入修改后的参数 JSON（仅 args，需可被解析为对象）, 例如: {\"email\": \"x@y.com\"}")
            raw = input("JSON: ").strip()
            try:
                new_args = json.loads(raw)
            except json.JSONDecodeError as e:
                raise ValueError(f"参数 JSON 无效: {e}") from e
            decisions.append(
                {
                    "type": "edit",
                    "edited_action": {"name": name, "args": new_args},
                }
            )
        else:
            decisions.append({"type": "approve"})

    return decisions


async def chat(query: str, thread_id: str) -> None:
    config = RunnableConfig(configurable={"thread_id": thread_id})
    pending: Any = {"messages": [HumanMessage(content=query)]}

    print("助手: ", end="", flush=True)
    while True:
        async for event in deep_agent.astream_events(
            pending,
            config=config,
            version="v2",
        ):
            kind = event.get("event")
            if kind == "on_tool_start":
                data = event.get("data") or {}
                print(
                    f"\n[工具开始] {event.get('name')} 输入: {data.get('input')}",
                    flush=True,
                )
            elif kind == "on_tool_end":
                data = event.get("data") or {}
                print(
                    f"[工具结束] {event.get('name')} 输出: {data.get('output')}\n",
                    flush=True,
                )
                print("助手: ", end="", flush=True)
            elif kind == "on_chat_model_stream":
                chunk = (event.get("data") or {}).get("chunk")
                text = _stream_chunk_text(chunk)
                if text:
                    print(text, end="", flush=True)

        print()

        state = await deep_agent.aget_state(config)
        hitl_payload = _hitl_payload_from_state(state)

        if hitl_payload is not None:
            try:
                decisions = _collect_hitl_decisions(hitl_payload)
            except ValueError as e:
                print(f"输入无效，已中止: {e}")
                return
            pending = Command(resume={"decisions": decisions})
            print("助手: ", end="", flush=True)
            continue
        break


if __name__ == "__main__":
    thread_id = str(uuid.uuid4())
    while True:
        query = input("请输入问题: ")
        if query.lower() in ["exit", "quit"]:
            break
        asyncio.run(chat(query, thread_id))
    print("程序结束")
