"""
工具选择 Agent

职责：
1. 加载可用工具清单
2. 根据意图选择工具（基于 LLM 语义匹配）
3. 规划工具参数
4. 分析工具依赖关系
"""

import logging
from typing import List, Dict, Any, Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from models.intent import EnhancedIntent
from core.utils import extract_json

logger = logging.getLogger(__name__)


class ToolDefinition(BaseModel):
    """工具定义"""

    id: Optional[int] = Field(default=None, description="工具 ID")
    name: str = Field(..., description="工具名称")
    tool_key: str = Field(..., description="工具唯一标识")
    desc: str = Field(..., description="工具描述")
    logo: Optional[str] = Field(default=None, description="工具 logo")
    parameters: List[Dict[str, Any]] = Field(
        default_factory=list, description="工具参数列表"
    )
    extra: Optional[Dict[str, Any]] = Field(default=None, description="额外配置信息")

    def to_schema(self) -> Dict[str, Any]:
        """转换为 LLM 可调用的 schema 格式"""
        return {
            "name": self.tool_key,
            "description": self.desc,
            "parameters": {
                "type": "object",
                "properties": {
                    param.get("name", ""): {
                        "type": param.get("type", "string"),
                        "description": param.get("description", ""),
                    }
                    for param in self.parameters
                },
                "required": [
                    p.get("name") for p in self.parameters if p.get("required", False)
                ],
            },
        }


class ToolPlan(BaseModel):
    """工具选择计划"""

    selected_tools: List[ToolDefinition] = Field(
        default_factory=list, description="选中的工具列表"
    )
    parameters_mapping: Dict[str, str] = Field(
        default_factory=dict, description="参数映射：工具参数 -> 节点变量"
    )
    dependencies: List[tuple] = Field(default_factory=list, description="工具依赖关系")
    execution_order: List[str] = Field(default_factory=list, description="执行顺序")
    reasoning: str = Field(default="", description="选择这些工具的理由")


class ToolAgent:
    """工具选择专家"""

    def __init__(self, llm: BaseChatModel, embedding: Embeddings):
        self.llm = llm
        self.embedding = embedding

        # 预定义的工具清单（基于毕昇平台内置工具）
        # TODO: 后续可以从数据库动态加载，或使用 embedding 进行语义匹配
        self.tools_catalog = self._init_tools_catalog()

        # 工具选择提示词
        self.select_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一个专业的工具选择专家。根据用户需求，从可用工具列表中选择最合适的工具。",
                ),
                (
                    "human",
                    """
请根据用户需求，从可用工具列表中选择最合适的工具。

用户需求：{rewritten_input}

可用工具列表：
{tools_catalog}

选择原则：
1. 精准匹配：只选择与用户需求明确相关的工具，不要强行匹配
2. 参数完整性：确保工具参数可以被满足
3. 最小化原则：只选择必要的工具，避免过度使用
4. 允许为空：如果没有合适的工具，返回空列表

请分析并返回：
- selected_tools: 选中的工具列表（返回 tool_key 数组，如果没有匹配的工具则返回空数组）
- parameters_mapping: 参数映射关系（格式说明：key 为 "工具 key_参数名"，value 为节点变量名，例如：web_search_query -> user_query）
- reasoning: 选择理由（50 字以内，如果没有选中工具则说明原因）

以 JSON 格式返回。
""",
                ),
            ]
        )

    def _init_tools_catalog(self) -> List[ToolDefinition]:
        """
        初始化工具清单

        精选高可用性核心工具
        """
        return [
            # ========== 基础工具 ==========
            ToolDefinition(
                id=1,
                name="计算器",
                tool_key="calculator",
                desc="执行数学表达式计算，支持加减乘除、指数、对数、三角函数等运算",
                logo=None,
                parameters=[
                    {
                        "name": "expression",
                        "type": "string",
                        "description": "数学表达式，例如：2 + 2 * 3 或 sin(3.14/2)",
                        "required": True,
                    }
                ],
                extra={},
            ),
            ToolDefinition(
                id=2,
                name="获取当前时间",
                tool_key="get_current_time",
                desc="返回当前时间（UTC+8 时区），支持指定时区转换",
                logo=None,
                parameters=[
                    {
                        "name": "timezone",
                        "type": "string",
                        "description": "时区，例如：UTC+8、America/New_York，默认为 UTC+8",
                        "required": False,
                    }
                ],
                extra={},
            ),
            # ========== 搜索检索工具 ==========
            ToolDefinition(
                id=3,
                name="联网搜索",
                tool_key="web_search",
                desc="使用 Bing 搜索引擎检索网页、新闻、学术文章等实时信息，返回搜索结果摘要和链接",
                logo=None,
                parameters=[
                    {
                        "name": "query",
                        "type": "string",
                        "description": "搜索查询关键词",
                        "required": True,
                    },
                    {
                        "name": "num_results",
                        "type": "integer",
                        "description": "返回结果数量，取值范围 1-50，默认为 10",
                        "required": False,
                    },
                ],
                extra={},
            ),
            ToolDefinition(
                id=4,
                name="网页爬取",
                tool_key="fire_scrape",
                desc="爬取指定 URL 的网页内容并转换为 Markdown 格式，支持单页面和深度爬取（包含子页面）",
                logo=None,
                parameters=[
                    {
                        "name": "url",
                        "type": "string",
                        "description": "要爬取的网页 URL",
                        "required": True,
                    },
                    {
                        "name": "mode",
                        "type": "string",
                        "description": "爬取模式：single（单页面）或 deep（包含子页面），默认为 single",
                        "required": False,
                    },
                ],
                extra={},
            ),
            ToolDefinition(
                id=5,
                name="网页转 Markdown",
                tool_key="jina_reader",
                desc="将网页（包括 PDF、Word 文档）转换为 Markdown 格式，适合 LLM 处理和分析",
                logo=None,
                parameters=[
                    {
                        "name": "url",
                        "type": "string",
                        "description": "要转换的网页 URL",
                        "required": True,
                    }
                ],
                extra={},
            ),
            # ========== 图像生成工具 ==========
            ToolDefinition(
                id=6,
                name="AI 绘画（Flux）",
                tool_key="flux_image_gen",
                desc="使用 Flux 模型生成高质量图像，支持复杂场景描述和多种艺术风格",
                logo=None,
                parameters=[
                    {
                        "name": "prompt",
                        "type": "string",
                        "description": "图像描述词（建议使用英文以获得更好效果）",
                        "required": True,
                    },
                    {
                        "name": "size",
                        "type": "string",
                        "description": "图像尺寸，可选值：1024x1024、1920x1080、1080x1920，默认为 1024x1024",
                        "required": False,
                    },
                ],
                extra={},
            ),
            ToolDefinition(
                id=7,
                name="AI 绘画（DALL-E 3）",
                tool_key="dalle_image_gen",
                desc="使用 DALL-E 3 模型生成图像，适合艺术风格创作和创意图像生成",
                logo=None,
                parameters=[
                    {
                        "name": "prompt",
                        "type": "string",
                        "description": "图像描述词，详细描述想要生成的图像内容",
                        "required": True,
                    },
                    {
                        "name": "style",
                        "type": "string",
                        "description": "艺术风格：vivid（鲜艳风格）或 natural（自然风格），默认为 vivid",
                        "required": False,
                    },
                ],
                extra={},
            ),
        ]

    async def select_tools(self, intent: EnhancedIntent) -> ToolPlan:
        """
        根据意图选择工具

        Args:
            intent: 用户意图描述

        Returns:
            ToolPlan: 工具选择计划
        """
        if not intent.needs_tool:
            logger.info("工具选择跳过，needs_tool=false")
            return ToolPlan(selected_tools=[], reasoning="用户需求不需要调用外部工具")

        tools_catalog_str = self._format_tools_catalog()
        chain = self.select_prompt | self.llm
        response = await chain.ainvoke(
            {
                "rewritten_input": intent.rewritten_input,
                "tools_catalog": tools_catalog_str,
            }
        )

        # 解析响应
        result = extract_json(response.content)
        if result is None:
            logger.error(f"LLM 响应 JSON 提取/解析失败。原始响应：{response.content}")
            result = {}

        # 获取选中的工具
        selected_tool_keys = result.get("selected_tools", [])
        selected_tools = [
            tool for tool in self.tools_catalog if tool.tool_key in selected_tool_keys
        ]

        if not selected_tools and intent.needs_tool:
            logger.info("工具选择完成，matched=0，返回空计划")
            return ToolPlan(selected_tools=[], reasoning="未找到与用户需求匹配的工具")

        execution_order = [tool.tool_key for tool in selected_tools]
        logger.info("工具选择完成，count=%s, keys=%s", len(selected_tools), execution_order)

        return ToolPlan(
            selected_tools=selected_tools,
            parameters_mapping=result.get("parameters_mapping", {}),
            dependencies=[],  # TODO: 后续实现依赖分析
            execution_order=execution_order,
            reasoning=result.get("reasoning", ""),
        )

    def _format_tools_catalog(self) -> str:
        """格式化工具清单描述"""
        formatted = []
        for tool in self.tools_catalog:
            desc = f"""
工具名称：{tool.name}
tool_key: {tool.tool_key}
描述：{tool.desc}
参数：
"""
            for param in tool.parameters:
                required = "必填" if param.get("required", False) else "选填"
                desc += f"  - {param.get('name')}({param.get('type')}, {required}): {param.get('description')}\n"
            formatted.append(desc)
        return "\n---\n".join(formatted)

    async def get_tools(self) -> List[ToolDefinition]:
        """
        获取所有可用工具

        Returns:
            工具列表
        """
        return self.tools_catalog

    async def get_tool_by_key(self, tool_key: str) -> Optional[ToolDefinition]:
        """
        根据 tool_key 获取工具定义

        Args:
            tool_key: 工具唯一标识

        Returns:
            工具定义，如果不存在则返回 None
        """
        for tool in self.tools_catalog:
            if tool.tool_key == tool_key:
                return tool
        return None

    # ========== 预留 embedding 匹配接口 ==========
    # TODO: 后续实现基于向量相似度的工具匹配
    async def match_tools_by_embedding(
        self, query: str, top_k: int = 3
    ) -> List[ToolDefinition]:
        """
        使用 embedding 进行语义匹配

        Args:
            query: 查询文本
            top_k: 返回最相关的 K 个工具

        Returns:
            匹配的工具列表
        """
        # TODO: 实现逻辑
        # 1. 生成 query 的 embedding
        # query_embedding = self.embedding.embed_query(query)
        # 2. 计算与每个工具描述的相似度
        # 3. 返回 Top-K 最相似的工具
        pass
