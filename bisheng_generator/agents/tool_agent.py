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
1. 语义匹配：选择与用户需求最相关的工具
2. 参数完整性：确保工具参数可以被满足
3. 最小化原则：只选择必要的工具，避免过度使用
4. 知识库检索优先：如果能通过知识库解决，不需要调用工具

请分析并返回：
- selected_tools: 选中的工具列表（返回 tool_key 数组）
- parameters_mapping: 参数映射关系（格式说明：key 为 "工具 key_参数名"，value 为节点变量名，例如：web_search_query -> user_query）
- reasoning: 选择理由（50 字以内）

以 JSON 格式返回。
""",
                ),
            ]
        )

    def _init_tools_catalog(self) -> List[ToolDefinition]:
        """
        初始化工具清单

        基于毕昇平台内置的预定义工具
        参考：src/backend/bisheng/tool/domain/services/tool.py
        """
        return [
            # ========== 知识库检索工具 ==========
            ToolDefinition(
                id=100001,
                name="知识库和文件内容检索",
                tool_key="search_knowledge_base",
                desc="检索组织知识库、个人知识库以及本地上传文件的内容。支持语义检索，返回与查询相关的文档片段。",
                logo=None,
                parameters=[
                    {
                        "name": "query",
                        "type": "string",
                        "description": "用户查询问题，用于在知识库中检索相关内容",
                        "required": True,
                    }
                ],
                extra={},
            ),
            # ========== 文件操作工具 ==========
            ToolDefinition(
                id=200001,
                name="获取所有文件和目录",
                tool_key="list_files",
                desc="列出指定目录下的所有文件和子目录。",
                logo=None,
                parameters=[
                    {
                        "name": "path",
                        "type": "string",
                        "description": "要列出内容的目录路径，默认为当前工作目录",
                        "required": False,
                    }
                ],
                extra={},
            ),
            ToolDefinition(
                id=200002,
                name="获取文件详细信息",
                tool_key="get_file_details",
                desc="获取指定文件的文件名、文件大小、文件地址、字数、行数等详细信息。",
                logo=None,
                parameters=[
                    {
                        "name": "file_path",
                        "type": "string",
                        "description": "要获取详细信息的文件路径",
                        "required": True,
                    }
                ],
                extra={},
            ),
            ToolDefinition(
                id=200003,
                name="搜索文件",
                tool_key="search_files",
                desc="在指定目录中搜索文件和子目录，支持文件名模式匹配。",
                logo=None,
                parameters=[
                    {
                        "name": "pattern",
                        "type": "string",
                        "description": "文件名搜索模式，支持通配符，如 '*.txt'",
                        "required": True,
                    },
                    {
                        "name": "path",
                        "type": "string",
                        "description": "搜索的目录路径，默认为当前工作目录",
                        "required": False,
                    },
                ],
                extra={},
            ),
            ToolDefinition(
                id=200004,
                name="读取文件内容",
                tool_key="read_text_file",
                desc="读取本地文本文件的内容。",
                logo=None,
                parameters=[
                    {
                        "name": "file_path",
                        "type": "string",
                        "description": "要读取的文本文件路径",
                        "required": True,
                    }
                ],
                extra={},
            ),
            ToolDefinition(
                id=200005,
                name="写入文件内容",
                tool_key="add_text_to_file",
                desc="将文本内容追加到文本文件，如果文件不存在，则创建文件。",
                logo=None,
                parameters=[
                    {
                        "name": "file_path",
                        "type": "string",
                        "description": "要写入的文件路径",
                        "required": True,
                    },
                    {
                        "name": "content",
                        "type": "string",
                        "description": "要追加的文本内容",
                        "required": True,
                    },
                ],
                extra={},
            ),
            ToolDefinition(
                id=200006,
                name="替换文件指定行范围内容",
                tool_key="replace_file_lines",
                desc="替换文件中的指定行范围内容。",
                logo=None,
                parameters=[
                    {
                        "name": "file_path",
                        "type": "string",
                        "description": "要修改的文件路径",
                        "required": True,
                    },
                    {
                        "name": "start_line",
                        "type": "integer",
                        "description": "起始行号（从 1 开始）",
                        "required": True,
                    },
                    {
                        "name": "end_line",
                        "type": "integer",
                        "description": "结束行号（包含）",
                        "required": True,
                    },
                    {
                        "name": "content",
                        "type": "string",
                        "description": "替换的新内容",
                        "required": True,
                    },
                ],
                extra={},
            ),
            # ========== 代码解释器工具 ==========
            ToolDefinition(
                id=300001,
                name="代码解释器",
                tool_key="bisheng_code_interpreter",
                desc="执行 Python 代码并返回结果。支持数据分析、图表生成、文件处理等任务。",
                logo=None,
                parameters=[
                    {
                        "name": "python_code",
                        "type": "string",
                        "description": "要执行的 Python 代码脚本",
                        "required": True,
                    }
                ],
                extra={},
            ),
            # ========== 联网搜索工具 ==========
            ToolDefinition(
                id=400001,
                name="联网搜索",
                tool_key="web_search",
                desc="使用 query 进行联网检索并返回结果。支持搜索网页、新闻、文章等实时信息。",
                logo=None,
                parameters=[
                    {
                        "name": "query",
                        "type": "string",
                        "description": "搜索查询关键词",
                        "required": True,
                    }
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
        logger.info("开始工具选择")

        # 如果不需要工具，直接返回空计划
        if not intent.needs_tool:
            logger.info("用户需求不需要调用外部工具")
            return ToolPlan(selected_tools=[], reasoning="用户需求不需要调用外部工具")

        # 生成工具清单描述
        logger.info("格式化可用工具清单")
        tools_catalog_str = self._format_tools_catalog()

        # 调用 LLM 选择工具
        logger.info("调用 LLM 进行工具匹配")
        chain = self.select_prompt | self.llm
        response = await chain.ainvoke(
            {
                "rewritten_input": intent.rewritten_input,
                "tools_catalog": tools_catalog_str,
            }
        )

        # 解析响应
        import json

        try:
            result = json.loads(response.content)
        except:
            result = {}

        # 获取选中的工具
        selected_tool_keys = result.get("selected_tools", [])
        selected_tools = [
            tool for tool in self.tools_catalog if tool.tool_key in selected_tool_keys
        ]

        logger.info(f"LLM 推荐了 {len(selected_tool_keys)} 个工具")

        # 如果没有选中任何工具，但有工具需求，选择最相关的 Top-3
        # TODO: 这里后续可以使用 embedding 进行语义匹配
        if not selected_tools and intent.needs_tool:
            logger.warning("LLM 未选中任何工具，使用默认 Top-3 工具")
            selected_tools = self.tools_catalog[:3]  # 临时方案：返回前 3 个

        # 生成执行顺序（简单的拓扑排序，暂无依赖分析）
        execution_order = [tool.tool_key for tool in selected_tools]

        logger.info(f"最终选中 {len(selected_tools)} 个工具：{execution_order}")

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
