import os
import logging
import asyncio
import questionary

from typing import Any, Callable, Literal
from dotenv import load_dotenv

# langchain 相关
from langchain.agents.middleware.types import after_model, wrap_tool_call
from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables.config import RunnableConfig
from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentState,
    HumanInTheLoopMiddleware,
    InterruptOnConfig,
    SummarizationMiddleware,
    ToolCallRequest,
    ToolCallLimitMiddleware,
)

# langgraph 相关
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.runtime import Runtime
from langgraph.types import Command

# 模型服务
from chat_model_service import chat_model_service

# 加载环境变量
load_dotenv()

# 暂定内存记忆
checkpointer = InMemorySaver()

# 使用 token 计数回调
usage_callback = UsageMetadataCallbackHandler()

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format=_LOG_FORMAT,
    datefmt=_LOG_DATEFMT,
)
logger = logging.getLogger(__name__)

# 定义一些 middleware
summarization_middleware = SummarizationMiddleware(
    # 摘要模型
    model=chat_model_service.chat_model_flash,
    # 摘要触发点：当消息数达到 30 条或 token 数达到 3000 时，触发摘要
    trigger=[("messages", 10), ("tokens", 3000)],
    # 摘要保留：保留最近 10 条消息
    keep=("messages", 5),
    # 摘要长度：摘要长度为 500 个 token，超过 500 个 token 的摘要将被截断
    trim_tokens_to_summarize=500,
)


tool_call_limit_middleware = ToolCallLimitMiddleware(
    # 只限制某一个工具的名字；None 表示统计所有工具
    tool_name="calculate",
    # 在同一条会话（thread_id）下，允许的工具调用次数上限；None 表示不按 thread 限制。跨多次 invoke 累计时，需要 checkpointer，否则 thread 维度记不住。
    thread_limit=None,
    # 单次用户侧调用（一次 invoke/astream 这一轮）内的工具调用上限；None 表示不按 run 限制。
    run_limit=3,
    # 可选："continue"（默认）/ "error" / "end"
    # continue: 对超限的 tool call 注入错误内容的 ToolMessage（status="error"），模型看到「不要再调该工具」；其它未超限的调用仍可继续。
    # error: 抛出 ToolCallLimitExceededError，整次执行中断，便于外层 try/except。
    # end: 注入 ToolMessage + 一条说明超限的 AIMessage，并 jump_to: "end" 直接结束。限制：若同一条 AI 里还有其它待执行的工具调用（例如并行多工具），会 NotImplementedError，文档建议改用 continue 或 error。
    exit_behavior="continue",
)

human_in_the_loop_middleware = HumanInTheLoopMiddleware(
    # 中断条件
    interrupt_on={
        # 工具名：中断条件, True or False or InterruptOnConfig
        "calculate": InterruptOnConfig(
            allowed_decisions=["approve", "reject"],
            description="请确认是否需要调用 calculate 工具?",
        ),
    },
)


@after_model
def after_model_middleware(state: AgentState, runtime: Runtime) -> dict | None:
    """每次调用模型后打印消息数和 token 数"""
    messages = state.get("messages", [])
    n = len(messages)

    model_name = messages[-1].response_metadata.get("model_name", None)
    usage_metadata = usage_callback.usage_metadata.get(model_name)
    total_tokens = usage_metadata.get("total_tokens", 0) if usage_metadata else 0
    input_tokens = usage_metadata.get("input_tokens", 0) if usage_metadata else 0
    output_tokens = usage_metadata.get("output_tokens", 0) if usage_metadata else 0

    logger.info(
        "模型调用完成，当前消息数: %s, 使用 %s 模型，消耗总token: %s, 消耗输入token: %s, 消耗输出token: %s",
        n,
        model_name,
        total_tokens,
        input_tokens,
        output_tokens,
    )
    return None


@wrap_tool_call
async def awrap_tool_call_middleware(
    request: ToolCallRequest,
    handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
) -> ToolMessage | Command:
    tool = request.tool
    logger.info(f"awrap_tool_call_middleware 即将调用工具: {tool.name}")
    logger.info(f"awrap_tool_call_middleware 工具描述: {tool.description}")
    logger.info(f"awrap_tool_call_middleware 工具参数: {tool.args_schema}")
    result = await handler(request)
    logger.info(f"awrap_tool_call_middleware 工具调用完成，返回结果: {result}")
    return result


@tool
async def calculate(
    operation: Literal["+", "-", "*", "/"], a: float, b: float
) -> float:
    """
    计算两个数的四则运算
    Args:
        operation: 运算符 + - * /
        a: 第一个数
        b: 第二个数
    Returns:
        float: 计算结果
    """
    if operation == "+":
        return a + b
    elif operation == "-":
        return a - b
    elif operation == "*":
        return a * b
    elif operation == "/":
        return a / b
    else:
        raise ValueError(f"calculate 工具参数错误: {operation}")


# 创建 agent
agent = create_agent(
    model=chat_model_service.chat_model,
    tools=[calculate],
    system_prompt=SystemMessage(content="你是一个助手，请根据用户的问题，给出回答。"),
    debug=False,
    checkpointer=checkpointer,
    middleware=[
        summarization_middleware,
        after_model_middleware,
        awrap_tool_call_middleware,
        human_in_the_loop_middleware,
    ],
    name="test_agent",
)


def _hitl_interrupt_parts(interrupt_tuple: tuple[Any, ...]) -> tuple[str, list[str]]:
    """解析 `values` 里的 `__interrupt__`，得到日志摘要与每条待审批说明（与 decisions 一一对应）。

    `HumanInTheLoopMiddleware` 把 `InterruptOnConfig.description`（或默认前缀）写入每条
    `ActionRequest.description`。
    """
    log_lines: list[str] = []
    prompts: list[str] = []
    for intr in interrupt_tuple:
        hitl = intr.value
        if not isinstance(hitl, dict):
            log_lines.append(f"(非 dict 载荷: {hitl!r})")
            continue
        for ar in hitl.get("action_requests") or []:
            name = ar.get("name", "?")
            desc = (ar.get("description") or "").strip() or "(无说明)"
            args = ar.get("args", {})
            n = len(prompts) + 1
            log_lines.append(f"  [{n}] 工具={name!r} | {desc} | args={args!r}")
            prompts.append(f"待审批工具 {name}: {desc}")
    summary = "\n".join(log_lines) if log_lines else "(空 interrupt)"
    return summary, prompts


HITL_SELECT_TIMEOUT_SEC = 5.0


async def _prompt_hitl_decision_async(prompt: str) -> dict:
    """用 questionary 选择同意或拒绝；超时未选则默认同意。"""
    q = questionary.select(
        f"{prompt}（{HITL_SELECT_TIMEOUT_SEC:.0f}s 内未选默认同意）",
        choices=[
            questionary.Choice("同意", value="approve"),
            questionary.Choice("拒绝", value="reject"),
        ],
    )
    try:
        main = await asyncio.wait_for(q.ask_async(), timeout=HITL_SELECT_TIMEOUT_SEC)
    except TimeoutError:
        logger.info("HITL 选择超时（%.0fs），默认同意", HITL_SELECT_TIMEOUT_SEC)
        return {"type": "approve"}
    if main is None or main == "approve":
        return {"type": "approve"}
    return {"type": "reject", "message": "用户拒绝执行该工具调用"}


async def chat(query: str, user_id: str) -> None:
    config = RunnableConfig(
        configurable={"thread_id": user_id},
        callbacks=[usage_callback],
    )
    inp: dict | Command = {"messages": [HumanMessage(content=query)]}

    while True:
        interrupted = False
        hitl_action_prompts: list[str] = []
        async for item in agent.astream(
            inp,
            config,
            stream_mode=["messages", "values"],
        ):
            # 多模式： (mode, payload)；若以后开 subgraphs 可能是 (ns, mode, payload)
            if isinstance(item, tuple) and len(item) == 2:
                mode, payload = item
            elif isinstance(item, tuple) and len(item) == 3:
                _, mode, payload = item
            else:
                continue
            if mode == "messages":
                # 文档：常为 (token_chunk, metadata)
                if isinstance(payload, tuple) and len(payload) >= 1:
                    chunk = payload[0]
                    text = getattr(chunk, "content", None) or ""
                    if text:
                        print(text, end="", flush=True)
            elif mode == "values" and isinstance(payload, dict):
                interrupt_payload = payload.get("__interrupt__")
                if interrupt_payload:
                    interrupted = True
                    summary, hitl_action_prompts = _hitl_interrupt_parts(
                        interrupt_payload
                    )
                    logger.info(
                        "HITL __interrupt__（%s 条待审批）:\n%s",
                        len(hitl_action_prompts),
                        summary,
                    )
                    break

        if interrupted:
            prompts = hitl_action_prompts or ["工具调用待审批"]
            decisions: list[dict] = []
            for p in prompts:
                decisions.append(await _prompt_hitl_decision_async(p))
            inp = Command(resume={"decisions": decisions})
            continue
        logger.info("HITL 结束，退出循环")
        break


if __name__ == "__main__":
    import uuid

    user_id = str(uuid.uuid4())

    while True:
        query = input("请输入问题: ").strip()
        if query.lower() in ["exit", "quit"]:
            break
        asyncio.run(chat(query, user_id))
        print()
    logger.info("再见！欢迎下次使用！")
