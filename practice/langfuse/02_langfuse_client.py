# 从 langfuse 获取 trace 数据
import os
import asyncio
import json

from dotenv import load_dotenv

# langfuse
from langfuse import get_client
from langfuse.api import Traces

# 加载环境变量
load_dotenv()

# 创建 langfuse 客户端
langfuse_client = get_client()


async def get_trace(trace_id: str = None) -> Traces | None:
    """
    获取 trace 数据
    Args:
        trace_id: trace ID
    Returns:
        Traces: trace 数据
    """
    if trace_id is None:
        return None

    traces = langfuse_client.api.trace.list(page=1, limit=10)

    trace_ids = [trace.id for trace in traces.data]

    for trace in traces.data:
        print(trace.model_dump_json(indent=2, ensure_ascii=False))
        print("-" * 100)

    for trace_id in trace_ids:
        observations = langfuse_client.api.observations.get_many(
            limit=100, fields="core,basic,usage,io,model", trace_id=trace_id
        )

        for obs in observations.data:
            print(obs.model_dump_json(indent=2, ensure_ascii=False))
            print("-" * 100)

    return traces


if __name__ == "__main__":
    asyncio.run(get_trace("1234567890"))
