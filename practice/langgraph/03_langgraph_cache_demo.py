"""
LangGraph 节点级 Cache 示例：仅对指定节点启用缓存。

要点：
- `compile(cache=InMemoryCache())` 提供缓存后端；
- 只有 `add_node(..., cache_policy=CachePolicy(...))` 的节点会参与缓存；
- 缓存的是「该节点产生的 writes」；key 默认由 `CachePolicy.key_func(节点输入)` 决定（见 `langgraph.types.CachePolicy`）。

注意：大模型等不确定输出一般不建议对节点开 cache；本示例用确定性 `upper` 模拟「昂贵步骤」。
"""

from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from langgraph.cache.memory import InMemoryCache
from langgraph.graph import END, START, StateGraph
from langgraph.types import CachePolicy

expensive_runs = 0
plain_runs = 0


class DemoState(TypedDict):
    text: str
    plain_count: NotRequired[int]


def expensive_deterministic_rewrite(state: DemoState) -> dict:
    global expensive_runs
    expensive_runs += 1
    return {"text": state["text"].upper()}


def plain_counter(state: DemoState) -> dict:
    global plain_runs
    plain_runs += 1
    c = int(state.get("plain_count") or 0)
    return {"plain_count": c + 1}


def build_graph():
    builder = StateGraph(DemoState)
    builder.add_node(
        "expensive",
        expensive_deterministic_rewrite,
        cache_policy=CachePolicy(ttl=3600),
    )
    builder.add_node("plain", plain_counter)
    builder.add_edge(START, "expensive")
    builder.add_edge("expensive", "plain")
    builder.add_edge("plain", END)
    return builder.compile(cache=InMemoryCache())


def main() -> None:
    global expensive_runs, plain_runs

    graph = build_graph()
    cfg_a = {"configurable": {"thread_id": "user-a"}}
    cfg_b = {"configurable": {"thread_id": "user-b"}}
    inp = {"text": "hello", "plain_count": 0}

    print("--- 第一次 invoke（thread user-a）---")
    expensive_runs = plain_runs = 0
    out1 = graph.invoke(inp, cfg_a)
    print("out:", out1)
    print(f"expensive_runs={expensive_runs}, plain_runs={plain_runs}\n")

    print("--- 第二次相同输入（thread user-b）：expensive 可走缓存，plain 仍会执行 ---")
    out2 = graph.invoke(inp, cfg_b)
    print("out:", out2)
    print(f"expensive_runs={expensive_runs}, plain_runs={plain_runs}\n")

    print("--- clear_cache 后再 invoke，expensive 会再跑一遍 ---")
    graph.clear_cache()
    expensive_runs = plain_runs = 0
    out3 = graph.invoke(inp, cfg_a)
    print("out:", out3)
    print(f"expensive_runs={expensive_runs}, plain_runs={plain_runs}")


if __name__ == "__main__":
    main()
