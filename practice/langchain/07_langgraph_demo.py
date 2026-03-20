import os
import io
import json


from dotenv import load_dotenv
from typing import Literal, TypedDict, Dict, Any

# 看图
from PIL import Image


from dotenv import load_dotenv


# 加载环境变量
load_dotenv()

# langchain 相关
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai.chat_models import ChatOpenAI

# langgraph 相关
from langgraph.graph import StateGraph, START, END

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


class AgentState(TypedDict):

    original_query: str

    write_content: str

    evaluate_score: str

    evaluate_content: str

    answer: str


def write_node(state: AgentState) -> AgentState:

    print(">>> 开始执行 write_node")

    query = state["original_query"]

    evaluate_content = state.get("evaluate_content", "无评价内容")

    print("上一轮评价内容如下：", evaluate_content)

    write_content = ""
    print("文章内容如下：")
    for chunk in chat_model.stream(
        input=[
            SystemMessage(
                content="你是一个专业的文档写作助手，请根据用户的问题，给出回答。要求输出中文，内容不能超过100字。如果评价内容为空，则根据用户的问题，给出回答。"
            ),
            HumanMessage(
                content=f"用户的问题是：{query}, 根据评价内容，重新生成文档内容。评价内容：{evaluate_content}"
            ),
        ]
    ):
        write_content += chunk.content
        print(chunk.content, end="", flush=True)

    print("\n")

    print("文章内容：", write_content)

    state["write_content"] = write_content

    return state


def evaluate_node(state: AgentState) -> AgentState:

    print(">>> 开始执行 evaluate_node")

    write_content = state["write_content"]

    evaluate_content = ""
    if hasattr(state, "evaluate_content"):
        evaluate_content = state["evaluate_content"]

    evaluate_content = ""
    print("本次评价内容如下：")
    for chunk in chat_model.stream(
        input=[
            SystemMessage(
                content="""
                你是一个专业的文档评价助手，请根据用户的问题，给出评分，评分范围为0-100，0为最差，100为最好，必须严格按照 json 格式输出，
                包含评分和评价内容，评价内容不能超过200字。json 格式为：{"score": 评分, "content": "评价内容"}。
                """
            ),
            HumanMessage(content=f"文档内容是：{write_content}"),
        ]
    ):
        evaluate_content += chunk.content
        print(chunk.content, end="", flush=True)

    print("\n")

    try:
        evaluate_content = evaluate_content.replace("```json", "").replace("```", "")
        evaluate_result = json.loads(evaluate_content)
    except json.JSONDecodeError:
        print("评价结果解析失败：", evaluate_content)
        return {
            "evaluate_score": 0,
            "evaluate_content": "评价结果解析失败",
        }

    evaluate_score = evaluate_result["score"]
    evaluate_content = evaluate_result["content"]

    state["evaluate_score"] = evaluate_score
    state["evaluate_content"] = evaluate_content

    return state


# 1. 路由逻辑：只负责做判断，返回字符串
def route_after_evaluation(state: AgentState) -> Literal["write_node", "answer_node"]:
    print(">>> 正在进行路由判断...")
    score = state.get("evaluate_score", 0)
    if score <= 95:
        print("评分低于等于95，跳回写文章节点")
        return "write_node"  # 跳回写文章节点
    else:
        print("评分高于95，完成任务，跳向结束")
        return "answer_node"  # 完成任务，跳向结束


def answer_node(state: AgentState) -> Dict[str, Any]:
    print(">>> 开始执行 answer_node")

    state["answer"] = state["write_content"]

    return state


def main():
    graph = StateGraph(AgentState)

    graph.add_node("write_node", write_node)
    graph.add_node("evaluate_node", evaluate_node)
    graph.add_node("answer_node", answer_node)

    # 普通边
    graph.add_edge(START, "write_node")
    graph.add_edge("write_node", "evaluate_node")
    graph.add_edge("answer_node", END)

    # 条件边
    graph.add_conditional_edges(
        "evaluate_node",  # 从 evaluate_node 结束后判断
        route_after_evaluation,  # 使用路由逻辑函数
        path_map={
            "write_node": "write_node",
            "answer_node": "answer_node",
        },
    )

    # 构建并编译图
    app_graph = graph.compile()

    # png_data = app_graph.get_graph().draw_mermaid_png()
    # img = Image.open(io.BytesIO(png_data))
    # img.show()

    # print("图结构展示完成, 执行程序...")

    result = app_graph.invoke({"original_query": "写一篇有关于春天的文章"})
    print(result)


if __name__ == "__main__":
    main()
