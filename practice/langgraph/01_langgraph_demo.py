# langgraph demo
import os
import asyncio
import json
import logging

from dotenv import load_dotenv
from typing import Any, Literal, Optional, TypedDict

# langchain 相关
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

# langgraph 相关
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

# pydantic 相关
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt
from pydantic import Field

# 模型服务
from chat_model_service import chat_model_service

# 提示词
from prompt import (
    GENERATE_REPORT_SYSTEM_PROMPT,
    EVALUATE_REPORT_SYSTEM_PROMPT,
    GENERATE_REPORT_HUMAN_PROMPT,
    EVALUATE_REPORT_HUMAN_PROMPT,
)

MAX_REGENERATE_COUNT = 3

MAX_EVALUATE_SCORE = 85


# 加载环境变量
load_dotenv()

# 暂时使用内存记忆
checkpointer = InMemorySaver()

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format=_LOG_FORMAT,
    datefmt=_LOG_DATEFMT,
)
logger = logging.getLogger(__name__)


# 创建状态类
class ReportAgentState(TypedDict):

    original_query: Optional[str] = Field(default="", description="用户的原始输入")

    report_content: Optional[str] = Field(default="", description="报告内容")

    evaluate_score: Optional[float] = Field(default=0.0, description="评价得分")

    evaluate_content: Optional[str] = Field(default="", description="评价内容")

    regenerate_count: Optional[int] = Field(default=0, description="重试次数")

    answer: Optional[str] = Field(default="", description="回答内容")

    user_id: Optional[str] = Field(default="", description="用户ID")

    confirm_generate_report: Optional[bool] = Field(
        default=None, description="是否在生成报告前已确认执行"
    )

    confirm_regenerate: Optional[bool] = Field(
        default=None, description="是否在重试生成报告前已确认执行"
    )


def extract_json(content: str) -> dict[str, Any] | None:
    if not content:
        return None
    try:
        cleaned = content.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        preview = (cleaned[:200] + "…") if len(cleaned) > 200 else cleaned
        logger.error("JSON 解析失败: %s | 片段: %r", e, preview)
        return None


def _prompt_confirm_generate(interrupts: Any) -> str:
    """在本地终端阻塞读取，返回「是」或「否」，供 Command(resume=...) 使用。"""
    print("\n---------- 人工确认 ----------")
    if interrupts:
        seq = interrupts if isinstance(interrupts, (list, tuple)) else (interrupts,)
        for i, item in enumerate(seq):
            val = getattr(item, "value", item)
            print(f"[interrupt {i}] {val}")
    while True:
        line = input("是否根据上述主题生成报告？请输入「是」或「否」后回车: ").strip()
        if line in ("是", "否"):
            return line
        print("无效输入，请只输入「是」或「否」（不含引号）。")


# 定义图中的节点
async def human_confirm_generate_report_node(state: ReportAgentState) -> dict[str, Any]:
    logger.info("节点开始: human_confirm_generate_report_node")
    payload = {
        "step": "confirm_generate",
        "message": "请确认是否根据下列主题生成报告（resume 可传「是」/「否」）",
        "original_query": state.get("original_query") or "",
    }
    decision = interrupt(payload)
    # 定死暂时
    confirmed = True if decision == "是" else False
    logger.info("用户确认结果: confirmed=%s, raw=%r", confirmed, decision)
    return {"confirm_generate_report": confirmed}


async def generate_report_node(state: ReportAgentState) -> dict[str, Any]:
    logger.info("节点开始: generate_report_node")

    regenerate_count = state.get("regenerate_count", 0)

    evaluate_content = state.get("evaluate_content", None)
    evaluate_score = state.get("evaluate_score", None)
    if evaluate_content is not None and evaluate_score is not None:
        logger.info(
            "沿用上一轮评价: score=%s, regenerate_count=%s",
            evaluate_score,
            regenerate_count,
        )
    else:
        logger.info("无上一轮评价，regenerate_count=%s", regenerate_count)

    logger.info("调用模型生成报告")
    system_message = SystemMessage(content=GENERATE_REPORT_SYSTEM_PROMPT)
    human_message = HumanMessage(
        content=GENERATE_REPORT_HUMAN_PROMPT.format(
            original_query=state.get("original_query", ""),
            evaluate_content=evaluate_content,
        )
    )

    report_content = ""
    for chunk in chat_model_service.chat_model.stream(
        input=[
            system_message,
            human_message,
        ]
    ):
        report_content += chunk.content

    logger.info("报告生成完成，长度=%d 字符", len(report_content))
    logger.debug("报告全文: %s", report_content)

    if evaluate_content:
        regenerate_count += 1

    return {
        "report_content": report_content,
        "regenerate_count": regenerate_count,
    }


async def evaluate_report_node(state: ReportAgentState) -> dict[str, Any]:
    logger.info("节点开始: evaluate_report_node")

    report_content = state.get("report_content", "")
    if report_content:
        logger.info("待评价报告长度=%d 字符", len(report_content))
        logger.debug("待评价报告全文: %s", report_content)
    else:
        logger.warning("待评价报告为空")

    logger.info("调用模型评价报告")
    system_message = SystemMessage(content=EVALUATE_REPORT_SYSTEM_PROMPT)
    human_message = HumanMessage(
        content=EVALUATE_REPORT_HUMAN_PROMPT.format(
            original_query=state["original_query"], report_content=report_content
        )
    )

    evaluate_result = ""
    for chunk in chat_model_service.chat_model.stream(
        input=[
            system_message,
            human_message,
        ]
    ):
        evaluate_result += chunk.content

    logger.info("模型原始评价输出长度=%d 字符", len(evaluate_result))
    logger.debug("模型原始评价输出: %s", evaluate_result)

    evaluate_result = extract_json(evaluate_result)

    if evaluate_result:
        evaluate_content = evaluate_result["evaluate_content"]
        evaluate_score = evaluate_result["evaluate_score"]
        logger.info(
            "解析评价成功: evaluate_score=%s, content_len=%d",
            evaluate_score,
            len(evaluate_content or ""),
        )
    else:
        evaluate_content = ""
        evaluate_score = 0
        logger.warning("解析评价失败，已使用空内容与 0 分")

    return {
        "evaluate_content": evaluate_content,
        "evaluate_score": evaluate_score,
    }


def after_user_confirm_condition(
    state: ReportAgentState,
) -> Literal["generate_report_node", "cancel_report_node"]:
    if state.get("confirm_generate_report"):
        return "generate_report_node"
    return "cancel_report_node"


async def regenerate_report_condition(
    state: ReportAgentState,
) -> Literal["generate_report_node", "answer_node", "human_confirm_regenerate_node"]:
    evaluate_score = state.get("evaluate_score", 0)
    # 控制一下，最多重试三次，防止无限循环
    if evaluate_score <= MAX_EVALUATE_SCORE:
        if state.get("regenerate_count", 0) < MAX_REGENERATE_COUNT:
            return "human_confirm_regenerate_node"
        else:
            return "generate_report_node"
    else:
        return "answer_node"


async def human_confirm_regenerate_node(state: ReportAgentState) -> dict[str, Any]:
    logger.info("节点开始: human_confirm_regenerate_node")

    evaluate_score = state.get("evaluate_score")
    interrupt_payload = {
        "step": "human_confirm_regenerate_node",
        "message": f"当前评估次数已达到最大重试次数 {MAX_REGENERATE_COUNT} ，当前最新评估分值: {evaluate_score}。是否继续重试？",
    }
    decision = interrupt(interrupt_payload)
    confirmed = True if decision == "是" else False
    logger.info("用户确认结果: confirmed=%s, raw=%r", confirmed, decision)
    return {"confirm_regenerate": confirmed}


async def after_user_confirm_regenerate_condition(
    state: ReportAgentState,
) -> Literal["generate_report_node", "answer_node"]:
    if state.get("confirm_regenerate"):
        return "generate_report_node"
    return "answer_node"


async def cancel_report_node(state: ReportAgentState) -> dict[str, Any]:
    logger.info("节点开始: cancel_report_node")
    return {
        "answer": "用户已经取消，未生成报告。",
        "report_content": "",
    }


async def answer_node(state: ReportAgentState) -> dict[str, Any]:
    return {
        "answer": "用户已经生成完成报告",
    }


# 创建图
async def create_report_agent_graph() -> CompiledStateGraph[ReportAgentState]:
    graph = StateGraph(ReportAgentState)

    graph.add_node(
        "human_confirm_generate_report_node", human_confirm_generate_report_node
    )
    graph.add_node("generate_report_node", generate_report_node)
    graph.add_node("evaluate_report_node", evaluate_report_node)
    graph.add_node("human_confirm_regenerate_node", human_confirm_regenerate_node)
    graph.add_node("cancel_report_node", cancel_report_node)
    graph.add_node("answer_node", answer_node)

    graph.add_edge(START, "human_confirm_generate_report_node")
    graph.add_conditional_edges(
        "human_confirm_generate_report_node",
        after_user_confirm_condition,
        {
            "generate_report_node": "generate_report_node",
            "cancel_report_node": "cancel_report_node",
        },
    )
    graph.add_edge("generate_report_node", "evaluate_report_node")
    graph.add_conditional_edges(
        source="evaluate_report_node",
        path=regenerate_report_condition,
        path_map={
            "generate_report_node": "generate_report_node",
            "answer_node": "answer_node",
            "human_confirm_regenerate_node": "human_confirm_regenerate_node",
        },
    )
    graph.add_edge("cancel_report_node", END)
    graph.add_edge("answer_node", END)

    return graph.compile(
        checkpointer=checkpointer,
        name="report_agent_graph",
    )


async def chat(query: str, user_id: str) -> dict[str, Any]:
    """首次运行会在确认节点 interrupt；必须在本地终端输入「是」或「否」后才会继续执行。"""
    graph = await create_report_agent_graph()
    config = RunnableConfig(
        configurable={
            "thread_id": user_id,
            "user_id": user_id,
        },
    )

    result = await graph.ainvoke(
        input={
            "original_query": query,
            "user_id": user_id,
        },
        config=config,
    )

    if result.get("__interrupt__"):
        logger.info("收到 interrupt，等待终端输入确认…")
        resume_value = await asyncio.to_thread(
            _prompt_confirm_generate,
            result["__interrupt__"],
        )
        result = await graph.ainvoke(
            Command(resume=resume_value),
            config=config,
        )

    logger.info(
        "图执行结束: report_content_len=%d",
        len(result.get("report_content") or ""),
    )
    logger.debug("最终报告内容: %s", result.get("report_content"))
    return result


if __name__ == "__main__":
    import uuid

    user_id = str(uuid.uuid4())
    asyncio.run(chat("写一篇关于成都春天的文章", user_id))
