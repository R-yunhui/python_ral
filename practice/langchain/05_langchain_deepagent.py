import os

from dotenv import load_dotenv

from pathlib import Path

# langchain 相关
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_openai.chat_models import ChatOpenAI

from langgraph.checkpoint.memory import InMemorySaver

# deepagents
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

# 项目根目录（用于 .env 和 skills 路径）
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 加载环境变量（从项目根目录的 .env）
load_dotenv(PROJECT_ROOT / ".env")

checkpointer = InMemorySaver()

# 确保 model 不为 None，避免 ChatOpenAI 校验报错
_model_name = os.getenv("QWEN_CHAT_MODEL") or "qwen-plus"
chat_model = ChatOpenAI(
    model=_model_name,
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    streaming=True,
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    model_kwargs={
        "stream_options": {
            "include_usage": True,
        },
    },
    extra_body={
        "enable_thinking": True,
        "thinking_budget": 100,
    },
)

# deepagents 的 skills 约定（见 https://docs.langchain.com/oss/python/deepagents/skills）：
# - 默认 StateBackend 不读磁盘，需通过 invoke(files={...}) 注入
# - 用本地目录时需 FilesystemBackend(root_dir=..., virtual_mode=True)，skills 为 POSIX 虚拟路径（相对 root_dir）
# 本仓库的 skills 在 .cursor/skills/ 下，每个子目录需有 SKILL.md（YAML frontmatter + 说明）
SKILLS_SOURCE = "/.cursor/skills/"
CURSOR_SKILLS_PATH = Path(__file__).parent.parent / "skills/"
print(f"Skills 目录：{PROJECT_ROOT / '.cursor' / 'skills'}")

deep_agent = create_deep_agent(
    model=chat_model,
    system_prompt=SystemMessage(content='本任务：根据下方上下文**创建一个毕昇(Bisheng)平台的工作流**，输出符合 bisheng-workflow-generator 规范的 JSON，并做自检迭代。\n\n【用户需求分析】\n需求描述：创建深汕招商政策查询助手工作流，支持政策条文查询与解读、匹配适用该政策的企业、查询符合条件的企业信息，需结合知识库与联网检索。\n            工作流类型：混合类型：工具调用 + 知识库检索\n            复杂度：moderate\n            是否需要工具：True\n            是否需要知识库：True\n            是否多轮对话：True\n        \n\n【候选资源（按需选用，不必全部使用）】\n\n候选工具（tool_key 必须原样写入 JSON，与需求不直接相关的请忽略）：\n⚠️ 重要：以下每个工具的 tool_key 必须原样写入生成的 JSON，禁止省略、修改或截断任何部分（MCP 工具的 _数字ID 后缀不可删除）：\n- [MCP工具] tool_key: "search_companies_78090930"（必须完全一致）\n  名称：search_companies\n  描述：输入省份、城市、企业状态查询并统计企业\n\n回答问题时结果中请先说明查询到的记录数，并以列表的形式列出查询到的前10条企业\n\n:param province：省份,例如上海,新疆,江苏,为None时表示查询全国的企业\n\n:param city：城市,地级市，例如杭州，苏州\n\n:param district： 区县,区县名称需完整,包含市、县、区,例如昆山市，浦东新区\n\n:param company_status： 企业状态可以设为"正常"、"异常"、"在营"、"存续"、"在业"、"吊销"、"注销"、"迁入"、"迁出"、"清算"、"其他",为None时表示所有状态的企业\n\n                        企业状态正常，包括了在营、存续、在业、迁入、迁出的企业\n\n                        企业状态异常，包括了吊销、注销企业\n\n:return\n\n    Response:\n        status_code: 状态码，1为成功, 其他表示失败\n        status_message: 状态信息\n        data:\n            page_size: 每页数量\n            page_index: 当前页码\n            total: 返回的公司记录数\n            items: 公司列表,每个公司包含如下信息\n                company_name:企业名称\n                establish_date:成立时间\n                company_status:公司状态,\n                capital:注册资本\n                legal_person:法人\n                credit_no:统一信用码\n  参数：[\'city(选填): 城市,地级市，例如杭州，苏州\', \'district(选填): 区县,区县名称需完整,包含市、县、区,例如昆山市，浦东新区\', \'province(选填): 省份,例如上海,新疆,江苏,为None时表示查询全国的企业\', \'company_status(选填): 企业状态可以设为"正常"、"异常"、"在营"、"存续"、"在业"、"吊销"、"注销"、"迁入"、"迁出"、"清算"、"其他",为None时表示所有状态的企业\\n企业状态正常，包括了在营、存续、在业、迁入、迁出的企业\\n企业状态异常，包括了吊销、注销企业\']\n- [MCP工具] tool_key: "search_business_info_78090930"（必须完全一致）\n  名称：search_business_info\n  描述：查询企业的业务信息，包括产品品牌等信息\n\n:param company_name: 企业名称, 支持模糊搜索\n\n:param page_index: 页码, 从1开始计数, 当page_index为0时，返回全部业务产品品牌数据\n\n:return:\n\n    Response:\n        status_code: 状态码，1为成功, 其他表示失败\n        status_message: 状态信息\n        data:\n            page_size: 每页数量\n            page_index: 当前页数\n            total: 记录总数\n            items: 记录\n                company_name: 公司名称\n                round: 融资轮次\n                industry: 行业\n                logo: Logo链接\n                logo_oss_path: Logo oss链接\n                product: 产品名称\n                setup_date: 成立时间\n                business: 业务范围\n                introduction: 简介\n  参数：[\'page_index(选填): 页码, 从1开始计数, 当page_index为0时，返回全部业务产品品牌数据\', \'company_name(必填): 企业名称，支持模糊搜索\']\n- [MCP工具] tool_key: "get_stie_score_78090930"（必须完全一致）\n  名称：get_stie_score\n  描述：评估企业科创能力，给出科创能力评分及等级\n\n:param company_name: 企业名称, 支持模糊搜索\n\n:return:\n\n    Response:\n        status_code: 状态码，1为成功, 其他表示失败\n        status_message: 状态信息\n        searched_company: 实际查询的企业名称\n        data:\n            company_name:企业名称\n            credit_no:社会统一信用代码\n            score:科创评分\n            level:科创评级\n            ranking:科创排名\n            rating_dimension:维度评分\n            qualification:科技资质列表\n            company_base_infos:企业基本信息\n\n            history_names:曾用名\n            establish_date:成立日期\n            legal_person:法定代表人\n            capital:注册资本\n            real_capital:实缴资本\n            company_type:企业类型\n            authority:登记机关\n            company_status:登记状态\n            staff_size:人员规模\n            insurance_num:参保人数\n            nei_industry_l2_code:国标行业码值（二级）\n            nei_industry_l2_name:国标行业名称（二级）\n            sei_industry_l2_code:战略新兴行业码值（二级）\n            sei_industry_l2_name:战略新兴行业名称（二级）\n            company_nature:企业性质\n            company_address:注册地址\n            business_scope:经营范围\n            province:省份\n            scale:企业规模\n\n            nei_industry_l2_ranking:国标二级行业该科创等级排名（前%）\n            sei_industry_l2_ranking:战略新兴二级行业排名（前%）\n            nei_industry_l2_province_ranking:国标二级行业地域排名（前%）\n            sei_industry_l2_province_ranking:战略新兴二级行业地域排名（前%）\n\n            stii_invest_score_to_100:创新投入评分（百分制）\n            stii_output_score_to_100:创新产出评分（百分制）\n            stii_quality_score_to_100:创新质量评分（百分制）\n            stii_influence_score_to_100:创新影响评分（百分制）\n            stii_develop_score_to_100:创新成长评分（百分制）\n  参数：[\'company_name(必填): 企业名称, 支持模糊搜索\']\n\n候选知识库（仅当需求涉及文档检索时使用）：\n- ID: 6\n  名称：招商引资相关政策\n  描述：当回答与招商引资相关政策相关的问题时，参考此知识库\n  collection: col_1770633881_0d9d02fb\n\n【工作流设计原则】\n1. 保守优先：用户未明确要求的能力不要添加；简单场景工作流应精简\n2. 工具/知识库按需选用，与需求不直接相关的忽略\n3. 禁止死分支：每个 Tool 节点的输出必须被至少一个 LLM 节点通过 {#tool_xxx.output#} 引用\n4. 复杂度：simple 约 3-5 节点，moderate 约 5-8，full 可含条件分支\n\n【自检与输出】\n- 生成初版后请调用 validate_workflow 工具传入该 JSON 字符串进行校验；若返回非 OK，根据问题修正后再次校验，直到返回 OK 或已迭代 2 次\n- 本任务只需输出工作流 JSON，请勿使用 read_file、write_file、execute、task 等工具\n- 最终必须以 ```json 代码块输出完整工作流 JSON，确保可被 json.loads() 解析'

),
    debug=False,
    checkpointer=checkpointer,
    backend=FilesystemBackend(root_dir=str(PROJECT_ROOT), virtual_mode=True),
    skills=[SKILLS_SOURCE, CURSOR_SKILLS_PATH.__str__()],
)


async def chat(query: str):
    print("开始进行 deepagent 的调用")

    result = deep_agent.invoke(
        input={"messages": [HumanMessage(content=query)]},
        config=RunnableConfig(
            configurable={"thread_id": "thread-1"},
        ),
    )
    print(result["messages"][-1].content)


if __name__ == "__main__":
    import asyncio

    asyncio.run(chat('请根据提供的上下文信息，**创建一个毕昇(Bisheng)的工作流**，输出完整且符合规范的毕昇工作流 JSON。用户需求：创建深汕招商政策查询助手工作流，支持政策条文查询与解读、匹配适用该政策的企业、查询符合条件的企业信息，需结合知识库与联网检索。'
))
