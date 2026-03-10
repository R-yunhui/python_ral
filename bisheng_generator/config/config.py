"""配置管理模块"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config(BaseModel):
    """配置管理"""

    # LLM 配置 - 使用阿里云 DashScope
    llm_provider: str = Field(default="dashscope", description="LLM 提供商")
    llm_model: str = Field(
        default_factory=lambda: os.getenv("QWEN_CHAT_MODEL"),
        description="LLM 模型",
    )
    llm_api_key: str = Field(
        default_factory=lambda: os.getenv("DASHSCOPE_API_KEY"),
        description="DashScope API Key",
    )
    llm_base_url: str = Field(
        default_factory=lambda: os.getenv("DASHSCOPE_BASE_URL"),
        description="模型 API 地址",
    )
    llm_temperature: float = Field(default=0.7, ge=0, le=2)

    # 思考模式（仅对意图识别、工作流生成节点生效，0 表示不限制）
    thinking_budget_intent: int = Field(
        default_factory=lambda: int(os.getenv("THINKING_BUDGET_INTENT", "50")),
        ge=0,
        description="意图识别节点思考 token 上限，0 表示不限制，默认 50",
    )
    thinking_budget_workflow: int = Field(
        default_factory=lambda: int(os.getenv("THINKING_BUDGET_WORKFLOW", "100")),
        ge=0,
        description="工作流生成节点思考 token 上限，0 表示不限制，默认 100",
    )

    # 提示词目录（为空则使用默认 bisheng_generator/prompts）
    prompts_dir: Optional[str] = Field(
        default_factory=lambda: os.getenv("PROMPTS_DIR", ""),
        description="提示词 .md/.txt 根目录，为空则使用包内默认",
    )

    # 日志配置
    log_level: str = Field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"), description="日志级别"
    )
    log_dir: Optional[str] = Field(
        default_factory=lambda: os.getenv("LOG_DIR", "log"),
        description="日志文件目录（相对项目根或绝对路径），为空则仅输出到控制台",
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

    # 毕昇平台配置（仅保留地址；Token 由前端配置，上线后从 Cookie 获取）
    bisheng_base_url: str = Field(
        default_factory=lambda: os.getenv("BISHENG_BASE_URL", "http://localhost:3001"),
        description="毕昇接口地址，用于知识库列表、工作流导入等",
    )

    # MCP 工具搜索接口（已封装大模型筛选 + 向量检索）
    mcp_search_url: str = Field(
        default_factory=lambda: os.getenv(
            "MCP_SEARCH_URL", "http://10.10.1.40:8000/api/mcp-search"
        ),
        description="MCP 工具搜索接口地址，用于根据用户意图检索匹配的 MCP 工具",
    )
    mcp_search_top_k: int = Field(
        default_factory=lambda: int(os.getenv("MCP_SEARCH_TOP_K", "10")),
        ge=1,
        description="MCP 工具搜索返回的最大数量",
    )

    # 服务配置
    service_host: str = Field(default="0.0.0.0", description="服务监听地址")
    service_port: int = Field(default=8000, description="服务端口")

    # 数据库：工作流生成记录持久化
    # - 配置了 MySQL 连接信息时使用 MySQL
    # - 未配置 MySQL 时自动 fallback 到 SQLite（零配置）
    # - 设置 DB_ENABLED=false 可完全禁用数据库
    db_enabled: bool = Field(
        default_factory=lambda: os.getenv("DB_ENABLED", "true").lower()
        in ("true", "1", "yes"),
        description="是否启用数据库，设为 false 时完全不落库",
    )
    mysql_host: str = Field(
        default_factory=lambda: os.getenv("MYSQL_HOST", ""),
        description="MySQL 主机",
    )
    mysql_port: int = Field(
        default_factory=lambda: int(os.getenv("MYSQL_PORT", "3306")),
        description="MySQL 端口",
    )
    mysql_user: str = Field(
        default_factory=lambda: os.getenv("MYSQL_USER", ""),
        description="MySQL 用户名",
    )
    mysql_password: str = Field(
        default_factory=lambda: os.getenv("MYSQL_PASSWORD", ""),
        description="MySQL 密码",
    )
    mysql_database: str = Field(
        default_factory=lambda: os.getenv("MYSQL_DATABASE", ""),
        description="MySQL 数据库名",
    )

    def is_mysql_configured(self) -> bool:
        """是否已配置 MySQL 连接信息"""
        return bool(self.mysql_host and self.mysql_user and self.mysql_database)

    def is_db_enabled(self) -> bool:
        """是否启用数据库（MySQL 或 SQLite fallback）"""
        return self.db_enabled

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
            "bisheng_url": self.bisheng_base_url,
        }


# 全局配置实例
config = Config.from_env()
