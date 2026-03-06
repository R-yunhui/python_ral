"""日志配置：控制台 UTF-8 输出 + 可选文件轮转，由调用方传入配置避免循环依赖。"""

import io
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

LOG_FMT = (
    "%(asctime)s - %(name)s - [%(filename)s:%(lineno)d] - %(levelname)s - %(message)s"
)
DATE_FMT = "%Y-%m-%d %H:%M:%S"


class UTF8StreamHandler(logging.StreamHandler):
    """控制台 Handler，保证 UTF-8 输出，避免 Windows 乱码。"""

    def __init__(self, stream=None):
        super().__init__(stream)
        self.setFormatter(logging.Formatter(LOG_FMT, datefmt=DATE_FMT))

    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            if isinstance(stream, io.TextIOWrapper):
                stream.write(msg + self.terminator)
            else:
                stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


def setup_logging(
    log_level: str = "INFO",
    log_dir: Optional[str] = None,
    repo_root: Optional[Path] = None,
    *,
    log_filename: str = "bisheng_generator.log",
    file_max_bytes: int = 10 * 1024 * 1024,
    file_backup_count: int = 5,
) -> None:
    """
    配置根 logger：控制台（UTF-8）+ 可选 log 目录文件（按大小轮转）。

    Args:
        log_level: 日志级别，如 INFO、DEBUG。
        log_dir: 日志目录，相对路径时基于 repo_root 解析；为空则只打控制台。
        repo_root: 项目根路径，log_dir 为相对路径时使用；None 则用当前工作目录。
        log_filename: 日志文件名。
        file_max_bytes: 单文件最大字节数，默认 10MB。
        file_backup_count: 轮转保留备份数。
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    for h in root.handlers[:]:
        root.removeHandler(h)

    root.addHandler(UTF8StreamHandler(sys.stdout))

    if not (log_dir and str(log_dir).strip()):
        return

    try:
        log_path = Path(log_dir)
        if not log_path.is_absolute():
            base = repo_root if repo_root is not None else Path.cwd()
            log_path = base / log_path
        log_path.mkdir(parents=True, exist_ok=True)
        log_file = log_path / log_filename
        fh = RotatingFileHandler(
            log_file,
            encoding="utf-8",
            maxBytes=file_max_bytes,
            backupCount=file_backup_count,
        )
        fh.setFormatter(logging.Formatter(LOG_FMT, datefmt=DATE_FMT))
        root.addHandler(fh)
    except Exception as e:
        import traceback
        sys.stderr.write(f"日志文件 handler 初始化失败: {e}\n{traceback.format_exc()}\n")
