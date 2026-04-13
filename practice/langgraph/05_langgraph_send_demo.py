# Send API 并行执行 demo
# 动态创建多个并行任务，每个任务携带独立的输入状态
import time
from typing import TypedDict, Annotated
from operator import add

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send


# ===== 1. 定义 State =====

class ResearchState(TypedDict):
    """主状态：包含查询列表和汇总结果"""

    queries: list[str]  # 要并行处理的查询列表
    findings: Annotated[list, add]  # 所有研究结果自动汇总


# ===== 2. 定义每个 Send 任务的独立输入 =====

class ResearchTaskInput(TypedDict):
    """单个研究任务的输入（隔离的，不是全量 State）"""

    query: str


# ===== 3. 定义节点 =====

def kick_off_node(state: ResearchState) -> dict:
    """分发节点：仅标记开始，不返回 Send"""
    queries = state["queries"]
    print(f">>> kick_off: 收到 {len(queries)} 个查询，准备并行处理")
    return {}  # 节点必须返回 dict，不能返回 list


def route_to_researchers(state: ResearchState) -> list[Send]:
    """路由函数：返回 Send 列表，LangGraph 会并行调度"""
    return [Send("researcher", ResearchTaskInput(query=q)) for q in state["queries"]]


def researcher(task_input: ResearchTaskInput) -> dict:
    """研究节点：处理单个查询（会被并行调用多次）"""
    query = task_input["query"]
    start = time.perf_counter()

    # 模拟不同查询耗时不同
    sleep_map = {"Python": 3, "Go": 5, "Rust": 7}
    time.sleep(sleep_map.get(query, 2))

    elapsed = time.perf_counter() - start
    print(f">>> researcher('{query}') 完成, 耗时: {elapsed:.2f}秒")

    return {"findings": [f"[{query}] 研究结果 - 耗时 {elapsed:.1f}秒"]}


def summarize(state: ResearchState) -> dict:
    """汇总节点：等所有 researcher 完成后执行"""
    findings = state["findings"]
    print(f">>> summarize: 收到 {len(findings)} 条研究结果")
    for f in findings:
        print(f"  - {f}")
    return {}  # 不需要更新 state，只是打印


# ===== 4. 构建图 =====

def build_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("kick_off", kick_off_node)
    graph.add_node("researcher", researcher)
    graph.add_node("summarize", summarize)

    graph.add_edge(START, "kick_off")

    # kick_off 节点走路由函数，返回 Send 列表 = 动态并行
    graph.add_conditional_edges("kick_off", route_to_researchers, ["researcher"])

    # 所有 researcher 完成后汇聚到 summarize
    graph.add_edge("researcher", "summarize")
    graph.add_edge("summarize", END)

    return graph.compile()


# ===== 5. 运行 =====

if __name__ == "__main__":
    app = build_graph()

    result = app.invoke(
        input={
            "queries": ["Python", "Go", "Rust"],
            "findings": [],
        }
    )

    print(f"\n最终结果: {result['findings']}")
