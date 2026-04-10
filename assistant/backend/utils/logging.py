import logging
import re
from contextvars import ContextVar

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


class TraceFilter(logging.Filter):
    def filter(self, record):
        record.trace_id = trace_id_var.get()
        return True


def sanitize_amount(text: str) -> str:
    """日志中脱敏金额"""
    return re.sub(r"\d+\.\d{2}", "XXX.XX", text)


def setup_logging(level: str = "INFO"):
    handler = logging.StreamHandler()
    handler.addFilter(TraceFilter())
    formatter = logging.Formatter(
        fmt='{"time":"%(asctime)s","level":"%(levelname)s","trace_id":"%(trace_id)s","msg":"%(message)s"}'
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper()))
