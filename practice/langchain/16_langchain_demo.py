# langchain  chain 和 agent
import asyncio
import os

from dotenv import load_dotenv

# Pydantic
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

# langchain
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.agents import create_agent


load_dotenv()


class CityInfo(BaseModel):
    """地理信息；兼容模型返回中文键名或单元素数组。"""

    model_config = ConfigDict(populate_by_name=True)

    province: str = Field(
        default="",
        validation_alias=AliasChoices("province", "省份"),
        description="省份名称",
    )
    city: str = Field(
        default="",
        validation_alias=AliasChoices("city", "城市"),
        description="城市名称",
    )
    country: str = Field(
        default="",
        validation_alias=AliasChoices("country", "国家"),
        description="国家名称",
    )

    @model_validator(mode="before")
    @classmethod
    def unwrap_single_element_list(cls, data: object) -> object:
        if isinstance(data, list) and data:
            return data[0]
        return data


# 结构化输出建议关闭 streaming；DashScope 的 json 模式要求 messages 含 json 字样（见 system 提示）
chat_model = ChatOpenAI(
    model=os.getenv("QWEN_CHAT_MODEL") or "qwen-plus",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    streaming=False,
    extra_body={
        "enable_thinking": False,
    },
    # model_kwargs={
    #     "stream_options": {
    #         "include_usage": True,
    #     },
    # },
)

structured_llm = chat_model.with_structured_output(CityInfo, method="json_mode")


agent = create_agent(
    model=chat_model,
    tools=[],
    system_prompt=SystemMessage(content="""
                从用户描述中抽取省份、城市、国家；无法确定时对应字段用空字符串。
                只输出一个 JSON 对象，不要输出数组。
                键名必须使用英文：province, city, country。
                请使用 JSON 格式回答。
                """),
    response_format=CityInfo,
)


async def chat(query: str) -> CityInfo:
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(
                content="""
                          从用户描述中抽取省份、城市、国家；无法确定时对应字段用空字符串。
                          只输出一个 JSON 对象，不要输出数组。
                          键名必须使用英文：province, city, country。
                          请使用 JSON 格式回答。
                          """
            ),
            HumanMessage(content=query),
        ]
    )

    # method 默认是 function_calling
    chain = prompt | structured_llm
    return await chain.ainvoke({"query": query}, verbose=True)


async def chat_with_agent(query: str) -> CityInfo:
    result = await agent.ainvoke(
        input={"messages": [HumanMessage(content=query)]},
    )
    # create_agent 的 response_format 会在 state 中写入 structured_response
    return result["structured_response"]

async def main() -> None:
    cases = [
        "浙江省杭州市在中华人民共和国。",
        "我住在广东省深圳市。",
        "东京是日本的首都。",
        "我是谁阿",
    ]
    results = await asyncio.gather(
        *(chat_with_agent(case) for case in cases),
        return_exceptions=True,
    )
    for case, result in zip(cases, results, strict=True):
        print("Q:", case)
        if isinstance(result, Exception):
            print("  error:", result)
        else:
            print(" ", result.model_dump())
        print("-" * 40)


if __name__ == "__main__":
    asyncio.run(main())
