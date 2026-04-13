# 并行节点执行
import os
import time
import uuid

from dotenv import load_dotenv
from typing import TypedDict, Dict, Any

# langchain 相关
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

# langgraph 相关
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph


# 加载环境变量
load_dotenv()

# 暂时使用内存存储上下文信息


checkpointer = InMemorySaver()


class AgentState(TypedDict):

    original_query: str

    search_web_content: str

    search_knowledge_content: str

    search_db_content: str

    answer: str


def search_web_node(state: AgentState) -> Dict[str, Any]:

    print(">>> 开始执行 search_web_node")

    start_time = time.perf_counter()

    original_query = state.get("original_query")

    print(f"用户的问题是：{original_query}")

    time.sleep(5)

    elapsed_time = time.perf_counter() - start_time

    print(f">>> web_search_node 完成, 耗时: {elapsed_time:.2f} 秒")

    return {
        "search_web_content": "web_search_result",
    }


def search_knowledge_node(state: AgentState) -> Dict[str, Any]:

    print(">>> 开始执行 search_knowledge_node")

    start_time = time.perf_counter()

    original_query = state.get("original_query")

    print(f"用户的问题是：{original_query}")

    time.sleep(10)

    elapsed_time = time.perf_counter() - start_time

    print(f">>> search_knowledge_node 完成, 耗时: {elapsed_time:.2f} 秒")

    return {
        "search_knowledge_content": "search_knowledge_result",
    }


def search_db_node(state: AgentState) -> Dict[str, Any]:

    print(">>> 开始执行 search_db_node")

    start_time = time.perf_counter()

    original_query = state.get("original_query")

    print(f"用户的问题是：{original_query}")

    time.sleep(15)

    elapsed_time = time.perf_counter() - start_time

    print(f">>> search_db_node 完成, 耗时: {elapsed_time:.2f} 秒")

    return {
        "search_db_content": "search_db_result",
    }


def answer_node(state: AgentState) -> Dict[str, Any]:

    print(">>> 开始执行 answer_node")

    return {
        "answer": "answer_result",
    }


def rewrite_node(state: AgentState) -> Dict[str, Any]:

    print(">>> 开始执行 rewrite_node")

    return {"rewrite_query": "rewrite_query"}


def build_graph() -> CompiledStateGraph[AgentState]:

    graph = StateGraph(AgentState)

    # 预制节点
    graph.add_node("rewrite_node", rewrite_node)
    graph.add_node("search_web_node", search_web_node)
    graph.add_node("search_knowledge_node", search_knowledge_node)
    graph.add_node("search_db_node", search_db_node)
    graph.add_node("answer_node", answer_node)

    # 预制边
    graph.add_edge(START, "rewrite_node")
    # 并行扇出：从 rewrite_node 同时触发 3 个搜索节点
    graph.add_conditional_edges(
        "rewrite_node",
        lambda s: ["search_web_node", "search_knowledge_node", "search_db_node"],
    )
    # 所有搜索节点汇聚到 answer_node
    graph.add_edge("search_web_node", "answer_node")
    graph.add_edge("search_knowledge_node", "answer_node")
    graph.add_edge("search_db_node", "answer_node")
    graph.add_edge("answer_node", END)

    complle_graph = graph.compile()

    return complle_graph


def main():
    agent_state = {"original_query": "你好"}

    user_id = str(uuid.uuid4())

    graph = build_graph()

    config = RunnableConfig(
        configurable={
            "thread_id": user_id,
        },
    )

    ans = graph.invoke(input=agent_state, config=config)

    print(ans)


if __name__ == "__main__":
    main()
