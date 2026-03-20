"""
Python 异步编程进阶

掌握基础 async/await 后，还需要了解并发控制、任务编排等高级模式。
本文件涵盖：
1. Semaphore 信号量（限制并发数）
2. asyncio.Queue 异步队列（生产者-消费者模式）
3. asyncio.shield() 防止取消
4. TaskGroup（Python 3.11+ 结构化并发）
5. 异步迭代器协议
6. 综合实战：带限流的并发爬虫模拟
"""

import asyncio
import random
import time
from typing import Any, AsyncIterator


# ==================== 1. Semaphore 信号量 ====================


async def limited_request(
    sem: asyncio.Semaphore, url: str, delay: float
) -> dict[str, Any]:
    """
    Semaphore 限制同时运行的协程数量。
    典型场景：限制并发 HTTP 请求数，避免打爆目标服务器。
    """
    async with sem:  # 获取信号量（并发数已满时阻塞）
        print(f"  → 请求开始: {url}")
        await asyncio.sleep(delay)
        print(f"  ← 请求完成: {url}")
        return {"url": url, "status": 200}


async def demo_semaphore() -> None:
    """虽然提交了 10 个请求，但最多只有 3 个同时执行。"""
    print("=== 1. Semaphore 信号量（限制并发数）===")

    sem: asyncio.Semaphore = asyncio.Semaphore(3)  # 最多 3 个并发

    urls: list[str] = [f"https://api.example.com/page/{i}" for i in range(8)]
    tasks: list[asyncio.Task[dict[str, Any]]] = [
        asyncio.create_task(limited_request(sem, url, random.uniform(0.3, 1.0)))
        for url in urls
    ]

    start: float = time.perf_counter()
    results: list[dict[str, Any]] = await asyncio.gather(*tasks)
    elapsed: float = time.perf_counter() - start

    print(f"  共 {len(results)} 个请求完成，耗时 {elapsed:.2f}s")
    print(f"  （如无限制约需 {sum(0.65 for _ in urls) / 8:.1f}s，限 3 并发约需更久）\n")


# ==================== 2. asyncio.Queue 异步队列 ====================


async def async_producer(
    queue: asyncio.Queue[str], producer_id: int, num_items: int
) -> None:
    """异步生产者：向队列中放入数据。"""
    for i in range(num_items):
        item: str = f"item-{producer_id}-{i}"
        await queue.put(item)  # 队列满时阻塞
        print(f"  [P{producer_id}] 放入: {item}（队列大小: {queue.qsize()}）")
        await asyncio.sleep(random.uniform(0.1, 0.3))


async def async_consumer(queue: asyncio.Queue[str], consumer_id: int) -> list[str]:
    """异步消费者：从队列中取数据，收到 None 时退出。"""
    consumed: list[str] = []
    while True:
        item: str = await queue.get()  # 队列空时阻塞
        if item is None:  # type: ignore[comparison-overlap]
            queue.task_done()
            break
        consumed.append(item)
        print(f"  [C{consumer_id}] 消费: {item}")
        await asyncio.sleep(random.uniform(0.1, 0.2))
        queue.task_done()  # 通知队列该任务已处理完毕（配合 join 使用）
    return consumed


async def demo_async_queue() -> None:
    """
    asyncio.Queue 是协程安全的 FIFO 队列，无需加锁。
    - maxsize=0 表示无限大小
    - put/get 在队列满/空时自动阻塞当前协程
    - task_done() + join() 实现优雅关闭
    """
    print("=== 2. asyncio.Queue 异步队列 ===")

    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=5)  # 最多缓存 5 个
    num_consumers: int = 2

    # 启动生产者和消费者
    producers: list[asyncio.Task[None]] = [
        asyncio.create_task(async_producer(queue, pid, 4))
        for pid in range(2)
    ]
    consumers: list[asyncio.Task[list[str]]] = [
        asyncio.create_task(async_consumer(queue, cid))
        for cid in range(num_consumers)
    ]

    # 等待所有生产者完成
    await asyncio.gather(*producers)

    # 发送哨兵值通知消费者退出
    for _ in range(num_consumers):
        await queue.put(None)  # type: ignore[arg-type]

    # 等待消费者完成
    all_consumed: list[list[str]] = await asyncio.gather(*consumers)
    total: int = sum(len(c) for c in all_consumed)
    print(f"  共消费 {total} 个项目\n")


# ==================== 3. asyncio.shield() 防止取消 ====================


async def critical_operation() -> str:
    """关键操作，不应被取消（如数据库事务提交）。"""
    print("  [critical] 开始执行关键操作...")
    await asyncio.sleep(2.0)
    print("  [critical] 关键操作完成")
    return "关键数据已保存"


async def demo_shield() -> None:
    """
    asyncio.shield(coro) 保护协程不被外部取消。
    即使外层 Task 被 cancel()，shield 内部的协程仍会继续执行。
    注意：shield 不能阻止 CancelledError 传播到调用者。
    """
    print("=== 3. asyncio.shield() 防止取消 ===")

    async def wrapper() -> str | None:
        try:
            return await asyncio.shield(critical_operation())
        except asyncio.CancelledError:
            print("  [wrapper] 外层被取消，但内部操作仍在运行")
            return None

    task: asyncio.Task[str | None] = asyncio.create_task(wrapper())
    await asyncio.sleep(0.5)

    # 尝试取消（shield 保护内部操作不受影响）
    task.cancel()

    try:
        result: str | None = await task
        print(f"  结果: {result}")
    except asyncio.CancelledError:
        print("  任务被取消")

    # 给 shield 内部的协程足够时间完成
    await asyncio.sleep(2.0)
    print()


# ==================== 4. TaskGroup 结构化并发（3.11+） ====================


async def fetch_page(page: int) -> dict[str, Any]:
    """模拟获取分页数据。"""
    delay: float = random.uniform(0.2, 0.8)
    await asyncio.sleep(delay)
    if page == 3:
        raise ValueError(f"第 {page} 页获取失败")
    return {"page": page, "items": [f"item_{page}_{i}" for i in range(3)]}


async def demo_task_group() -> None:
    """
    TaskGroup（Python 3.11+）是 gather 的结构化替代：
    - 用 async with 管理一组任务的生命周期
    - 任一任务异常时，自动取消所有其他任务
    - 异常通过 ExceptionGroup 聚合（可用 except* 处理）

    优势：不会像 gather 那样"泄漏"正在运行的任务。
    """
    print("=== 4. TaskGroup 结构化并发（3.11+）===")

    # --- 正常执行 ---
    print("--- 正常执行 ---")
    results: list[dict[str, Any]] = []

    async with asyncio.TaskGroup() as tg:
        tasks: list[asyncio.Task[dict[str, Any]]] = [
            tg.create_task(fetch_page(page)) for page in [1, 2, 4, 5]
        ]

    results = [t.result() for t in tasks]
    for r in results:
        print(f"  第 {r['page']} 页: {r['items']}")

    # --- 异常处理 ---
    print("\n--- 任一任务异常时，所有任务被取消 ---")
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(fetch_page(1))
            tg.create_task(fetch_page(3))  # 会失败
            tg.create_task(fetch_page(5))
    except* ValueError as eg:
        for exc in eg.exceptions:
            print(f"  捕获异常: {exc}")
    print()


# ==================== 5. 异步迭代器协议 ====================


class AsyncCounter:
    """
    实现异步迭代器协议：
    - __aiter__() → 返回自身
    - __anext__() → 返回下一个值或 raise StopAsyncIteration

    类似同步的 __iter__ / __next__，但可以在 __anext__ 中 await。
    """

    def __init__(self, start: int, stop: int) -> None:
        self.current: int = start
        self.stop: int = stop

    def __aiter__(self) -> "AsyncCounter":
        return self

    async def __anext__(self) -> int:
        if self.current >= self.stop:
            raise StopAsyncIteration
        value: int = self.current
        self.current += 1
        await asyncio.sleep(0.1)  # 模拟异步获取下一个值
        return value


class AsyncDatabasePaginator:
    """实战示例：异步分页迭代器，自动翻页直到无更多数据。"""

    def __init__(self, table: str, page_size: int = 3) -> None:
        self.table: str = table
        self.page_size: int = page_size
        self._page: int = 0
        self._total_pages: int = 4  # 模拟总共 4 页

    def __aiter__(self) -> "AsyncDatabasePaginator":
        return self

    async def __anext__(self) -> list[dict[str, Any]]:
        if self._page >= self._total_pages:
            raise StopAsyncIteration

        await asyncio.sleep(0.2)  # 模拟数据库查询
        page_data: list[dict[str, Any]] = [
            {"id": self._page * self.page_size + i, "name": f"row_{i}"}
            for i in range(self.page_size)
        ]
        self._page += 1
        return page_data


async def demo_async_iterator() -> None:
    """async for 遍历异步迭代器。"""
    print("=== 5. 异步迭代器 ===")

    print("  AsyncCounter(0, 5):")
    async for num in AsyncCounter(0, 5):
        print(f"    {num}", end=" ")
    print()

    print("\n  异步分页迭代器:")
    async for page_rows in AsyncDatabasePaginator("users", page_size=2):
        print(f"    页数据: {page_rows}")
    print()


# ==================== 6. 综合实战：带限流的并发爬虫 ====================


class AsyncRateLimiter:
    """基于令牌桶算法的异步限流器。"""

    def __init__(self, rate: float, max_tokens: int = 10) -> None:
        """
        Args:
            rate: 每秒产生的令牌数
            max_tokens: 桶中最大令牌数
        """
        self._rate: float = rate
        self._max_tokens: int = max_tokens
        self._tokens: float = max_tokens
        self._last_refill: float = time.monotonic()
        self._lock: asyncio.Lock = asyncio.Lock()

    async def acquire(self) -> None:
        """获取一个令牌，令牌不足时等待。"""
        async with self._lock:
            while True:
                now: float = time.monotonic()
                elapsed: float = now - self._last_refill
                self._tokens = min(
                    self._max_tokens, self._tokens + elapsed * self._rate
                )
                self._last_refill = now

                if self._tokens >= 1:
                    self._tokens -= 1
                    return

                # 计算需要等待多久才能有一个令牌
                wait_time: float = (1 - self._tokens) / self._rate
                await asyncio.sleep(wait_time)


async def crawl_page(
    url: str,
    sem: asyncio.Semaphore,
    limiter: AsyncRateLimiter,
    results_queue: asyncio.Queue[dict[str, Any]],
) -> None:
    """模拟爬取单个页面，受信号量和限流器双重控制。"""
    await limiter.acquire()  # 限流
    async with sem:  # 限并发
        start: float = time.perf_counter()
        delay: float = random.uniform(0.2, 0.8)
        await asyncio.sleep(delay)
        result: dict[str, Any] = {
            "url": url,
            "status": 200,
            "latency": round(time.perf_counter() - start, 2),
            "size_kb": random.randint(10, 500),
        }
        await results_queue.put(result)


async def result_collector(
    queue: asyncio.Queue[dict[str, Any]], total: int
) -> list[dict[str, Any]]:
    """收集所有爬取结果。"""
    collected: list[dict[str, Any]] = []
    for _ in range(total):
        item: dict[str, Any] = await queue.get()
        collected.append(item)
        queue.task_done()
    return collected


async def demo_rate_limited_crawler() -> None:
    """
    综合运用 Semaphore + 限流器 + Queue 构建并发爬虫。
    - Semaphore 限制最大并发连接数
    - RateLimiter 限制每秒请求频率
    - Queue 解耦爬取与结果处理
    """
    print("=== 6. 综合实战：带限流的并发爬虫 ===")

    urls: list[str] = [f"https://example.com/page/{i}" for i in range(15)]
    sem: asyncio.Semaphore = asyncio.Semaphore(5)  # 最多 5 个并发
    limiter: AsyncRateLimiter = AsyncRateLimiter(rate=10.0)  # 每秒最多 10 个请求
    results_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    start: float = time.perf_counter()

    # 启动结果收集器
    collector_task: asyncio.Task[list[dict[str, Any]]] = asyncio.create_task(
        result_collector(results_queue, len(urls))
    )

    # 启动所有爬取任务
    crawl_tasks: list[asyncio.Task[None]] = [
        asyncio.create_task(crawl_page(url, sem, limiter, results_queue))
        for url in urls
    ]

    # 等待所有爬取完成
    await asyncio.gather(*crawl_tasks)

    # 等待结果收集完成
    results: list[dict[str, Any]] = await collector_task
    elapsed: float = time.perf_counter() - start

    print(f"  总页面: {len(results)}")
    print(f"  总耗时: {elapsed:.2f}s")
    avg_latency: float = sum(r["latency"] for r in results) / len(results)
    total_size: int = sum(r["size_kb"] for r in results)
    print(f"  平均延迟: {avg_latency:.2f}s")
    print(f"  总数据量: {total_size}KB")

    # 展示部分结果
    for r in results[:5]:
        print(f"    {r['url']}: {r['status']}, {r['latency']}s, {r['size_kb']}KB")
    if len(results) > 5:
        print(f"    ... 还有 {len(results) - 5} 个结果")
    print()


# ==================== 主流程 ====================


async def main() -> None:
    await demo_semaphore()
    await demo_async_queue()
    await demo_shield()
    await demo_task_group()
    await demo_async_iterator()
    await demo_rate_limited_crawler()


if __name__ == "__main__":
    asyncio.run(main())
