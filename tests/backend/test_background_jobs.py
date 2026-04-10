import pytest
from assistant.backend.service.background_jobs import StoreJob, QUEUE


@pytest.mark.asyncio
async def test_enqueue_does_not_block():
    """入队后立即返回，不等待写入完成"""
    job = StoreJob(user_id="u1", data={"amount": 30}, trace_id="t1")
    await QUEUE.put(job)
    assert QUEUE.qsize() == 1


@pytest.mark.asyncio
async def test_store_job_creation():
    job = StoreJob(user_id="u1", data={"amount": 30, "category": "餐饮"}, trace_id="trace-123")
    assert job.user_id == "u1"
    assert job.retry_count == 0
