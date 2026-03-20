"""
Python 多线程（threading）基础

线程是操作系统调度的最小单位，共享同一进程的内存空间。
Python 由于 GIL（全局解释器锁）的存在，多线程无法真正并行执行 CPU 密集任务，
但对 I/O 密集（网络请求、文件读写、sleep 等）场景依然能显著提升吞吐。

本文件涵盖：
1. 创建线程的两种方式（函数式 / 继承 Thread）
2. 守护线程（daemon thread）
3. 线程同步：Lock、RLock
4. 线程事件：Event
5. 线程本地数据：threading.local()
6. Condition 条件变量（生产者-消费者模型）
"""

import threading
import time
from typing import Any


# ==================== 1. 创建线程的两种方式 ====================


# ---------- 1.1 函数式：传 target + args ----------
def worker(name: str, seconds: float) -> None:
    """模拟一个耗时 I/O 任务。"""
    thread_name: str = threading.current_thread().name
    print(f"[{thread_name}] 任务 '{name}' 开始，预计 {seconds}s")
    time.sleep(seconds)
    print(f"[{thread_name}] 任务 '{name}' 完成")


def demo_target_thread() -> None:
    """用 target 参数把普通函数交给线程执行。"""
    print("=== 1.1 函数式创建线程 ===")

    # 创建两个线程，name 参数可选，方便调试
    t1: threading.Thread = threading.Thread(
        target=worker, args=("下载文件", 2), name="Thread-Download"
    )
    t2: threading.Thread = threading.Thread(
        target=worker, args=("写入数据库", 1.5), name="Thread-DB"
    )

    t1.start()  # 启动线程（非阻塞，立即返回）
    t2.start()

    # join()：阻塞当前线程，直到目标线程执行完毕
    t1.join()
    t2.join()
    print("两个线程全部完成\n")


# ---------- 1.2 继承 Thread：重写 run() ----------
class DownloadThread(threading.Thread):
    """继承 Thread，重写 run() 方法来定义线程执行逻辑。"""

    def __init__(self, url: str, timeout: float) -> None:
        super().__init__(name=f"Download-{url[:20]}")
        self.url: str = url
        self.timeout: float = timeout
        self.result: str | None = None  # 存放执行结果

    def run(self) -> None:
        """线程启动后自动调用此方法。"""
        print(f"[{self.name}] 开始下载: {self.url}")
        time.sleep(self.timeout)
        self.result = f"来自 {self.url} 的数据"
        print(f"[{self.name}] 下载完成")


def demo_subclass_thread() -> None:
    """继承 Thread 方式：适合需要保存线程状态 / 结果的场景。"""
    print("=== 1.2 继承 Thread 创建线程 ===")

    threads: list[DownloadThread] = [
        DownloadThread("https://api.example.com/users", 1.0),
        DownloadThread("https://api.example.com/orders", 1.5),
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for t in threads:
        print(f"  结果: {t.result}")
    print()


# ==================== 2. 守护线程（Daemon Thread） ====================


def background_heartbeat(interval: float) -> None:
    """
    守护线程：主线程结束时自动被杀死，不会阻止程序退出。
    典型用途：心跳检测、日志写入、监控等后台任务。
    """
    while True:
        print(f"  [heartbeat] {time.strftime('%H:%M:%S')} ❤")
        time.sleep(interval)


def demo_daemon_thread() -> None:
    """daemon=True 的线程不会阻止主线程退出。"""
    print("=== 2. 守护线程 ===")
    t: threading.Thread = threading.Thread(
        target=background_heartbeat, args=(0.5,), daemon=True
    )
    t.start()
    time.sleep(1.6)  # 主线程只等 1.6s，之后 daemon 线程自动终止
    print("主线程结束，daemon 线程随之退出\n")


# ==================== 3. 线程同步：Lock / RLock ====================

# 多线程共享变量时，不加锁会导致竞态条件（race condition）。
# Lock：同一时刻只允许一个线程进入临界区。
# RLock（可重入锁）：同一线程可多次 acquire，不会死锁自己。


class BankAccount:
    """
    用 Lock 保护共享数据的经典示例。
    不加锁时，并发 deposit/withdraw 会导致余额不一致。
    """

    def __init__(self, balance: float = 0.0) -> None:
        self._balance: float = balance
        self._lock: threading.Lock = threading.Lock()

    @property
    def balance(self) -> float:
        return self._balance

    def deposit(self, amount: float) -> None:
        with self._lock:  # with 语句自动 acquire + release，更安全
            current: float = self._balance
            time.sleep(0.001)  # 模拟一小段处理时间，放大竞态
            self._balance = current + amount

    def withdraw(self, amount: float) -> bool:
        with self._lock:
            if self._balance >= amount:
                current: float = self._balance
                time.sleep(0.001)
                self._balance = current - amount
                return True
            return False


def demo_lock() -> None:
    """对比加锁和不加锁的结果差异。"""
    print("=== 3. Lock 线程同步 ===")
    account: BankAccount = BankAccount(balance=0.0)

    def do_deposits(n: int) -> None:
        for _ in range(n):
            account.deposit(1.0)

    threads: list[threading.Thread] = [
        threading.Thread(target=do_deposits, args=(100,)) for _ in range(5)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 5 个线程各存 100 次 1.0，期望余额 = 500.0
    print(f"  最终余额: {account.balance}（期望 500.0）\n")


# ---------- RLock 示例 ----------
class SafeCounter:
    """
    RLock 允许同一线程多次 acquire 而不死锁。
    适用于：一个方法内部调用了另一个同样需要加锁的方法。
    """

    def __init__(self) -> None:
        self._count: int = 0
        self._lock: threading.RLock = threading.RLock()

    def increment(self) -> None:
        with self._lock:
            self._count += 1

    def increment_twice(self) -> None:
        with self._lock:  # 第一次 acquire
            self.increment()  # 内部再次 acquire 同一把 RLock，OK
            self.increment()

    @property
    def count(self) -> int:
        return self._count


def demo_rlock() -> None:
    print("=== 3.1 RLock 可重入锁 ===")
    counter: SafeCounter = SafeCounter()

    threads: list[threading.Thread] = [
        threading.Thread(target=counter.increment_twice) for _ in range(100)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"  最终计数: {counter.count}（期望 200）\n")


# ==================== 4. 线程事件：Event ====================


def demo_event() -> None:
    """
    Event 是线程间的信号量：
    - event.set()     → 发信号
    - event.wait()    → 阻塞直到信号被 set
    - event.clear()   → 重置信号
    - event.is_set()  → 检查信号是否已设置
    """
    print("=== 4. Event 线程事件 ===")
    data_ready: threading.Event = threading.Event()
    shared_data: dict[str, Any] = {}

    def producer() -> None:
        print("  [producer] 准备数据中...")
        time.sleep(1)
        shared_data["value"] = 42
        data_ready.set()  # 通知消费者数据已就绪
        print("  [producer] 数据已就绪，通知消费者")

    def consumer() -> None:
        print("  [consumer] 等待数据...")
        data_ready.wait()  # 阻塞直到 set()
        print(f"  [consumer] 收到数据: {shared_data['value']}")

    t_prod: threading.Thread = threading.Thread(target=producer)
    t_cons: threading.Thread = threading.Thread(target=consumer)
    t_cons.start()
    t_prod.start()
    t_prod.join()
    t_cons.join()
    print()


# ==================== 5. 线程本地数据：threading.local() ====================


def demo_thread_local() -> None:
    """
    threading.local() 创建的对象，每个线程拥有独立的属性副本。
    典型场景：数据库连接、request context 等线程隔离的资源。
    """
    print("=== 5. ThreadLocal 线程本地数据 ===")
    local_data: threading.local = threading.local()

    def process(thread_id: int) -> None:
        # 每个线程设置自己的 user，互不干扰
        local_data.user = f"user_{thread_id}"
        time.sleep(0.1)
        print(f"  [{threading.current_thread().name}] local_data.user = {local_data.user}")

    threads: list[threading.Thread] = [
        threading.Thread(target=process, args=(i,), name=f"T-{i}") for i in range(4)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print()


# ==================== 6. Condition 条件变量 ====================


def demo_condition() -> None:
    """
    Condition 是 Lock + 等待/通知机制的组合，适合生产者-消费者模式。
    - condition.wait()       → 释放锁并阻塞，直到被 notify
    - condition.notify()     → 唤醒一个等待的线程
    - condition.notify_all() → 唤醒所有等待的线程
    """
    print("=== 6. Condition 条件变量（生产者-消费者）===")
    buffer: list[int] = []
    max_size: int = 5
    condition: threading.Condition = threading.Condition()

    def producer(count: int) -> None:
        for i in range(count):
            with condition:
                while len(buffer) >= max_size:
                    print("  [producer] 缓冲区满，等待消费者消费...")
                    condition.wait()
                buffer.append(i)
                print(f"  [producer] 生产 → {i}，当前缓冲区: {buffer}")
                condition.notify()  # 通知消费者
            time.sleep(0.1)

    def consumer(count: int) -> None:
        consumed: list[int] = []
        for _ in range(count):
            with condition:
                while not buffer:
                    print("  [consumer] 缓冲区空，等待生产者生产...")
                    condition.wait()
                item: int = buffer.pop(0)
                consumed.append(item)
                print(f"  [consumer] 消费 ← {item}，当前缓冲区: {buffer}")
                condition.notify()  # 通知生产者
            time.sleep(0.15)
        print(f"  [consumer] 共消费: {consumed}")

    total: int = 8
    t_prod: threading.Thread = threading.Thread(target=producer, args=(total,))
    t_cons: threading.Thread = threading.Thread(target=consumer, args=(total,))
    t_cons.start()
    t_prod.start()
    t_prod.join()
    t_cons.join()
    print()


# ==================== 主流程 ====================

if __name__ == "__main__":
    demo_target_thread()
    demo_subclass_thread()
    demo_daemon_thread()
    demo_lock()
    demo_rlock()
    demo_event()
    demo_thread_local()
    demo_condition()
