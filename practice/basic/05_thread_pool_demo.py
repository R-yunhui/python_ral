"""
Python 线程池（ThreadPoolExecutor）

手动管理线程（创建、启动、join）在任务数量多时非常繁琐。
concurrent.futures 模块提供了高层级的线程池（和进程池）抽象：
- 自动管理线程的创建与回收
- 通过 Future 对象获取异步结果
- 支持批量提交、超时控制、异常处理

本文件涵盖：
1. submit() + Future 基本用法
2. map() 批量提交（保序返回）
3. as_completed() 按完成顺序获取结果
4. Future 的回调（add_done_callback）
5. 异常处理与超时
6. 实战：并发 HTTP 请求模拟
"""

import time
from concurrent.futures import (
    Future,
    ThreadPoolExecutor,
    as_completed,
    wait,
    FIRST_COMPLETED,
    ALL_COMPLETED,
)
from typing import Any


# ==================== 1. submit() + Future 基本用法 ====================


def fetch_url(url: str, delay: float) -> dict[str, Any]:
    """模拟一个 HTTP 请求，返回结果字典。"""
    time.sleep(delay)
    return {"url": url, "status": 200, "body": f"Response from {url}"}


def demo_submit() -> None:
    """
    submit(fn, *args, **kwargs) → Future
    Future 代表一个"将来会有结果"的占位符。
    """
    print("=== 1. submit() + Future ===")

    # max_workers：线程池中最大线程数，默认 min(32, os.cpu_count() + 4)
    with ThreadPoolExecutor(max_workers=3) as executor:
        # submit 返回 Future 对象（非阻塞）
        future: Future[dict[str, Any]] = executor.submit(
            fetch_url, "https://example.com", 1.0
        )

        print(f"  Future 是否完成: {future.done()}")  # 刚提交，通常 False
        print(f"  Future 是否运行中: {future.running()}")

        # result() 阻塞等待结果（可设 timeout 参数）
        result: dict[str, Any] = future.result(timeout=5.0)
        print(f"  结果: {result}")
        print(f"  Future 是否完成: {future.done()}\n")  # 现在是 True


# ==================== 2. map() 批量提交 ====================


def square(n: int) -> int:
    """计算平方，模拟少量耗时。"""
    time.sleep(0.3)
    return n * n


def demo_map() -> None:
    """
    executor.map(fn, *iterables, timeout=None) → Iterator
    - 类似内置 map()，但并发执行
    - 结果按提交顺序返回（保序），而非完成顺序
    - 任何一个任务抛异常，迭代到该结果时会重新抛出
    """
    print("=== 2. map() 批量提交（保序返回）===")
    numbers: list[int] = [1, 2, 3, 4, 5, 6, 7, 8]

    start: float = time.perf_counter()
    with ThreadPoolExecutor(max_workers=4) as executor:
        results: list[int] = list(executor.map(square, numbers))
    elapsed: float = time.perf_counter() - start

    print(f"  输入: {numbers}")
    print(f"  结果: {results}")
    print(f"  耗时: {elapsed:.2f}s（串行需 {len(numbers) * 0.3:.1f}s）\n")


# ==================== 3. as_completed() 按完成顺序获取 ====================


def download_file(filename: str, size_mb: float) -> str:
    """模拟下载文件，size 越大耗时越长。"""
    time.sleep(size_mb * 0.5)
    return f"{filename} ({size_mb}MB) 下载完成"


def demo_as_completed() -> None:
    """
    as_completed(futures) → Iterator[Future]
    - 哪个先完成就先返回哪个（不保序）
    - 适合"尽早处理已完成任务"的场景
    """
    print("=== 3. as_completed() 按完成顺序获取 ===")
    tasks: list[tuple[str, float]] = [
        ("large.zip", 3.0),
        ("small.txt", 0.5),
        ("medium.pdf", 1.5),
    ]

    with ThreadPoolExecutor(max_workers=3) as executor:
        # 用字典映射 Future → 任务名，便于追踪
        future_to_name: dict[Future[str], str] = {
            executor.submit(download_file, name, size): name
            for name, size in tasks
        }

        for future in as_completed(future_to_name):
            name: str = future_to_name[future]
            try:
                result: str = future.result()
                print(f"  ✓ {result}")
            except Exception as exc:
                print(f"  ✗ {name} 出错: {exc}")
    print()


# ==================== 4. Future 回调 ====================


def heavy_computation(n: int) -> int:
    """模拟重计算。"""
    time.sleep(1)
    return n ** 3


def on_complete(future: Future[int]) -> None:
    """
    回调函数：Future 完成时自动调用（在线程池的某个线程中执行）。
    注意：回调中不要做耗时操作，否则会阻塞线程池。
    """
    if future.exception():
        print(f"  [callback] 任务失败: {future.exception()}")
    else:
        print(f"  [callback] 任务成功，结果: {future.result()}")


def demo_callback() -> None:
    """add_done_callback：任务完成时自动触发回调，无需手动轮询。"""
    print("=== 4. Future 回调（add_done_callback）===")

    with ThreadPoolExecutor(max_workers=2) as executor:
        future: Future[int] = executor.submit(heavy_computation, 5)
        future.add_done_callback(on_complete)

        # 主线程可以继续做别的事
        print("  主线程：任务已提交，继续做其他事情...")
        time.sleep(1.5)
    print()


# ==================== 5. 异常处理与超时 ====================


def risky_task(task_id: int) -> str:
    """模拟一个可能失败的任务。"""
    time.sleep(0.5)
    if task_id == 2:
        raise ValueError(f"任务 {task_id} 执行失败！")
    return f"任务 {task_id} 成功"


def demo_exception_handling() -> None:
    """Future 的异常不会立即抛出，直到调用 result() 或 exception() 时才会传播。"""
    print("=== 5. 异常处理 ===")

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures: list[Future[str]] = [
            executor.submit(risky_task, i) for i in range(4)
        ]

        for future in as_completed(futures):
            # 方式一：try-except 包裹 result()
            try:
                result: str = future.result()
                print(f"  ✓ {result}")
            except ValueError as e:
                print(f"  ✗ 捕获异常: {e}")

    # --- 超时演示 ---
    print("\n--- 超时演示 ---")
    with ThreadPoolExecutor(max_workers=1) as executor:
        future: Future[dict[str, Any]] = executor.submit(
            fetch_url, "https://slow-api.com", 3.0
        )
        try:
            result_timeout: dict[str, Any] = future.result(timeout=1.0)
        except TimeoutError:
            print("  ⏰ 任务超时！（但任务仍在后台运行）")
            # cancel() 只能取消尚未开始的任务；已开始的无法取消
            cancelled: bool = future.cancel()
            print(f"  取消结果: {cancelled}")
    print()


# ==================== 6. wait() 等待策略 ====================


def demo_wait() -> None:
    """
    wait(futures, timeout, return_when) → (done_set, not_done_set)
    - FIRST_COMPLETED：任意一个完成就返回
    - ALL_COMPLETED：全部完成才返回（默认）
    - FIRST_EXCEPTION：任意一个抛异常就返回
    """
    print("=== 6. wait() 等待策略 ===")

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures: list[Future[str]] = [
            executor.submit(download_file, "fast.txt", 0.5),
            executor.submit(download_file, "slow.zip", 2.0),
            executor.submit(download_file, "mid.pdf", 1.0),
        ]

        # 等待第一个完成
        done, not_done = wait(futures, return_when=FIRST_COMPLETED)
        print(f"  FIRST_COMPLETED: {len(done)} 个完成, {len(not_done)} 个未完成")
        for f in done:
            print(f"    ✓ {f.result()}")

        # 等待全部完成
        done, not_done = wait(not_done, return_when=ALL_COMPLETED)
        print(f"  ALL_COMPLETED: 剩余 {len(done)} 个全部完成")
        for f in done:
            print(f"    ✓ {f.result()}")
    print()


# ==================== 7. 实战：并发请求模拟 ====================


def api_request(endpoint: str) -> dict[str, Any]:
    """模拟调用不同 API 端点。"""
    latency_map: dict[str, float] = {
        "/users": 0.8,
        "/orders": 1.2,
        "/products": 0.5,
        "/reviews": 1.0,
        "/inventory": 0.3,
    }
    latency: float = latency_map.get(endpoint, 1.0)
    time.sleep(latency)
    return {"endpoint": endpoint, "data_count": int(latency * 100)}


def demo_concurrent_requests() -> None:
    """实战场景：后端聚合层同时请求多个微服务，合并结果后返回。"""
    print("=== 7. 实战：并发 API 请求 ===")
    endpoints: list[str] = ["/users", "/orders", "/products", "/reviews", "/inventory"]

    # --- 串行 ---
    start: float = time.perf_counter()
    serial_results: list[dict[str, Any]] = [api_request(ep) for ep in endpoints]
    serial_time: float = time.perf_counter() - start
    print(f"  串行耗时: {serial_time:.2f}s")

    # --- 并发 ---
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=5) as executor:
        concurrent_results: list[dict[str, Any]] = list(
            executor.map(api_request, endpoints)
        )
    concurrent_time: float = time.perf_counter() - start
    print(f"  并发耗时: {concurrent_time:.2f}s")
    print(f"  加速比: {serial_time / concurrent_time:.1f}x")

    for r in concurrent_results:
        print(f"    {r['endpoint']}: {r['data_count']} 条数据")
    print()


# ==================== 主流程 ====================

if __name__ == "__main__":
    demo_submit()
    demo_map()
    demo_as_completed()
    demo_callback()
    demo_exception_handling()
    demo_wait()
    demo_concurrent_requests()
