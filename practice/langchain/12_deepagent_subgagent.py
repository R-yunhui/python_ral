import os
import requests
import asyncio
import httpx

from dotenv import load_dotenv
from typing import Literal
from pathlib import Path
from datetime import datetime

# uapi
from uapi import UapiClient
from uapi.errors import UapiError

# langchain
from langchain_core.tools import tool
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

# deepagents
from deepagents import create_deep_agent
from deepagents.middleware import SubAgent
from deepagents.backends.filesystem import FilesystemBackend

# langgraph
from langgraph.checkpoint.memory import InMemorySaver

# 加载环境变量
load_dotenv()

checkpointer = InMemorySaver()

uapi_client = UapiClient("https://uapis.cn", token=os.getenv("UAPI_KEY"))


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


@tool(
    description="使用Bocha Web Search API 进行网页搜索。",
    args_schema={
        "query": {"type": "string", "description": "搜索关键词"},
        "count": {
            "type": "integer",
            "description": "返回的搜索结果数量",
            "default": 10,
        },
        "freshness": {
            "type": "string",
            "enum": ["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"],
            "description": "搜索的时间范围",
            "default": "noLimit",
        },
        "summary": {
            "type": "boolean",
            "description": "是否显示文本摘要",
            "default": True,
        },
    },
)
async def bocha_websearch_tool(
    query: str,
    count: int = 10,
    freshness: Literal[
        "oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"
    ] = "noLimit",
    summary: bool = True,
) -> str:
    """
    使用Bocha Web Search API 进行网页搜索。

    参数:
    - query: 搜索关键词
    - freshness: 搜索的时间范围
    - summary: 是否显示文本摘要
    - count: 返回的搜索结果数量

    返回:
    - 搜索结果的详细信息，包括网页标题、网页URL、网页摘要、网站名称、网站Icon、网页发布时间等。
    """

    url = os.getenv("WEB_SEARCH_URL")
    headers = {
        "Authorization": f'Bearer {os.getenv("WEB_SEARCH_KEY")}',
        "Content-Type": "application/json",
    }
    data = {
        "query": query,
        "freshness": freshness,  # 搜索的时间范围，例如 "oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"
        "summary": summary,  # 是否返回长文本摘要
        "count": count,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=data)
        if response.status_code == 200:
            json_response = response.json()
            try:
                if json_response["code"] != 200 or not json_response["data"]:
                    return f"搜索API请求失败，原因是: {response.msg or '未知错误'}"

                webpages = json_response["data"]["webPages"]["value"]
                if not webpages:
                    return "未找到相关结果。"
                formatted_results = ""
                for idx, page in enumerate(webpages, start=1):
                    formatted_results += (
                        f"引用: {idx}\n"
                        f"标题: {page['name']}\n"
                        f"URL: {page['url']}\n"
                        f"摘要: {page['summary']}\n"
                        f"网站名称: {page['siteName']}\n"
                        f"网站图标: {page['siteIcon']}\n"
                        f"发布时间: {page['dateLastCrawled']}\n\n"
                    )
                return formatted_results.strip()
            except Exception as e:
                return f"搜索API请求失败，原因是：搜索结果解析失败 {str(e)}"
        else:
            return f"搜索API请求失败，状态码: {response.status_code}, 错误信息: {response.json()}"


@tool(
    description="实时查询指定城市的天气数据，支持国内和国际城市。",
    args_schema={
        "city": {"type": "string", "description": "城市名称"},
        "adcode": {"type": "string", "description": "行政区编码"},
        "lang": {"type": "string", "enum": ["zh", "en"], "description": "语言"},
    },
)
def real_time_weather_query(city: str, adcode: str = None, lang: Literal["zh", "en"] = "zh") -> str:
    """
    为你提供精准、实时的天气数据，支持国内和国际城市。

    ## 功能概述
    这个接口支持三种查询方式：
    - 可以传 `adcode`，按行政区编码查询（优先级最高）
    - 可以传 `city`，按城市名称查询，支持中文（`北京`）和英文（`Tokyo`）
    - 两个都不传时，按客户端 IP 自动定位查询

    支持 `lang` 参数，可选 `zh`（默认）和 `en`，城市名翻译覆盖 7000+ 城市。

    ## 可选功能模块
    - `extended=true`：扩展气象字段（体感温度、能见度、气压、紫外线、空气质量及污染物分项数据）
    - `forecast=true`：多天预报（最多7天，含日出日落、风速等详细数据）
    - `hourly=true`：逐小时预报（24小时）
    - `minutely=true`：分钟级降水预报（仅国内城市）
    - `indices=true`：18项生活指数（穿衣、紫外线、洗车、运动、花粉等）
    """
    try:
        weather = uapi_client.misc.get_misc_weather(city=city, adcode=adcode, lang=lang)
        return weather
    except UapiError as e:
        return f"天气查询API请求失败，原因是：{str(e)}"

PLATFORM_TYPE = [
    "bilibili", "acfun", "weibo", 
    "zhihu", "zhihu-daily", "douyin", 
    "kuaishou", "douban-movie", "douban-group", 
    "tieba", "hupu", "ngabbs", "v2ex", 
    "52pojie", "hostloc", "coolapk", "baidu", 
    "thepaper", "toutiao", "qq-news", "sina",
    "sina-news", "netease-news", "huxiu", 
    "ifanr", "sspai", "ithome", 
    "ithome-xijiayi", "juejin", "jianshu", 
    "guokr", "36kr", "51cto", 
    "csdn", "nodeseek", "hellogithub", 
    "lol", "genshin", "honkai", 
    "starrail", "netease-music", "qq-music", 
    "weread", "weatheralarm", "earthquake", "history"
]


@tool(
    description="查询指定平台的热榜数据列表。",
    args_schema={
        "type": {
            "type": "string",
            "enum": [str(platform) for platform in PLATFORM_TYPE],
            "description": "你想要查询的热榜平台类型",
        },
        "time": {
            "type": "int",
            "description": "时光机模式：毫秒时间戳，返回最接近该时间的热榜快照。不传则返回当前实时热榜。",
        },
        "keyword": {
            "type": "string",
            "description": "搜索模式：搜索关键词，在历史热榜中搜索包含该关键词的条目。需配合 time_start 和 time_end 使用。",
        },
        "time_start": {
            "type": "int",
            "description": "搜索模式必填：搜索起始时间戳（毫秒）。",
        },
        "time_end": {
            "type": "int",
            "description": "搜索模式必填：搜索结束时间戳（毫秒）。",
        },
        "limit": {
            "type": "integer",
            "description": "搜索模式下最大返回条数，默认 50，最大 200。",
            "default": 10,
        },
    },
)
def hot_list_query(
    type: Literal[PLATFORM_TYPE] = "weibo",
    time: int = None,
    keyword: str = None,
    time_start: int = None,
    time_end: int = None,
    limit: int = 10,
) -> str:
    """
    查询指定平台的热榜数据列表。

    type:

    ## 功能概述
    你只需要指定一个平台类型，就能获取到该平台当前的热榜数据列表。每个热榜条目都包含标题、热度值和原始链接。非常适合用于制作信息聚合类应用或看板。

    ## 三种使用模式

    ### 默认模式
    只传 `type` 参数，返回该平台当前的实时热榜。

    ### 时光机模式
    传 `type` + `time` 参数，返回最接近指定时间的热榜快照。如果不可用或无数据，会返回空。

    ### 搜索模式
    传 `type` + `keyword` + `time_start` + `time_end` 参数，在指定时间范围内搜索包含关键词的热榜条目。可选传 `limit` 限制返回数量。

    ### 数据源列表
    传 `sources=true`，返回所有支持历史数据的平台列表。

    ## 可选值
    PLATFORM_TYPE
    """
    try:
        host_list = uapi_client.misc.get_misc_hotboard(
            type=type,
            time=time,
            keyword=keyword,
            time_start=time_start,
            time_end=time_end,
            limit=limit,
        )
        return host_list
    except UapiError as e:
        return f"热门列表查询API请求失败，原因是：{str(e)}"


deep_agent = create_deep_agent(
    model=chat_model,
    system_prompt=SystemMessage(content="你是一个助手，请根据用户的问题，给出回答。"),
    subagents=[
        SubAgent(
            name="researcher",
            description="研究助手",
            system_prompt="你是一个研究助手，请根据用户的问题，给出回答。",
            model=chat_model,
            tools=[
                bocha_websearch_tool,
            ],
        ),
    ],
    checkpointer=checkpointer,
    backend=FilesystemBackend(root_dir=str(Path(__file__).parent), virtual_mode=True),
    tools=[
        bocha_websearch_tool,
        real_time_weather_query,
        hot_list_query,
    ],
)


async def chat(query: str):
    user_query = f"""
        用户问题: {query},
        当前时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    """

    async for event in deep_agent.astream_events(
        input={"messages": [HumanMessage(content=user_query)]},
        stream_mode="messages",
        config=RunnableConfig(
            configurable={"thread_id": "thread-1"},
        ),
        version="v1",
    ):
        kind = event.get("event")
        # 处理工具调用流
        if kind == "on_tool_start":
            print(f"开始调用工具, 工具名称: {event['name']}")
        elif kind == "on_tool_end":
            print(
                f"完成工具调用, 工具名称: {event['name']}, 工具执行结果: {event['data']['output']}"
            )
        # 处理 LLM 对话内容流
        elif kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and chunk.content:
                print(chunk.content, end="", flush=True)
    print()


if __name__ == "__main__":
    query = input("请输入问题, 输入 exit 或 quit 退出: ").strip()
    while query not in ["exit", "quit"]:
        asyncio.run(chat(query))
        query = input("请输入问题, 输入 exit 或 quit 退出: ").strip()
    print("再见!")
