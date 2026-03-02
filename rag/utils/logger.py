"""
日志工具模块
提供统一的日志配置和记录功能
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler
import os


def setup_logger(
    name: str,
    log_dir: str = None,
    level: str = None,
    format_string: str = None,
) -> logging.Logger:
    """
    配置并返回一个日志记录器

    Args:
        name: 日志记录器名称（通常是模块名）
        log_dir: 日志文件存储目录
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        format_string: 日志格式字符串

    Returns:
        配置好的 Logger 对象
    """
    # 默认配置
    if log_dir is None:
        from rag.config import LOG_DIR
        log_dir = LOG_DIR

    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")

    if format_string is None:
        format_string = (
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )

    # 创建 logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # 创建 formatter
    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")

    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件 handler (按天轮转)
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # 日志文件名：rag_YYYY-MM-DD.log
        log_file = log_path / f"rag_{datetime.now().strftime('%Y-%m-%d')}.log"

        # 使用轮转文件处理器（每个文件最大 10MB，保留 7 个文件）
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=7,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取一个日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        Logger 对象
    """
    return setup_logger(name)


# 创建全局默认 logger
default_logger = get_logger("RAG")
