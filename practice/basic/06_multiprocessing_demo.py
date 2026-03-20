"""
Python 多进程（multiprocessing）

线程受 GIL 限制无法并行 CPU 密集任务；多进程能真正利用多核。
每个进程有独立的内存空间，进程间通信需通过 Queue / Pipe / 共享内存。

本文件涵盖：
1. Process 基本用法
2. 进程间通信：Queue、Pipe
3. 共享状态：Value、Array、Manager
4. 进程池：Pool（旧接口）
5. ProcessPoolExecutor（推荐的高层接口）
6. CPU 密集任务对比：多线程 vs 多进程
"""

import math
import multiprocessing
import os
import time
from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from multiprocessing import Process, Queue, Pipe, Value, Array, Manager
from multiprocessing.connection import Connection
from typing import Any


# ==================== 1. Process 基本用法 ====================


def cpu_work(name: str, n: int) -> None:
    """CPU 密集任务：计算阶乘。"""
    pid: int = os.getpid()
    print(f"  [进程 {pid}] 任务 '{name}' 开始，计算 {n}!")
    result: int = math.factorial(n)
    print(f"  [进程 {pid}] 任务 '{name}' 完成，{n}! 的位数 = {len(str(result))}")


def demo_basic_process() -> None:
    """创建并启动子进程，与线程 API 类似。"""
    print("=== 1. Process 基本用法 ===")
    print(f"主进程 PID: {os.getpid()}")

    p1: Process = Process(target=cpu_work, args=("计算A", 50000), name="Worker-A")
    p2: Process = Process(target=cpu_work, args=("计算B", 60000), name="Worker-B")

    p1.start()
    p2.start()

    # join() 等待子进程结束
    p1.join()
    p2.join()

    print(f"  p1 退出码: {p1.exitcode}, p2 退出码: {p2.exitcode}\n")


# ==================== 2. 进程间通信：Queue ====================


def producer_queue(q: "Queue[str]", items: list[str]) -> None:
    """生产者：往队列中放数据。"""
    for item in items:
        q.put(item)
        print(f"  [producer pid={os.getpid()}] 放入: {item}")
        time.sleep(0.2)
    q.put("STOP")  # 哨兵值，通知消费者结束


def consumer_queue(q: "Queue[str]") -> None:
    """消费者：从队列中取数据，直到收到 STOP。"""
    while True:
        item: str = q.get()  # 阻塞等待
        if item == "STOP":
            print(f"  [consumer pid={os.getpid()}] 收到 STOP，退出")
            break
        print(f"  [consumer pid={os.getpid()}] 取出: {item}")


def demo_queue() -> None:
    """
    multiprocessing.Queue 是进程安全的 FIFO 队列。
    底层通过 Pipe + 锁实现，数据会被 pickle 序列化传输。
    """
    print("=== 2. 进程间通信：Queue ===")
    q: Queue[str] = Queue()

    p_prod: Process = Process(target=producer_queue, args=(q, ["苹果", "香蕉", "橘子"]))
    p_cons: Process = Process(target=consumer_queue, args=(q,))

    p_prod.start()
    p_cons.start()
    p_prod.join()
    p_cons.join()
    print()


# ==================== 3. 进程间通信：Pipe ====================


def sender(conn: Connection) -> None:
    """Pipe 发送端。"""
    messages: list[str] = ["hello", "world", "done"]
    for msg in messages:
        conn.send(msg)
        print(f"  [sender pid={os.getpid()}] 发送: {msg}")
        time.sleep(0.2)
    conn.close()


def receiver(conn: Connection) -> None:
    """Pipe 接收端。"""
    while True:
        try:
            msg: str = conn.recv()  # 阻塞等待
            print(f"  [receiver pid={os.getpid()}] 接收: {msg}")
            if msg == "done":
                break
        except EOFError:
            break
    conn.close()


def demo_pipe() -> None:
    """
    Pipe() 返回一对 Connection 对象，默认双向通信。
    比 Queue 更轻量，适合两个进程之间点对点通信。
    """
    print("=== 3. 进程间通信：Pipe ===")
    parent_conn: Connection
    child_conn: Connection
    parent_conn, child_conn = Pipe()

    p_send: Process = Process(target=sender, args=(parent_conn,))
    p_recv: Process = Process(target=receiver, args=(child_conn,))

    p_send.start()
    p_recv.start()
    p_send.join()
    p_recv.join()
    print()


# ==================== 4. 共享状态：Value / Array ====================


def increment_shared(counter: "Value[int]", lock: multiprocessing.Lock, n: int) -> None:  # type: ignore[type-arg]
    """多进程对共享计数器累加，必须加锁。"""
    for _ in range(n):
        with lock:
            counter.value += 1


def demo_shared_state() -> None:
    """
    Value(typecode, init) 和 Array(typecode, size_or_init)
    在进程间共享基本类型数据（底层使用共享内存）。
    typecode: 'i' = int, 'd' = double, 'c' = char 等。
    """
    print("=== 4. 共享状态：Value / Array ===")

    counter: Value = Value("i", 0)  # 共享整数，初始值 0
    lock: multiprocessing.Lock = multiprocessing.Lock()

    processes: list[Process] = [
        Process(target=increment_shared, args=(counter, lock, 1000))
        for _ in range(4)
    ]
    for p in processes:
        p.start()
    for p in processes:
        p.join()

    print(f"  共享计数器最终值: {counter.value}（期望 4000）")

    # Array 示例
    shared_arr: Array = Array("d", [0.0, 0.0, 0.0])  # 3 个 double
    print(f"  共享数组: {list(shared_arr)}\n")


# ==================== 5. Manager（更灵活的共享对象） ====================


def worker_manager(
    shared_dict: dict[str, int], shared_list: list[int], worker_id: int
) -> None:
    """通过 Manager 共享的 dict/list 可以像普通对象一样使用。"""
    shared_dict[f"worker_{worker_id}"] = os.getpid()
    shared_list.append(worker_id)


def demo_manager() -> None:
    """
    Manager 通过代理对象（Proxy）支持共享 dict、list、Namespace 等复杂类型。
    底层通过 socket 通信，比 Value/Array 慢，但更灵活。
    """
    print("=== 5. Manager 共享复杂对象 ===")

    with Manager() as manager:
        shared_dict: dict[str, int] = manager.dict()  # type: ignore[assignment]
        shared_list: list[int] = manager.list()  # type: ignore[assignment]

        processes: list[Process] = [
            Process(target=worker_manager, args=(shared_dict, shared_list, i))
            for i in range(4)
        ]
        for p in processes:
            p.start()
        for p in processes:
            p.join()

        print(f"  shared_dict: {dict(shared_dict)}")
        print(f"  shared_list: {list(shared_list)}\n")


# ==================== 6. ProcessPoolExecutor ====================

# 与 ThreadPoolExecutor API 完全一致，区别是：
# - 任务在子进程中执行（真正并行）
# - 参数和返回值必须可 pickle 序列化
# - 创建进程开销更大，适合粗粒度、CPU 密集任务


def is_prime(n: int) -> bool:
    """判断素数（CPU 密集）。"""
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i: int = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def count_primes_in_range(start: int, end: int) -> int:
    """统计 [start, end) 范围内的素数个数。"""
    return sum(1 for n in range(start, end) if is_prime(n))


def demo_process_pool_executor() -> None:
    """用 ProcessPoolExecutor 并行计算素数。"""
    print("=== 6. ProcessPoolExecutor ===")
    total: int = 500_000
    chunk_size: int = 100_000

    # 把区间拆分成多个子区间
    ranges: list[tuple[int, int]] = [
        (i, min(i + chunk_size, total)) for i in range(0, total, chunk_size)
    ]

    # --- 串行 ---
    start: float = time.perf_counter()
    serial_count: int = count_primes_in_range(0, total)
    serial_time: float = time.perf_counter() - start
    print(f"  串行: {serial_count} 个素数, 耗时 {serial_time:.2f}s")

    # --- 多进程并行 ---
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures: list[Future[int]] = [
            executor.submit(count_primes_in_range, s, e) for s, e in ranges
        ]
        parallel_count: int = sum(f.result() for f in as_completed(futures))
    parallel_time: float = time.perf_counter() - start
    print(f"  并行: {parallel_count} 个素数, 耗时 {parallel_time:.2f}s")
    print(f"  加速比: {serial_time / parallel_time:.1f}x\n")


# ==================== 7. 对比：多线程 vs 多进程 ====================


def cpu_bound_work(n: int) -> int:
    """纯 CPU 密集任务。"""
    return sum(i * i for i in range(n))


def demo_thread_vs_process() -> None:
    """
    CPU 密集任务下的对比：
    - 多线程受 GIL 限制，无法真正并行
    - 多进程能利用多核，显著加速
    """
    print("=== 7. CPU 密集：多线程 vs 多进程 ===")
    work_size: int = 2_000_000
    num_workers: int = 4

    from concurrent.futures import ThreadPoolExecutor

    # 多线程
    start: float = time.perf_counter()
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        list(executor.map(cpu_bound_work, [work_size] * num_workers))
    thread_time: float = time.perf_counter() - start

    # 多进程
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        list(executor.map(cpu_bound_work, [work_size] * num_workers))
    process_time: float = time.perf_counter() - start

    print(f"  多线程耗时: {thread_time:.2f}s")
    print(f"  多进程耗时: {process_time:.2f}s")
    print(f"  多进程加速比: {thread_time / process_time:.1f}x")
    print("  → CPU 密集任务应优先使用多进程\n")


# ==================== 主流程 ====================

if __name__ == "__main__":
    demo_basic_process()
    demo_queue()
    demo_pipe()
    demo_shared_state()
    demo_manager()
    demo_process_pool_executor()
    demo_thread_vs_process()
