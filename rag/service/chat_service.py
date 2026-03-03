"""
问答服务
处理普通问答和 RAG 知识库问答（仅支持流式）
"""

import os
from typing import AsyncGenerator, List, Optional
from dotenv import load_dotenv

from langchain_community.chat_models import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings

from langchain.agents import create_agent
from langchain.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_openai.chat_models import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.embeddings.langchain import LangchainEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore

from rag.service.qdrant_client import get_qdrant_client, get_qdrant_async_client
from rag.config import QDRANT_PATH
from rag.utils.logger import get_logger

load_dotenv()

logger = get_logger(__name__)

# ==================== 常量定义 ====================

AGENT_SYSTEM_PROMPT = """你是一个专业的聊天助手，可以使用工具回答问题。
重要提示：
1. 调用工具时，必须使用有效的 JSON 格式传递参数
2. 所有字符串参数值必须用双引号包裹，例如："query": "天气查询"
3. 不要使用未加引号的值，例如：freshness: oneDay 是错误的
4. 正确的示例：{"query": "成都天气", "freshness": "oneDay"}
5. 确保生成的 JSON 可以被 json.loads() 解析
"""

RAG_PROMPT_TEMPLATE = """请根据以下资料回答问题。如果资料中没有相关信息，请说明。

资料：
{context}

问题：{question}

请根据上述资料回答问题，如果资料中没有相关信息，请说明"根据提供的资料，无法找到相关信息"。
回答："""


class ChatService:
    """问答服务"""

    def __init__(self):
        self._llm = None
        self._agent = None
        self._embed_model = None

    @property
    def client(self):
        """获取 Qdrant 同步客户端单例"""
        return get_qdrant_client()

    @property
    def embed_model(self):
        """获取嵌入模型"""
        if self._embed_model is None:
            logger.debug("初始化 Embedding 模型")
            embeddings = DashScopeEmbeddings(
                model=os.getenv("EMBEDDING_MODEL", "text-embedding-v3"),
                dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
            )
            self._embed_model = LangchainEmbedding(embeddings)
            logger.info("Embedding 模型初始化完成")
        return self._embed_model

    @property
    def llm(self):
        """获取 LLM"""
        if self._llm is None:
            model_name = os.getenv("QWEN_CHAT_MODEL", "qwen-plus")
            logger.debug(f"初始化 LLM: {model_name}")
            self._llm = ChatOpenAI(
                model=os.getenv("QWEN_CHAT_MODEL"),
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                streaming=True,
                base_url=os.getenv("DASHSCOPE_BASE_URL"),
            )

            logger.info(f"LLM 初始化完成：{model_name}")
        return self._llm

    async def _init_agent(self):
        """异步初始化 agent"""
        if self._agent is None:
            # 暂时使用内存记忆，后续可以考虑使用持久化记忆
            checkpointer = InMemorySaver()
            from rag.service.mcp_service import get_mcp_tools

            tools = await get_mcp_tools()

            self._agent = create_agent(
                model=self.llm,
                system_prompt=SystemMessage(content=AGENT_SYSTEM_PROMPT),
                tools=tools,
                debug=False,
                checkpointer=checkpointer,
            )

            logger.info("Agent 初始化完成")
        return self._agent

    @property
    async def async_agent(self):
        """异步获取 agent"""
        return await self._init_agent()

    def _build_context_from_nodes(self, nodes) -> str:
        """从检索的节点构建上下本文本"""
        context_parts = []
        for i, node in enumerate(nodes, 1):
            # 提取节点内容
            content = node.get_content() if hasattr(node, "get_content") else str(node)
            context_parts.append(f"[资料{i}]\n{content}")

        return "\n\n".join(context_parts)

    async def chat_astream(self, question: str) -> AsyncGenerator[str, None]:
        """普通问答（异步流式）"""
        logger.info(f"流式问答：{question[:50]}...")
        agent = await self.async_agent
        async for chunk, metadata in agent.astream(
            input={"messages": [HumanMessage(content=question)]},
            stream_mode="messages",
            config=RunnableConfig(
                configurable={"thread_id": "thread-1"},
            ),
        ):
            # 忽略工具调用和空内容
            if chunk.content != "" and metadata["langgraph_node"] != "tools":
                yield chunk.content
        logger.info("流式问答完成")

    async def rag_chat_astream(
        self,
        question: str,
        collection_names: List[str],
        top_k: int = 3,
    ) -> AsyncGenerator[str, None]:
        """RAG 知识库问答（异步流式）"""
        logger.info(
            f"RAG 流式问答：{question[:50]}... (collections: {collection_names})"
        )

        # 获取合并的索引
        logger.debug(f"加载索引：{collection_names}")
        index = self._get_combined_index(collection_names)
        if not index:
            logger.warning("未找到索引")
            yield "抱歉，未找到相关知识库内容。"
            return

        # 检索相关文档
        # 显式传入 llm 和 embed_model，避免使用 Settings 全局配置
        query_engine = index.as_query_engine(
            similarity_top_k=top_k,
            llm=self.llm,  # 使用我们的 LLM
            embed_model=self.embed_model,  # 使用我们的 Embedding
        )
        logger.debug(f"执行流式查询，top_k={top_k}")
        
        # 使用同步检索（Qdrant 同步客户端的异步方法实际在线程池中执行）
        try:
            nodes = await query_engine.aretrieve(question)
        except Exception:
            # 如果异步检索失败，使用同步检索
            nodes = query_engine.retrieve(question)
        
        if not nodes or len(nodes) == 0:
            logger.warning("未检索到相关文档")
            yield "抱歉，未找到相关知识库内容。"
            return

        # 构建上下文
        context_text = self._build_context_from_nodes(nodes)
        logger.debug(f"构建上下文，长度：{len(context_text)}")

        # 使用 LLM 异步流式回答
        prompt = RAG_PROMPT_TEMPLATE.format(context=context_text, question=question)

        async for chunk in self.llm.astream(prompt):
            content = chunk.content if hasattr(chunk, "content") else str(chunk)
            if content:
                yield content

        logger.info("异步 RAG 流式问答完成")

    def _get_combined_index(
        self, collection_names: List[str]
    ) -> Optional[VectorStoreIndex]:
        """获取合并的向量索引"""
        if not collection_names:
            logger.warning("集合名称列表为空")
            return None

        # 使用第一个集合作为主索引
        # 后续可以考虑合并多个集合
        logger.debug(f"使用集合：{collection_names[0]}")

        # 获取同步客户端（单例模式）
        sync_client = get_qdrant_client()
        
        # QdrantVectorStore 使用同步客户端
        # 注意：不需要传入 aclient，因为同步客户端在异步调用时会自动处理
        vector_store = QdrantVectorStore(
            client=sync_client,
            collection_name=collection_names[0],
        )

        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        try:
            # 传入 embedding 模型，避免 LlamaIndex 尝试使用 OpenAI
            index = VectorStoreIndex.from_vector_store(
                vector_store,
                storage_context=storage_context,
                embed_model=self.embed_model,  # 使用 DashScope Embedding
            )
            logger.debug(f"索引加载成功")
            return index
        except Exception as e:
            logger.error(f"加载索引失败：{e}", exc_info=True)
            return None


# 全局服务实例
chat_service = ChatService()
