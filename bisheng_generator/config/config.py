"""配置管理模块"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config(BaseModel):
    """配置管理"""

    # LLM 配置 - 使用阿里云 DashScope
    llm_provider: str = Field(default="dashscope", description="LLM 提供商")
    llm_model: str = Field(
        default_factory=lambda: os.getenv("QWEN_CHAT_MODEL", "qwen3-max"),
        description="LLM 模型",
    )
    llm_api_key: str = Field(
        default_factory=lambda: os.getenv("DASHSCOPE_API_KEY", ""),
        description="DashScope API Key",
    )
    llm_base_url: str = Field(
        default_factory=lambda: os.getenv(
            "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        ),
        description="DashScope API 地址",
    )
    llm_temperature: float = Field(default=0.7, ge=0, le=2)

    # Embedding 配置
    embedding_model: str = Field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-v3"),
        description="Embedding 模型",
    )
    embedding_dimension: int = Field(default=1536, description="Embedding 维度")

    # 工具配置
    bocha_search_api_key: str = Field(
        default_factory=lambda: os.getenv("BOCHA_WEB_SEARCH_API_KEY", ""),
        description="博查联网搜索 API Key",
    )

    # 日志配置
    log_level: str = Field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"), description="日志级别"
    )

    # 容错重试配置（各节点最多重试次数，总调用次数 = 1 + 重试次数）
    max_retries_intent: int = Field(
        default_factory=lambda: int(os.getenv("MAX_RETRIES_INTENT", "2")),
        ge=0,
        description="意图理解节点最大重试次数，默认 2（共 3 次调用）",
    )
    max_retries_tool: int = Field(
        default_factory=lambda: int(os.getenv("MAX_RETRIES_TOOL", "1")),
        ge=0,
        description="工具选择节点最大重试次数，默认 1",
    )
    max_retries_knowledge: int = Field(
        default_factory=lambda: int(os.getenv("MAX_RETRIES_KNOWLEDGE", "1")),
        ge=0,
        description="知识库匹配节点最大重试次数，默认 1",
    )
    max_retries_workflow: int = Field(
        default_factory=lambda: int(os.getenv("MAX_RETRIES_WORKFLOW", "2")),
        ge=0,
        description="工作流生成节点最大重试次数，默认 2（共 3 次调用）",
    )

    # 毕昇平台配置（知识库列表等接口）
    bisheng_base_url: str = Field(
        default_factory=lambda: os.getenv("BISHENG_BASE_URL", "http://localhost:3001"),
        description="毕昇接口域名，用于获取知识库列表等",
    )
    bisheng_api_url: str = Field(
        default="http://localhost:7860", description="毕昇 API 地址（兼容旧配置）"
    )
    bisheng_api_key: Optional[str] = Field(default=None, description="毕昇 API Key")

    # 服务配置
    service_host: str = Field(default="0.0.0.0", description="服务监听地址")
    service_port: int = Field(default=8000, description="服务端口")

    class Config:
        env_prefix = ""
        extra = "ignore"

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置"""
        return cls()

    def to_langchain_config(self) -> Dict[str, Any]:
        """转换为 LangChain 配置"""
        return {
            "llm_model": self.llm_model,
            "llm_provider": self.llm_provider,
            "api_key": self.llm_api_key,
            "base_url": self.llm_base_url,
            "temperature": self.llm_temperature,
            "embedding_model": self.embedding_model,
            "bisheng_url": self.bisheng_api_url,
            "bisheng_api_key": self.bisheng_api_key,
            "bocha_search_api_key": self.bocha_search_api_key,
        }


# 全局配置实例
config = Config.from_env()
