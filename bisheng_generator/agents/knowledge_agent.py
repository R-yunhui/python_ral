"""
知识库匹配 Agent

职责：
1. 从毕昇接口异步加载可用知识库清单（项目启动时调用）
2. 根据意图匹配知识库（基于 LLM 语义匹配）
3. 配置检索参数
4. 分析知识库权限
"""

import logging
from typing import List, Dict, Any, Optional
import httpx
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from models.intent import EnhancedIntent
from core.utils import extract_json

logger = logging.getLogger(__name__)

# 毕昇知识库列表接口分页大小
KNOWLEDGE_PAGE_SIZE = 20


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

        # 知识库清单：由 load_knowledge_catalog() 在项目启动时从毕昇接口异步加载
        self.knowledge_catalog: List[KnowledgeBaseDefinition] = []

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

    def _parse_knowledge_item(self, item: Dict[str, Any]) -> KnowledgeBaseDefinition:
        """将毕昇接口单条知识库数据解析为 KnowledgeBaseDefinition"""
        name = item.get("name") or ""
        desc = item.get("description") or ""
        extra = {
            "model": item.get("model"),
            "collection_name": item.get("collection_name"),
            "index_name": item.get("index_name"),
            "state": item.get("state"),
            "type": item.get("type"),
        }
        return KnowledgeBaseDefinition(
            id=item.get("id"),
            name=name,
            desc=desc,
            document_count=0,  # 接口未返回文档数
            owner=item.get("user_name"),
            tags=[],  # 接口未返回标签，可后续从 description 解析
            extra=extra,
        )

    async def load_knowledge_catalog(
        self,
        base_url: str,
        access_token: str = "",
    ) -> None:
        """
        从毕昇接口异步加载知识库列表（协程），应在项目启动时调用一次。

        接口：GET {base_url}/api/v1/knowledge?page_num=1&page_size=20&name=&type=0
        鉴权：Cookie 中 access_token_cookie（JWT）
        """
        logger.info("按请求加载知识库，has_token=%s", bool(access_token))
        base_url = (base_url or "").rstrip("/")
        if not base_url:
            logger.warning("毕昇 base_url 为空，跳过知识库加载")
            return

        all_items: List[KnowledgeBaseDefinition] = []
        page_num = 1

        try:
            async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
                while True:
                    url = (
                        f"{base_url}/api/v1/knowledge"
                        f"?page_num={page_num}&page_size={KNOWLEDGE_PAGE_SIZE}&name=&type=0"
                    )
                    headers = {"Accept": "application/json"}
                    if access_token:
                        headers["Cookie"] = (
                            f"lang=zh-Hans; access_token_cookie={access_token}"
                        )

                    resp = await client.get(url, headers=headers)

                    if resp.status_code != 200:
                        logger.warning(
                            "毕昇知识库接口请求失败: status=%s, body=%s",
                            resp.status_code,
                            resp.text[:500],
                        )
                        break

                    body = resp.json()
                    if body.get("status_code") != 200:
                        logger.warning(
                            "毕昇知识库接口返回错误: %s",
                            body.get("status_message", body),
                        )
                        break

                    data = body.get("data") or {}
                    raw_list = data.get("data") or []
                    total = data.get("total") or 0

                    for raw in raw_list:
                        if isinstance(raw, dict):
                            all_items.append(self._parse_knowledge_item(raw))

                    if len(raw_list) < KNOWLEDGE_PAGE_SIZE or len(all_items) >= total:
                        break
                    page_num += 1

            self.knowledge_catalog = all_items
            logger.info(
                "知识库加载完成：从毕昇接口加载 %d 个知识库",
                len(self.knowledge_catalog),
            )
        except httpx.RequestError as e:
            logger.warning("请求毕昇知识库接口失败: %s", e)
        except Exception as e:
            logger.exception("加载知识库列表异常: %s", e)

    async def match_knowledge(self, intent: EnhancedIntent) -> KnowledgeMatch:
        """
        根据意图匹配知识库

        Args:
            intent: 用户意图描述

        Returns:
            KnowledgeMatch: 知识库匹配结果
        """
        if not intent.needs_knowledge:
            logger.info("知识库匹配跳过，needs_knowledge=false")
            return KnowledgeMatch(required=False, reasoning="用户需求不需要检索知识库")

        if not self.knowledge_catalog:
            logger.warning("知识库列表为空，跳过匹配")
            return KnowledgeMatch(
                required=True,
                matched_knowledge_bases=[],
                reasoning="知识库列表未加载或为空",
            )

        knowledge_catalog_str = self._format_knowledge_catalog()
        chain = self.match_prompt | self.llm
        response = await chain.ainvoke(
            {
                "rewritten_input": intent.rewritten_input,
                "workflow_type": intent.get_workflow_type(),
                "knowledge_catalog": knowledge_catalog_str,
            }
        )

        # 解析响应
        result = extract_json(response.content)
        if result is None:
            logger.error(f"LLM 响应 JSON 提取/解析失败。原始响应：{response.content}")
            result = {}

        # 获取匹配的知识库
        matched_kb_ids = result.get("matched_knowledge_bases", [])
        matched_knowledge_bases = [
            kb for kb in self.knowledge_catalog if kb.id in matched_kb_ids
        ]

        if not matched_knowledge_bases and intent.needs_knowledge:
            logger.warning("知识库匹配无结果，使用默认 Top-2")
            matched_knowledge_bases = self.knowledge_catalog[:2]

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

        logger.info(
            "知识库匹配完成，count=%s, ids=%s",
            len(matched_knowledge_bases),
            [kb.id for kb in matched_knowledge_bases],
        )

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
