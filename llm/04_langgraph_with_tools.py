"""LangGraph 进阶示例：状态图中调用工具并按条件路由."""

from __future__ import annotations

from typing import Literal, TypedDict

from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph


class ToolState(TypedDict):
    a: int
    b: int
    operation: Literal["add", "multiply"]
    result: int
    answer: str


@tool
def add_tool(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


@tool
def multiply_tool(a: int, b: int) -> int:
    """Multiply two integers."""
    return a * b


def choose_operation(state: ToolState) -> ToolState:
    # 这里只做占位，真实项目可以接入模型判断 intent。
    return state


def add_node(state: ToolState) -> ToolState:
    state["result"] = add_tool.invoke({"a": state["a"], "b": state["b"]})
    state["answer"] = f"加法结果: {state['a']} + {state['b']} = {state['result']}"
    return state


def multiply_node(state: ToolState) -> ToolState:
    state["result"] = multiply_tool.invoke({"a": state["a"], "b": state["b"]})
    state["answer"] = f"乘法结果: {state['a']} * {state['b']} = {state['result']}"
    return state


def route(state: ToolState) -> Literal["add", "multiply"]:
    return state["operation"]


def build_graph():
    graph = StateGraph(ToolState)
    graph.add_node("choose", choose_operation)
    graph.add_node("add", add_node)
    graph.add_node("multiply", multiply_node)

    graph.add_edge(START, "choose")
    graph.add_conditional_edges("choose", route, {"add": "add", "multiply": "multiply"})
    graph.add_edge("add", END)
    graph.add_edge("multiply", END)
    return graph.compile()


def main() -> None:
    app = build_graph()

    add_case = app.invoke({"a": 7, "b": 5, "operation": "add", "result": 0, "answer": ""})
    multiply_case = app.invoke({"a": 7, "b": 5, "operation": "multiply", "result": 0, "answer": ""})

    print("=== LangGraph + Tools 示例 ===")
    print(add_case["answer"])
    print(multiply_case["answer"])


if __name__ == "__main__":
    main()
