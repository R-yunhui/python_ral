"""
知识库服务
处理知识库的创建、删除、查询以及 Qdrant 集合管理
"""

import uuid
from typing import List, Optional
from pathlib import Path
from sqlmodel import Session, select

from qdrant_client.http import models as qdrant_models

from rag.models.models import KnowledgeBase, Document
from rag.api.schemas import KnowledgeBaseCreate, KnowledgeBaseResponse
from rag.config import get_collection_name
from rag.service.qdrant_client import get_qdrant_client
from rag.utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeBaseService:
    """知识库服务"""

    def __init__(self):
        pass

    @property
    def client(self):
        """获取 Qdrant 客户端单例"""
        return get_qdrant_client()

    def _generate_collection_name(self, kb_id: int) -> str:
        """生成集合名称"""
        return get_collection_name(kb_id)

    def create_knowledge_base(
        self, session: Session, data: KnowledgeBaseCreate
    ) -> KnowledgeBase:
        """创建知识库"""
        logger.info(f"创建知识库：{data.name}")
        try:
            # 先创建数据库记录获取 ID
            kb = KnowledgeBase(
                name=data.name,
                description=data.description,
                collection_name="",  # 稍后更新
            )
            session.add(kb)
            session.commit()
            session.refresh(kb)
            logger.debug(f"知识库记录创建成功，ID: {kb.id}")

            # 使用 KB ID 生成集合名称
            collection_name = self._generate_collection_name(kb.id)

            # 创建 Qdrant 集合
            logger.debug(f"创建 Qdrant 集合：{collection_name}")
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=1024,  # DashScope text-embedding-v3 维度
                    distance=qdrant_models.Distance.COSINE,
                ),
            )
            logger.info(f"Qdrant 集合创建成功：{collection_name}")

            # 更新集合名称
            kb.collection_name = collection_name
            session.add(kb)
            session.commit()
            session.refresh(kb)

            logger.info(f"知识库创建成功：{kb.name} (ID: {kb.id})")
            return kb

        except Exception as e:
            logger.error(f"创建知识库失败：{e}", exc_info=True)
            raise

    def get_knowledge_base(self, session: Session, kb_id: int) -> Optional[KnowledgeBase]:
        """获取单个知识库"""
        logger.debug(f"获取知识库：ID={kb_id}")
        kb = session.get(KnowledgeBase, kb_id)
        if kb:
            logger.debug(f"知识库存在：{kb.name}")
        else:
            logger.warning(f"知识库不存在：ID={kb_id}")
        return kb

    def list_knowledge_bases(self, session: Session) -> List[KnowledgeBase]:
        """获取知识库列表"""
        logger.debug("获取知识库列表")
        statement = select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())
        kbs = session.exec(statement).all()
        logger.info(f"获取到 {len(kbs)} 个知识库")
        return kbs

    def delete_knowledge_base(self, session: Session, kb_id: int) -> bool:
        """删除知识库"""
        logger.info(f"删除知识库：ID={kb_id}")
        try:
            kb = session.get(KnowledgeBase, kb_id)
            if not kb:
                logger.warning(f"知识库不存在，无法删除：ID={kb_id}")
                return False

            # 删除关联的文档记录
            doc_statement = select(Document).where(Document.kb_id == kb_id)
            documents = session.exec(doc_statement).all()
            logger.debug(f"删除关联文档：{len(documents)} 个")
            for doc in documents:
                session.delete(doc)

            # 删除 Qdrant 集合
            try:
                logger.debug(f"删除 Qdrant 集合：{kb.collection_name}")
                self.client.delete_collection(kb.collection_name)
                logger.info(f"Qdrant 集合删除成功：{kb.collection_name}")
            except Exception as e:
                logger.error(f"删除 Qdrant 集合失败：{e}")

            # 删除知识库记录
            session.delete(kb)
            session.commit()

            logger.info(f"知识库删除成功：{kb.name} (ID: {kb_id})")
            return True

        except Exception as e:
            logger.error(f"删除知识库失败：{e}", exc_info=True)
            return False

    def get_kb_with_document_count(
        self, session: Session, kb: KnowledgeBase
    ) -> KnowledgeBaseResponse:
        """获取带文档数量的知识库响应"""
        doc_statement = select(Document).where(Document.kb_id == kb.id)
        documents = session.exec(doc_statement).all()

        return KnowledgeBaseResponse(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            collection_name=kb.collection_name,
            created_at=kb.created_at,
            document_count=len(documents),
        )


# 全局服务实例
kb_service = KnowledgeBaseService()