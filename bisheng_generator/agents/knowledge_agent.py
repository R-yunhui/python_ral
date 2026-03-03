"""
知识库匹配 Agent

职责：
1. 加载可用知识库清单
2. 根据意图匹配知识库（基于 LLM 语义匹配）
3. 配置检索参数
4. 分析知识库权限
"""

import logging
from typing import List, Dict, Any, Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from models.intent import EnhancedIntent

logger = logging.getLogger(__name__)


class KnowledgeBaseDefinition(BaseModel):
    """知识库定义"""

    id: Optional[int] = Field(default=None, description="知识库 ID")
    name: str = Field(..., description="知识库名称")
    desc: str = Field(..., description="知识库描述")
    document_count: Optional[int] = Field(default=0, description="文档数量")
    owner: Optional[str] = Field(default=None, description="知识库所有者")
    tags: List[str] = Field(default_factory=list, description="知识库标签")
    extra: Optional[Dict[str, Any]] = Field(default=None, description="额外配置信息")

    def to_schema(self) -> Dict[str, Any]:
        """转换为 LLM 可调用的 schema 格式"""
        return {
            "knowledge_base_id": self.id,
            "name": self.name,
            "description": self.desc,
            "document_count": self.document_count,
            "tags": self.tags,
        }


class KnowledgeMatch(BaseModel):
    """知识库匹配结果"""

    required: bool = Field(default=False, description="是否需要知识库")
    matched_knowledge_bases: List[KnowledgeBaseDefinition] = Field(
        default_factory=list, description="匹配的知识库列表"
    )
    retrieval_config: Dict[str, Any] = Field(
        default_factory=dict, description="检索配置"
    )
    similarity_score: float = Field(default=0.0, description="相似度分数（0-1）")
    reasoning: str = Field(default="", description="匹配理由")


class KnowledgeAgent:
    """知识库匹配专家"""

    def __init__(self, llm: BaseChatModel, embedding: Embeddings):
        self.llm = llm
        self.embedding = embedding

        # 预定义的知识库清单（模拟毕昇平台的知识库）
        # TODO: 后续可以从数据库动态加载，或使用 embedding 进行语义匹配
        self.knowledge_catalog = self._init_knowledge_catalog()

        # 知识库匹配提示词
        self.match_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一个专业的知识库匹配专家。根据用户需求，从可用知识库列表中选择最合适的知识库。",
                ),
                (
                    "human",
                    """
请根据用户需求，从可用知识库列表中选择最合适的知识库。

用户需求：{rewritten_input}
工作流类型：{workflow_type}

可用知识库列表：
{knowledge_catalog}

匹配原则：
1. 语义匹配：选择与用户需求最相关的知识库
2. 领域匹配：优先选择同一领域的知识库（如政策、法律、科技等）
3. 权威性优先：优先选择官方、权威的知识库
4. 政策类查询：如果有多个政策相关知识库，可以都选中

请分析并返回：
- matched_knowledge_bases: 匹配的知识库列表（返回 id）
- retrieval_config: 检索配置（可选）
- reasoning: 匹配理由（50 字以内）

以 JSON 格式返回。
""",
                ),
            ]
        )

    def _init_knowledge_catalog(self) -> List[KnowledgeBaseDefinition]:
        """
        初始化知识库清单
        
        基于毕昇平台现有的真实知识库
        """
        return [
            # ========== 深汕合作区政策类知识库 ==========
            KnowledgeBaseDefinition(
                id=6,
                name="招商引资相关政策",
                desc="当回答与招商引资相关政策相关的问题时，参考此知识库",
                document_count=0,  # 文档数待获取
                owner="admin",
                tags=["招商", "投资", "政策", "优惠"],
                extra={
                    "model": "6",
                    "collection_name": "col_1770633881_0d9d02fb",
                    "index_name": "col_1770633881_0d9d02fb",
                    "state": 1,
                    "type": 0
                }
            ),
            KnowledgeBaseDefinition(
                id=7,
                name="深汕海洋产业",
                desc="深汕海洋产业相关知识库",
                document_count=0,  # 文档数待获取
                owner="admin",
                tags=["海洋", "产业", "深汕", "经济"],
                extra={
                    "model": "6",
                    "collection_name": "col_1770687360_549bb98b",
                    "index_name": "col_1770687360_549bb98b",
                    "state": 1,
                    "type": 0
                }
            ),
            
            # ========== 测试知识库 ==========
            KnowledgeBaseDefinition(
                id=9,
                name="test4",
                desc="当回答与 test4 相关的问题时，参考此知识库",
                document_count=0,  # 文档数待获取
                owner="admin",
                tags=["test4", "测试"],
                extra={
                    "model": "6",
                    "collection_name": "col_1772076951_e3a04132",
                    "index_name": "col_1772076951_e3a04132",
                    "state": 1,
                    "type": 0
                }
            ),
            KnowledgeBaseDefinition(
                id=10,
                name="test4 副本",
                desc="当回答与 test4 相关的问题时，参考此知识库",
                document_count=0,  # 文档数待获取
                owner="admin",
                tags=["test4", "测试"],
                extra={
                    "model": "6",
                    "collection_name": "col_1772439817_8bb38ba4",
                    "index_name": "col_1772439817_8bb38ba4",
                    "state": 1,
                    "type": 0
                }
            ),
            
            # ========== 其他知识库 ==========
            KnowledgeBaseDefinition(
                id=4,
                name="AI 手表",
                desc="AI 手表相关知识库",
                document_count=0,  # 文档数待获取
                owner="admin",
                tags=["AI", "手表", "智能硬件"],
                extra={
                    "model": "6",
                    "collection_name": "col_1770619074_795e525e",
                    "index_name": "col_1770619074_795e525e",
                    "state": 1,
                    "type": 0
                }
            ),
        ]

    async def match_knowledge(self, intent: EnhancedIntent) -> KnowledgeMatch:
        """
        根据意图匹配知识库

        Args:
            intent: 用户意图描述

        Returns:
            KnowledgeMatch: 知识库匹配结果
        """
        logger.info("开始知识库匹配")
        
        # 如果不需要知识库，直接返回空结果
        if not intent.needs_knowledge:
            logger.info("用户需求不需要检索知识库")
            return KnowledgeMatch(required=False, reasoning="用户需求不需要检索知识库")

        # 生成知识库清单描述
        logger.info("格式化可用知识库清单")
        knowledge_catalog_str = self._format_knowledge_catalog()

        # 调用 LLM 匹配知识库
        logger.info("调用 LLM 进行知识库匹配")
        chain = self.match_prompt | self.llm
        response = await chain.ainvoke(
            {
                "rewritten_input": intent.rewritten_input,
                "workflow_type": intent.get_workflow_type(),
                "knowledge_catalog": knowledge_catalog_str,
            }
        )

        # 解析响应
        import json

        try:
            result = json.loads(response.content)
        except:
            result = {}

        # 获取匹配的知识库
        matched_kb_ids = result.get("matched_knowledge_bases", [])
        matched_knowledge_bases = [
            kb for kb in self.knowledge_catalog if kb.id in matched_kb_ids
        ]
        
        logger.info(f"LLM 匹配到 {len(matched_kb_ids)} 个知识库：{matched_kb_ids}")

        # 如果没有匹配到任何知识库，但有知识库需求，返回最相关的 Top-2
        # TODO: 这里后续可以使用 embedding 进行语义匹配
        if not matched_knowledge_bases and intent.needs_knowledge:
            logger.warning("LLM 未匹配到任何知识库，使用默认 Top-2 知识库")
            matched_knowledge_bases = self.knowledge_catalog[:2]  # 临时方案：返回前 2 个

        # 生成检索配置
        retrieval_config = result.get("retrieval_config", {})
        if not retrieval_config:
            retrieval_config = {
                "top_k": 3,  # 默认返回 3 个最相关的文档片段
                "score_threshold": 0.6,  # 相似度阈值
                "search_type": "similarity",  # 相似度检索
            }

        # 计算相似度分数（简化版本，TODO: 后续使用实际的向量相似度）
        similarity_score = 0.8 if matched_knowledge_bases else 0.0
        
        kb_names = [kb.name for kb in matched_knowledge_bases]
        logger.info(f"知识库匹配完成：匹配到 {len(matched_knowledge_bases)} 个知识库 [{', '.join(kb_names)}], 相似度={similarity_score:.2f}")

        return KnowledgeMatch(
            required=True,
            matched_knowledge_bases=matched_knowledge_bases,
            retrieval_config=retrieval_config,
            similarity_score=similarity_score,
            reasoning=result.get("reasoning", ""),
        )

    def _format_knowledge_catalog(self) -> str:
        """格式化知识库清单描述"""
        formatted = []
        for kb in self.knowledge_catalog:
            desc = f"""
知识库 ID: {kb.id}
名称：{kb.name}
描述：{kb.desc}
文档数量：{kb.document_count}
所有者：{kb.owner}
标签：{', '.join(kb.tags)}
"""
            if kb.extra:
                desc += f"额外信息：{kb.extra}\n"
            formatted.append(desc)
        return "\n---\n".join(formatted)

    async def get_knowledge_bases(self) -> List[KnowledgeBaseDefinition]:
        """
        获取所有可用知识库

        Returns:
            知识库列表
        """
        return self.knowledge_catalog

    async def get_knowledge_base_by_id(
        self, kb_id: int
    ) -> Optional[KnowledgeBaseDefinition]:
        """
        根据 ID 获取知识库定义

        Args:
            kb_id: 知识库 ID

        Returns:
            知识库定义，如果不存在则返回 None
        """
        for kb in self.knowledge_catalog:
            if kb.id == kb_id:
                return kb
        return None

    # ========== 预留 embedding 匹配接口 ==========
    # TODO: 后续实现基于向量相似度的知识库匹配
    async def match_knowledge_by_embedding(
        self, query: str, top_k: int = 2
    ) -> List[KnowledgeBaseDefinition]:
        """
        使用 embedding 进行语义匹配

        Args:
            query: 查询文本
            top_k: 返回最相关的 K 个知识库

        Returns:
            匹配的知识库列表
        """
        # TODO: 实现逻辑
        # 1. 生成 query 的 embedding
        # query_embedding = self.embedding.embed_query(query)
        # 2. 计算与每个知识库描述的相似度
        # 3. 返回 Top-K 最相似的知识库
        pass
