"""LLM 模型工厂（单例创建与缓存）"""

import logging
from typing import Any, Dict, Optional

from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel

from config.config import Config, config

logger = logging.getLogger(__name__)


class ModelInitializer:
    """模型初始化器"""

    _llm_instance: Optional[BaseChatModel] = None
    _llm_intent_instance: Optional[BaseChatModel] = None
    _llm_workflow_instance: Optional[BaseChatModel] = None

    @classmethod
    def _create_llm_with_thinking(
        cls, config_obj: Optional[Config], thinking_budget: int
    ) -> BaseChatModel:
        """构建开启思考的 LLM 实例（供意图/工作流节点复用）。"""
        cfg = config_obj or config
        extra_body: Dict[str, Any] = {"enable_thinking": True}
        if thinking_budget > 0:
            extra_body["thinking_budget"] = thinking_budget
        return ChatOpenAI(
            model=cfg.llm_model,
            api_key=cfg.llm_api_key,
            base_url=cfg.llm_base_url,
            temperature=cfg.llm_temperature,
            streaming=True,
            max_tokens=None,
            model_kwargs={"stream_options": {"include_usage": True}},
            extra_body=extra_body,
        )

    @classmethod
    def get_llm(cls, config_obj: Optional[Config] = None) -> BaseChatModel:
        """
        获取 LLM 实例（单例模式）

        Args:
            config_obj: Config 配置对象，如果不传则使用全局配置

        Returns:
            BaseChatModel 实例
        """
        if cls._llm_instance is not None:
            return cls._llm_instance

        cfg = config_obj or config
        logger.info(f"初始化 LLM: provider={cfg.llm_provider}, model={cfg.llm_model}")

        cls._llm_instance = ChatOpenAI(
            model=cfg.llm_model,
            api_key=cfg.llm_api_key,
            base_url=cfg.llm_base_url,
            temperature=cfg.llm_temperature,
            streaming=True,
            max_tokens=None,
            model_kwargs={"stream_options": {"include_usage": True}},
            extra_body={"enable_thinking": False},
        )

        logger.info("LLM 初始化成功")
        return cls._llm_instance

    @classmethod
    def get_llm_for_intent(cls, config_obj: Optional[Config] = None) -> BaseChatModel:
        """获取用于意图识别的 LLM（开启思考，thinking_budget 来自配置）。"""
        if cls._llm_intent_instance is not None:
            return cls._llm_intent_instance
        cfg = config_obj or config
        budget = getattr(cfg, "thinking_budget_intent", 50)
        cls._llm_intent_instance = cls._create_llm_with_thinking(config_obj, budget)
        logger.info(
            "意图识别 LLM 初始化成功（思考开启, thinking_budget=%s）", budget
        )
        return cls._llm_intent_instance

    @classmethod
    def get_llm_for_workflow(
        cls, config_obj: Optional[Config] = None
    ) -> BaseChatModel:
        """获取用于工作流生成的 LLM（开启思考，thinking_budget 来自配置）。"""
        if cls._llm_workflow_instance is not None:
            return cls._llm_workflow_instance
        cfg = config_obj or config
        budget = getattr(cfg, "thinking_budget_workflow", 100)
        cls._llm_workflow_instance = cls._create_llm_with_thinking(
            config_obj, budget
        )
        logger.info(
            "工作流生成 LLM 初始化成功（思考开启, thinking_budget=%s）", budget
        )
        return cls._llm_workflow_instance

    @classmethod
    def reset(cls) -> None:
        """重置模型实例（用于测试）"""
        cls._llm_instance = None
        cls._llm_intent_instance = None
        cls._llm_workflow_instance = None


def create_llm(config_obj: Optional[Config] = None) -> BaseChatModel:
    """
    创建 LLM 实例的便捷函数

    Args:
        config_obj: Config 配置对象

    Returns:
        BaseChatModel 实例
    """
    return ModelInitializer.get_llm(config_obj)
