"""
Python 协程与 asyncio 基础

协程（coroutine）是 Python 异步编程的核心：
- 用 async def 定义协程函数，调用后返回协程对象
- 用 await 暂停当前协程，把控制权交回事件循环（event loop）
- 事件循环在单线程内调度多个协程，遇到 I/O 等待时切换到其他协程
- 相比多线程：无 GIL 限制、无上下文切换开销、无需加锁

适用场景：高并发 I/O 密集（网络请求、数据库查询、文件读写）
不适用场景：CPU 密集计算（应使用多进程）

本文件涵盖：
1. async/await 基础语法
2. asyncio.gather() 并发执行
3. asyncio.create_task() 任务调度
4. asyncio.wait() 灵活等待策略
5. asyncio.wait_for() 超时控制
6. 在协程中运行同步阻塞代码（run_in_executor）
7. 异步生成器（async generator）
8. 异步上下文管理器（async with）
"""

import asyncio
import time
from typing import Any, AsyncGenerator


# ==================== 1. async/await 基础 ====================


async def say_hello(name: str, delay: float) -> str:
    """
    async def 定义协程函数。
    await 只能在协程内部使用，用于等待另一个可等待对象（awaitable）。
    可等待对象包括：协程、Task、Future。
    """
    print(f"  [{name}] 开始（将等待 {delay}s）")
    await asyncio.sleep(delay)  # 非阻塞等待，让出控制权
    print(f"  [{name}] 完成")
    return f"Hello from {name}"


async def demo_basic() -> None:
    """最基本的协程调用。"""
    print("=== 1. async/await 基础 ===")

    # 直接 await 一个协程（串行执行）
    result: str = await say_hello("Alice", 1.0)
    print(f"  返回值: {result}")

    # 注意：直接调用协程函数只是创建了协程对象，不会执行
    coro = say_hello("Bob", 0.5)
    print(f"  协程对象类型: {type(coro)}")  # <class 'coroutine'>
    result = await coro  # 必须 await 才会执行
    print(f"  返回值: {result}\n")


# ==================== 2. asyncio.gather() 并发执行 ====================


async def fetch_api(endpoint: str, latency: float) -> dict[str, Any]:
    """模拟异步 API 请求。"""
    await asyncio.sleep(latency)
    return {"endpoint": endpoint, "data": f"response_{endpoint}", "latency": latency}


async def demo_gather() -> None:
    """
    asyncio.gather(*coros_or_futures) → 并发运行多个协程，返回结果列表。
    - 结果按传入顺序排列（保序）
    - 所有协程同时开始，总耗时 ≈ 最慢的那个
    - return_exceptions=True 时，异常作为结果返回而非抛出
    """
    print("=== 2. asyncio.gather() 并发执行 ===")

    start: float = time.perf_counter()

    # 并发请求 3 个 API
    results: list[dict[str, Any]] = await asyncio.gather(
        fetch_api("/users", 1.0),
        fetch_api("/orders", 2.0),
        fetch_api("/products", 0.5),
    )

    elapsed: float = time.perf_counter() - start
    print(f"  总耗时: {elapsed:.2f}s（串行需 3.5s）")
    for r in results:
        print(f"    {r['endpoint']}: {r['data']}")

    # --- return_exceptions=True 演示 ---
    print("\n--- return_exceptions=True ---")

    async def may_fail(name: str) -> str:
        if name == "bad":
            raise ValueError(f"任务 {name} 失败了")
        await asyncio.sleep(0.1)
        return f"{name} 成功"

    results_mixed: list[str | BaseException] = await asyncio.gather(
        may_fail("good1"),
        may_fail("bad"),
        may_fail("good2"),
        return_exceptions=True,  # 异常不会中断其他任务
    )
    for r in results_mixed:
        if isinstance(r, Exception):
            print(f"    ✗ 异常: {r}")
        else:
            print(f"    ✓ {r}")
    print()


# ==================== 3. asyncio.create_task() ====================


async def background_job(job_id: int, duration: float) -> str:
    """模拟后台任务。"""
    await asyncio.sleep(duration)
    return f"Job-{job_id} 完成（耗时 {duration}s）"


async def demo_create_task() -> None:
    """
    create_task(coro) 把协程包装成 Task 并立即调度到事件循环。
    Task 是 Future 的子类，可以取消、添加回调、获取结果。

    gather vs create_task:
    - gather：一次性提交一组协程，等待全部完成
    - create_task：更灵活，可以在任意时机创建、可以取消
    """
    print("=== 3. asyncio.create_task() ===")

    # 创建多个 Task（立即开始调度）
    tasks: list[asyncio.Task[str]] = [
        asyncio.create_task(background_job(i, 1.0 + i * 0.5), name=f"task-{i}")
        for i in range(3)
    ]

    print("  任务已创建，主协程可以做其他事情...")
    await asyncio.sleep(0.5)
    print("  主协程做完其他事了，开始等待任务结果...")

    # 等待所有 Task 完成
    for task in tasks:
        result: str = await task
        print(f"    {task.get_name()}: {result}")

    # --- Task 取消演示 ---
    print("\n--- Task 取消演示 ---")
    long_task: asyncio.Task[str] = asyncio.create_task(
        background_job(99, 10.0), name="long-task"
    )
    await asyncio.sleep(0.1)
    long_task.cancel()  # 取消任务
    try:
        await long_task
    except asyncio.CancelledError:
        print(f"  {long_task.get_name()} 已被取消")
    print()


# ==================== 4. asyncio.wait() ====================


async def variable_task(task_id: int) -> str:
    """耗时不等的任务。"""
    delay: float = task_id * 0.5
    await asyncio.sleep(delay)
    return f"task-{task_id} (耗时{delay}s)"


async def demo_wait() -> None:
    """
    asyncio.wait(tasks, return_when=...) → (done, pending)
    - FIRST_COMPLETED：任一完成就返回
    - FIRST_EXCEPTION：任一异常就返回
    - ALL_COMPLETED：全部完成（默认）

    与 gather 的区别：wait 返回的是集合，不保序，更灵活。
    """
    print("=== 4. asyncio.wait() ===")

    tasks: set[asyncio.Task[str]] = {
        asyncio.create_task(variable_task(i), name=f"task-{i}")
        for i in range(1, 5)
    }

    # 等待第一个完成
    done: set[asyncio.Task[str]]
    pending: set[asyncio.Task[str]]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    print(f"  FIRST_COMPLETED: {len(done)} 完成, {len(pending)} 待完成")
    for t in done:
        print(f"    ✓ {t.result()}")

    # 继续等待剩余全部完成
    if pending:
        done2, _ = await asyncio.wait(pending, return_when=asyncio.ALL_COMPLETED)
        print(f"  ALL_COMPLETED: 剩余 {len(done2)} 个完成")
        for t in done2:
            print(f"    ✓ {t.result()}")
    print()


# ==================== 5. asyncio.wait_for() 超时控制 ====================


async def slow_operation() -> str:
    """一个很慢的操作。"""
    await asyncio.sleep(5.0)
    return "操作完成"


async def demo_wait_for() -> None:
    """
    asyncio.wait_for(coro, timeout) → 给协程设置超时。
    超时后抛出 asyncio.TimeoutError，协程会被自动取消。
    """
    print("=== 5. asyncio.wait_for() 超时控制 ===")

    try:
        result: str = await asyncio.wait_for(slow_operation(), timeout=1.0)
        print(f"  结果: {result}")
    except asyncio.TimeoutError:
        print("  ⏰ 超时！操作已被自动取消")

    # Python 3.11+ 推荐使用 asyncio.timeout() 上下文管理器
    print("\n--- asyncio.timeout() 上下文管理器（3.11+）---")
    try:
        async with asyncio.timeout(1.0):
            await asyncio.sleep(5.0)
            print("  这行不会被执行")
    except asyncio.TimeoutError:
        print("  ⏰ timeout 上下文管理器超时")
    print()


# ==================== 6. run_in_executor：在协程中运行同步代码 ====================


def blocking_io(path: str) -> str:
    """模拟阻塞 I/O（如调用不支持异步的第三方库）。"""
    time.sleep(1.5)  # time.sleep 是阻塞的，不能直接在协程中用
    return f"读取 {path} 完成"


def cpu_heavy(n: int) -> int:
    """CPU 密集计算。"""
    return sum(i * i for i in range(n))


async def demo_run_in_executor() -> None:
    """
    loop.run_in_executor(executor, func, *args)
    把同步阻塞函数放到线程池/进程池中执行，不阻塞事件循环。

    - executor=None：使用默认线程池
    - 可传入 ThreadPoolExecutor 或 ProcessPoolExecutor
    """
    print("=== 6. run_in_executor ===")
    loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()

    start: float = time.perf_counter()

    # 把两个阻塞调用放到线程池并发执行
    result1: str
    result2: str
    result1, result2 = await asyncio.gather(
        loop.run_in_executor(None, blocking_io, "/data/file1.csv"),
        loop.run_in_executor(None, blocking_io, "/data/file2.csv"),
    )

    elapsed: float = time.perf_counter() - start
    print(f"  {result1}")
    print(f"  {result2}")
    print(f"  并发耗时: {elapsed:.2f}s（串行需 3.0s）")

    # asyncio.to_thread()（Python 3.9+ 简化写法）
    print("\n--- asyncio.to_thread()（3.9+ 推荐）---")
    result3: str = await asyncio.to_thread(blocking_io, "/data/file3.csv")
    print(f"  {result3}\n")


# ==================== 7. 异步生成器 ====================


async def async_countdown(start: int) -> AsyncGenerator[int, None]:
    """
    async def + yield = 异步生成器。
    和普通生成器类似，但每次 yield 之间可以 await。
    """
    current: int = start
    while current > 0:
        await asyncio.sleep(0.3)
        yield current
        current -= 1


async def async_range(start: int, stop: int, step: int = 1) -> AsyncGenerator[int, None]:
    """异步版 range，每步之间有延迟。"""
    current: int = start
    while current < stop:
        await asyncio.sleep(0.1)
        yield current
        current += step


async def demo_async_generator() -> None:
    """
    异步生成器用 async for 迭代。
    适合：流式数据处理、SSE 事件流、分页 API 拉取等场景。
    """
    print("=== 7. 异步生成器 ===")

    print("  倒计时:")
    async for num in async_countdown(5):
        print(f"    {num}...")
    print("    发射！")

    print("\n  异步 range(0, 10, 3):")
    values: list[int] = [v async for v in async_range(0, 10, 3)]  # 异步列表推导
    print(f"    {values}\n")


# ==================== 8. 异步上下文管理器 ====================


class AsyncDatabaseConnection:
    """
    async with 需要实现 __aenter__ 和 __aexit__。
    典型场景：异步数据库连接、HTTP session、文件操作。
    """

    def __init__(self, db_url: str) -> None:
        self.db_url: str = db_url
        self.connected: bool = False

    async def __aenter__(self) -> "AsyncDatabaseConnection":
        print(f"  连接数据库: {self.db_url}")
        await asyncio.sleep(0.3)  # 模拟连接耗时
        self.connected = True
        print("  连接成功")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        print("  关闭数据库连接")
        await asyncio.sleep(0.1)
        self.connected = False
        if exc_type:
            print(f"  异常被捕获: {exc_val}")

    async def query(self, sql: str) -> list[dict[str, Any]]:
        if not self.connected:
            raise RuntimeError("未连接数据库")
        await asyncio.sleep(0.2)
        return [{"id": 1, "sql": sql, "result": "mock_data"}]


async def demo_async_context_manager() -> None:
    """async with 自动管理异步资源的获取与释放。"""
    print("=== 8. 异步上下文管理器 ===")

    async with AsyncDatabaseConnection("postgresql://localhost/mydb") as db:
        results: list[dict[str, Any]] = await db.query("SELECT * FROM users")
        print(f"  查询结果: {results}")
    print()


# ==================== 主流程 ====================


async def main() -> None:
    await demo_basic()
    await demo_gather()
    await demo_create_task()
    await demo_wait()
    await demo_wait_for()
    await demo_run_in_executor()
    await demo_async_generator()
    await demo_async_context_manager()


if __name__ == "__main__":
    asyncio.run(main())
