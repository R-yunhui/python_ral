"""
用户意图理解 Agent（简化版）

职责：
1. 理解用户需求
2. 判断需要哪些功能（工具/知识库/条件/报告）
3. 生成 EnhancedIntent
"""

import logging
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from langchain_core.prompts import ChatPromptTemplate
from models.intent import EnhancedIntent

logger = logging.getLogger(__name__)


class UserAgent:
    """用户意图理解专家"""

    def __init__(self, llm: BaseChatModel, embedding: Embeddings):
        self.llm = llm
        self.embedding = embedding

        # 优化的提示词模板（支持通用场景，联网作为补充）
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
                      你是一个专业的需求分析专家。请分析用户需求，判断需要哪些功能。
                      
                      【核心判断原则】⭐ 必须严格遵守

                      📌 实时信息查询原则（重要！）：
                      - 查询天气、股票、汇率、航班等实时数据 → needs_tool=true（必须调用工具）
                      - 原因：这些信息需要从外部 API 获取，无法通过知识库或 LLM 已有知识提供
                      - ⚠️ 即使用户说"创建一个...工作流"，只要涉及实时数据查询，就需要工具
                      - 示例：
                        ✓ "帮我查天气" → needs_tool=true
                        ✓ "今天会下雨吗" → needs_tool=true
                        ✓ "查询股票价格" → needs_tool=true
                        ✓ "明天去北京的航班" → needs_tool=true
                        ✓ "创建一个天气查询工作流" → needs_tool=true
                        ✓ "做一个查汇率的助手" → needs_tool=true

                      📌 政策类特殊处理原则（重要！）：
                      - 查询政策、法规、政府文件等 → 默认需要知识库 + 联网检索（混合模式）
                      - 原因：政策时效性极强，新政策不断出台，旧政策可能废止
                      - 过度服务原则：提供额外信息总比遗漏重要信息好
                      - 示例：
                        ✓ "深汕的招商政策有哪些" → needs_knowledge=true, needs_tool=true（默认混合）
                        ✓ "最新的税收优惠政策" → needs_knowledge=true, needs_tool=true
                        ✓ "科技创新补贴政策" → needs_knowledge=true, needs_tool=true
                        ✓ "帮我查一下 XXX 政策的原文" → needs_knowledge=true, needs_tool=false（特例：只要原文）

                      📌 混合检索场景（needs_tool=true AND needs_knowledge=true）：
                      - 政策类查询：默认混合检索（除非用户明确只要原文）
                      - 其他混合场景：既需要查知识库（静态内容），又需要查实时信息（动态内容）

                      📌 简单问答场景（都不需要）：
                      - 简单闲聊、通用知识、创意写作等 → needs_tool=false, needs_knowledge=false

                      【详细判断参考】

                      1. 是否需要调用外部工具/API？（needs_tool）
                      - 需要调用工具的典型场景：
                        • 实时信息查询：天气、股票、汇率、航班、火车时刻等
                        • 搜索类：新闻搜索、网页搜索、学术搜索等
                        • 计算处理类：翻译、数学计算、代码执行、图像处理等
                        • 第三方服务：地图导航、快递查询、酒店预订、机票预订等
                      - 不需要工具的典型场景：
                        • 查询已有文档资料：公司制度、产品手册、技术文档等
                        • 基于知识库的问答：企业内部知识、历史数据、培训资料等
                        • 简单对话：闲聊、情感陪伴、创意写作、头脑风暴等

                      2. 是否需要检索知识库？（needs_knowledge）
                      - 需要知识库的典型场景：
                        • 企业/组织内部资料：公司文档、产品资料、技术手册、规章制度等
                        • 政策法规：政府文件、行业规定、地方政策、管理办法等
                        • 专业知识库：医疗知识、法律知识、金融知识、教育资料等
                        • 历史数据：销售记录、客户档案、项目文档、会议纪要等
                      - 不需要知识库的典型场景：
                        • 通用知识问答：常识性问题、百科知识等
                        • 纯工具调用：只需要调用 API 即可完成任务（如天气查询、翻译、计算等）
                        • 创意类任务：写诗、写故事、生成创意等
                        • ⚠️ 即使用户说"创建一个...工作流"，如果不涉及查阅资料，就不需要知识库

                      3. 是否需要多轮对话？（multi_turn）
                      - 需要多轮交互时设为 true

                      【其他场景的联网检索原则】
                      - 政策类默认需要联网（见 System 消息的核心原则）
                      - 其他场景需要联网的情况：
                        • 用户明确要求"实时查询"、"联网搜索"、"在线查询"等
                        • 查询动态信息：申报进度、公示名单、截止状态、实时库存、当前价格等
                        • 知识库可能没有的信息：最新新闻、突发事件、专家观点、网友评论等
                        • 需要调用第三方 API：天气、翻译、计算、地图等

                      【输出要求】
                      - 必须以 JSON 格式返回，包含字段：rewritten_input, needs_tool, needs_knowledge, multi_turn
                      - rewritten_input 控制在 50 字以内，使其更清晰完整
                      - 布尔值字段必须明确返回 true 或 false
                    """,
                ),
                (
                    "human",
                    "用户需求：{user_input}",
                ),
            ]
        )

    async def understand(self, user_input: str) -> EnhancedIntent:
        """
        理解用户意图

        Args:
            user_input: 用户输入

        Returns:
            EnhancedIntent: 结构化的意图描述
        """
        logger.info(f"开始理解用户意图：{user_input[:50]}...")
        
        # 调用 LLM 分析
        logger.info("调用 LLM 分析用户需求")
        chain = self.prompt | self.llm
        response = await chain.ainvoke({"user_input": user_input})

        # 解析 JSON 响应
        import json

        try:
            result = json.loads(response.content)
        except Exception as e:
            # 解析失败时记录详细错误信息
            logger.error(f"LLM 响应 JSON 解析失败：{str(e)}")
            logger.error(f"LLM 原始响应内容：{response.content}")
            logger.warning("使用默认值")
            result = {}

        # 创建 EnhancedIntent
        intent = EnhancedIntent(
            original_input=user_input,
            rewritten_input=result.get("rewritten_input", user_input),
            needs_tool=result.get("needs_tool", False),
            needs_knowledge=result.get("needs_knowledge", False),
            multi_turn=result.get("multi_turn", True),
        )
        
        # 记录意图分析结果
        features = []
        if intent.needs_tool:
            features.append("工具调用")
        if intent.needs_knowledge:
            features.append("知识库检索")
        
        logger.info(f"意图分析完成：工作流类型={intent.get_workflow_type()}, 功能={features}")
        
        return intent
