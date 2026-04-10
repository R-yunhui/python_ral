from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM - 意图识别（小模型）
    intent_model: str = "qwen-turbo"
    intent_api_key: str = ""
    intent_base_url: str = ""

    # LLM - 主对话（大模型）
    reply_model: str = "claude-sonnet-4-6-20250514"
    reply_api_key: str = ""
    reply_base_url: str = ""

    # 数据库
    sqlite_path: str = "data/finance.db"

    # mem0
    mem0_api_key: str = ""

    # 通用
    log_level: str = "INFO"
    timezone: str = "Asia/Shanghai"
    api_key: str = ""  # API 认证密钥

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # 忽略 .env 中其他项目的变量
    }

    def validate(self):
        """启动时校验必填项"""
        if not self.sqlite_path:
            raise ValueError("SQLITE_PATH is required")
        if not self.reply_api_key:
            raise ValueError("REPLY_API_KEY is required")


# 全局默认实例（懒加载，不强制校验，测试时可覆盖）
settings = Settings()
