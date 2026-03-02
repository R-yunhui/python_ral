"""
问答服务
处理普通问答和 RAG 知识库问答
"""

import os
from typing import List, Optional, Generator
from dotenv import load_dotenv

from langchain_community.chat_models import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings

from langchain.agents import create_agent
from langchain.messages import HumanMessage, SystemMessage

from langgraph.types import StreamMode
from llama_index.core import VectorStoreIndex, Settings, StorageContext
from llama_index.llms.langchain import LangChainLLM
from llama_index.embeddings.langchain import LangchainEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore

from rag.service.qdrant_client import get_qdrant_client
from rag.utils.logger import get_logger
from rag.service.mcp_service import mcp_service

load_dotenv()

logger = get_logger(__name__)


class ChatService:
    """问答服务"""

    def __init__(self):
        self._llm = None
        self._embed_model = None
        self._agent = None

    @property
    def client(self):
        """获取 Qdrant 客户端单例"""
        return get_qdrant_client()

    @property
    def llm(self):
        """获取 LLM"""
        if self._llm is None:
            model_name = os.getenv("QWEN_CHAT_MODEL", "qwen-plus")
            logger.debug(f"初始化 LLM: {model_name}")
            self._llm = ChatTongyi(
                model=model_name,
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                streaming=True,
            )
            
            logger.info(f"LLM 初始化完成：{model_name}")
        return self._llm
    
    @property
    def agent(self):
        """获取 agent"""
        if self._agent is None:
            self._agent = create_agent(
                model=self.llm,
                system_prompt=SystemMessage(content="你是一个专业的聊天助手，可以使用工具回答问题。"),
                tools=mcp_service.get_tools(),
                debug=False,
            )
            
            logger.info("Agent 初始化完成")
        return self._agent

    @property
    def embed_model(self):
        """获取嵌入模型"""
        if self._embed_model is None:
            logger.debug("初始化 Embedding 模型")
            embeddings = DashScopeEmbeddings(
                model="text-embedding-v3",
                dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
            )
            self._embed_model = LangchainEmbedding(embeddings)
            logger.info("Embedding 模型初始化完成")
        return self._embed_model

    def _setup_settings(self):
        """配置 LlamaIndex 设置"""
        Settings.llm = LangChainLLM(self.llm)
        Settings.embed_model = self.embed_model
        Settings.chunk_size = 512
        Settings.chunk_overlap = 50

    def chat(self, question: str) -> str:
        """普通问答"""
        logger.info(f"普通问答：{question[:50]}...")
        try:
            response = self.llm.invoke(question)
            logger.info("普通问答完成")
            return response.content
        except Exception as e:
            logger.error(f"普通问答失败：{e}", exc_info=True)
            raise

    def chat_stream(self, question: str) -> Generator[str, None, None]:
        """普通问答（流式）"""
        logger.info(f"流式问答：{question[:50]}...")
        try:
            for chunk, _ in self.agent.stream(
                input={"messages": [HumanMessage(content=question)]},
                stream_mode="messages",
            ):
                yield chunk.content
            logger.info("流式问答完成")
        except Exception as e:
            logger.error(f"流式问答失败：{e}", exc_info=True)
            raise

    def rag_chat(
        self,
        question: str,
        collection_names: List[str],
        top_k: int = 3,
    ) -> str:
        """RAG 知识库问答"""
        logger.info(f"RAG 问答：{question[:50]}... (collections: {collection_names})")
        try:
            self._setup_settings()

            # 获取合并的索引
            logger.debug(f"加载索引：{collection_names}")
            index = self._get_combined_index(collection_names)
            if not index:
                logger.warning("未找到索引")
                return "抱歉，未找到相关知识库内容。"

            query_engine = index.as_query_engine(similarity_top_k=top_k)
            logger.debug(f"执行查询，top_k={top_k}")
            response = query_engine.query(question)
            logger.info("RAG 问答完成")
            return str(response)

        except Exception as e:
            logger.error(f"RAG 问答失败：{e}", exc_info=True)
            raise

    def rag_chat_stream(
        self,
        question: str,
        collection_names: List[str],
        top_k: int = 3,
    ) -> Generator[str, None, None]:
        """RAG 知识库问答（流式）"""
        logger.info(f"RAG 流式问答：{question[:50]}... (collections: {collection_names})")
        try:
            self._setup_settings()

            # 获取合并的索引
            logger.debug(f"加载索引：{collection_names}")
            index = self._get_combined_index(collection_names)
            if not index:
                logger.warning("未找到索引")
                yield "抱歉，未找到相关知识库内容。"
                return

            query_engine = index.as_query_engine(
                streaming=True,
                similarity_top_k=top_k,
            )
            logger.debug(f"执行流式查询，top_k={top_k}")
            response = query_engine.query(question)

            for text in response.response_gen:
                yield text
            logger.info("RAG 流式问答完成")

        except Exception as e:
            logger.error(f"RAG 流式问答失败：{e}", exc_info=True)
            raise

    def _get_combined_index(self, collection_names: List[str]) -> Optional[VectorStoreIndex]:
        """获取合并的向量索引"""
        if not collection_names:
            logger.warning("集合名称列表为空")
            return None

        # 使用第一个集合作为主索引
        # 后续可以考虑合并多个集合
        logger.debug(f"使用集合：{collection_names[0]}")
        vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=collection_names[0],
        )

        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        try:
            index = VectorStoreIndex.from_vector_store(
                vector_store,
                storage_context=storage_context,
            )
            logger.debug(f"索引加载成功")
            return index
        except Exception as e:
            logger.error(f"加载索引失败：{e}", exc_info=True)
            return None


# 全局服务实例
chat_service = ChatService()