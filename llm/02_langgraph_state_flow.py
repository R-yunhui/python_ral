"""LangGraph 最小示例：状态图 + 条件分支."""

from __future__ import annotations

import os
from typing import Literal, TypedDict

from langchain.chat_models import init_chat_model
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.graph import END, START, StateGraph


class AppState(TypedDict):
    query: str
    intent: Literal["learn", "other"]
    answer: str


def build_model():
    if os.getenv("USE_REAL_LLM") == "1":
        return init_chat_model("openai:gpt-4.1-mini", temperature=0)
    return FakeListChatModel(
        responses=[
            "你可以先学 LangChain 的组件，再学 LangGraph 的状态图，最后做多代理实践。",
        ]
    )


def router_node(state: AppState) -> AppState:
    text = state["query"].lower()
    if any(word in text for word in ["learn", "study", "学习", "langchain", "langgraph"]):
        state["intent"] = "learn"
    else:
        state["intent"] = "other"
    return state


def learn_node(state: AppState) -> AppState:
    model = build_model()
    msg = model.invoke(f"给这个学习请求一个简短建议：{state['query']}")
    state["answer"] = msg.content if isinstance(msg.content, str) else str(msg.content)
    return state


def other_node(state: AppState) -> AppState:
    state["answer"] = "这是一个非学习类问题。你可以继续扩展更多节点处理它。"
    return state


def route_by_intent(state: AppState) -> Literal["learn", "other"]:
    return state["intent"]


def main() -> None:
    graph = StateGraph(AppState)
    graph.add_node("router", router_node)
    graph.add_node("learn", learn_node)
    graph.add_node("other", other_node)

    graph.add_edge(START, "router")
    graph.add_conditional_edges("router", route_by_intent, {"learn": "learn", "other": "other"})
    graph.add_edge("learn", END)
    graph.add_edge("other", END)

    app = graph.compile()

    result = app.invoke({"query": "我想学习 LangGraph", "intent": "other", "answer": ""})
    print("=== LangGraph 状态流结果 ===")
    print(result["answer"])


if __name__ == "__main__":
    main()
