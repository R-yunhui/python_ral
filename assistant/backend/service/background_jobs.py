import logging
import asyncio
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class StoreJob:
    user_id: str
    data: Any
    trace_id: str
    retry_count: int = 0


# 全局队列
QUEUE: asyncio.Queue[StoreJob] = asyncio.Queue()

MAX_RETRIES = 3


async def enqueue_store(job: StoreJob):
    """将存储任务加入异步队列，不阻塞主流程"""
    await QUEUE.put(job)


async def _execute_store(store_service: Any, mem0_service: Any, job: StoreJob, max_retries: int = MAX_RETRIES) -> bool:
    """执行存储，支持指数退避重试"""
    for attempt in range(max_retries + 1):
        try:
            await store_service.execute(job.data)
            # 写入 mem0（失败不影响主流程）
            try:
                await mem0_service.add(job.user_id, job.data)
            except Exception as e:
                logger.warning(f"mem0 write failed (non-fatal): {e}")
            return True
        except Exception as e:
            if attempt < max_retries:
                wait = 0.5 * (2 ** attempt)
                logger.warning(f"Store attempt {attempt + 1} failed, retrying in {wait}s: {e}")
                await asyncio.sleep(wait)
            else:
                logger.error(f"Store failed after {max_retries} retries for trace_id={job.trace_id}: {e}")
                return False


async def store_worker(store_service: Any, mem0_service: Any):
    """后台消费队列"""
    while True:
        try:
            job = await QUEUE.get()
            success = await _execute_store(store_service, mem0_service, job)
            if not success:
                logger.error(f"Dead letter: store job failed for trace_id={job.trace_id}")
                # TODO: 写入 failed_operations 表
            QUEUE.task_done()
        except Exception as e:
            logger.exception(f"store_worker error: {e}")
