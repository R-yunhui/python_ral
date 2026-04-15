"""
Pottery demo + Java Redisson 对比

Pottery 是 Python 中最接近 Redisson 的库，提供 Redis-backed 的原生数据结构。
本文件演示 pottery 的核心用法，并在注释中对应 Java Redisson 的等价写法。

注意事项：
1. pottery 的 Redlock 是真正的 Redlock 算法（多 master 共识），
   释放时也要验证 quorum，可能抛 ReleaseUnlockedLock。
   实际单 Redis 实例场景，捕获该异常即可。

2. RedisCounter["key"] += 1 不是原子操作（读→加→写三步），
   高并发下会丢失更新。原子计数请用 redis_client.incr()。

3. pottery 不提供信号量、分布式队列等高级原语。
"""

import time
import threading
import redis
from pottery import (
    Redlock,          # 分布式锁
    RedisDict,        # 分布式字典
    RedisList,        # 分布式列表
    RedisCounter,     # 分布式计数器
    RedisSet,         # 分布式集合
    BloomFilter,      # 布隆过滤器
)
from pottery.exceptions import ReleaseUnlockedLock

# pottery 不提供信号量，用咱们自己写的 LIST 方案
from redis_semaphore_all import ListSemaphore


# ==================== 创建 Redis 客户端 ====================

redis_client = redis.Redis(
    host="192.168.2.137",
    port=6379,
    db=3,
    decode_responses=True,
)


# ==================== 1. 分布式锁 ====================


def demo_redlock():
    """
    分布式锁：Python Pottery vs Java Redisson

    ┌─────────────────────────────────┬─────────────────────────────────────┐
    │ Python (Pottery)                │ Java (Redisson)                     │
    ├─────────────────────────────────┼─────────────────────────────────────┤
    │ lock = Redlock(                 │ RLock lock = redisson.getLock(      │
    │     masters={redis_client},      │     "my-lock");                     │
    │     key="my-lock",              │                                     │
    │     auto_release_time=30_000    │                                     │
    │ )                               │                                     │
    │                                 │                                     │
    │ lock.acquire()                  │ lock.lock();                        │
    │ try: ...                        │ try { ... }                         │
    │ finally: lock.release()         │ finally { lock.unlock(); }          │
    └─────────────────────────────────┴─────────────────────────────────────┘

    注意：pottery 的 Redlock 释放时也要验证 quorum，
    可能抛 ReleaseUnlockedLock（锁已自动过期）。
    """
    print("\n=== 1. 分布式锁 (Redlock) ===")

    redis_client.delete("pottery:demo:lock")

    lock = Redlock(
        masters={redis_client},
        key="pottery:demo:lock",
        auto_release_time=30_000,  # 30 秒自动释放（ms）
    )

    # --- 用法一：手动 acquire/release ---
    print("  [用法一] 手动 acquire/release")
    print("  [lock] 尝试获取锁...")
    if lock.acquire():
        try:
            print("  [lock] 获取成功，执行任务...")
            time.sleep(0.5)
            print("  [lock] 任务完成")
        finally:
            try:
                lock.release()
                print("  [lock] 锁已释放")
            except ReleaseUnlockedLock:
                print("  [lock] 锁已过期自动释放（ReleaseUnlockedLock），跳过")

    # --- 用法二：context manager ---
    print("\n  [用法二] context manager（with 语句）")
    print("  [lock] 尝试获取锁...")
    try:
        with lock:
            print("  [lock] 获取成功，执行任务...")
            time.sleep(0.5)
            print("  [lock] 任务完成")
    except ReleaseUnlockedLock:
        print("  [lock] 锁已过期自动释放，跳过")

    print("\n  分布式锁测试完成\n")


# ==================== 2. 信号量 ====================


def demo_semaphore():
    """
    信号量：Python 自实现 vs Java Redisson

    pottery 不提供信号量！需要自己写（见 redis_semaphore_all.py）

    ┌─────────────────────────────────┬─────────────────────────────────────┐
    │ Python (自实现 LIST 方案)        │ Java (Redisson)                     │
    ├─────────────────────────────────┼─────────────────────────────────────┤
    │ sem = ListSemaphore(            │ RSemaphore sem = redisson.          │
    │     redis_client,               │     getSemaphore("my-sem");         │
    │     name="my-sem",              │ sem.setPermits(5);                  │
    │     permits=5                   │                                     │
    │ )                               │                                     │
    │                                 │                                     │
    │ with sem(timeout=3):            │ sem.acquire();                      │
    │     ...                         │ try { ... }                         │
    │                                 │ finally { sem.release(); }          │
    └─────────────────────────────────┴─────────────────────────────────────┘
    """
    print("\n=== 2. 信号量 (自实现 LIST 方案，pottery 不提供) ===")

    redis_client.delete("sem:list:demo:sem")

    sem = ListSemaphore(redis_client, "demo:sem", permits=2)

    def worker(name: str):
        print(f"  [{name}] 尝试获取信号量...")
        try:
            with sem(timeout=3):
                print(f"  [{name}] 获取成功，执行任务（1.5s）...")
                time.sleep(1.5)
                print(f"  [{name}] 任务完成")
        except TimeoutError:
            print(f"  [{name}] 超时，未获取到信号量")

    threads = [threading.Thread(target=worker, args=(f"S{i}",)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print("信号量测试完成\n")


# ==================== 3. 分布式数据结构 ====================


def demo_distributed_collections():
    """
    分布式数据结构对比

    ┌───────────────────────────┬─────────────────────────────────────────┐
    │ Python (Pottery)          │ Java (Redisson)                         │
    ├───────────────────────────┼─────────────────────────────────────────┤
    │ d = RedisDict(            │ RMap<String, Object> map =              │
    │     redis=client,          │     redisson.getMap("my-map");          │
    │     key="my-dict"          │ map.put("key", "value");                │
    │ )                         │                                         │
    │ d["key"] = "value"        │                                         │
    ├───────────────────────────┼─────────────────────────────────────────┤
    │ lst = RedisList(          │ RList<String> list =                    │
    │     redis=client,          │     redisson.getList("my-list");        │
    │     key="my-list"          │ list.add("item");                       │
    │ )                         │                                         │
    │ lst.append("item")        │                                         │
    ├───────────────────────────┼─────────────────────────────────────────┤
    │ s = RedisSet(             │ RSet<String> set =                      │
    │     redis=client,          │     redisson.getSet("my-set");          │
    │     key="my-set"           │ set.add("a");                           │
    │ )                         │                                         │
    │ s.add("a")                │                                         │
    ├───────────────────────────┼─────────────────────────────────────────┤
    │ bf = BloomFilter(         │ RBloomFilter<String> bf =               │
    │     redis=client,          │     redisson.getBloomFilter("my-bf");   │
    │     key="my-bf",           │ bf.tryInit(1000000, 0.01);              │
    │     num_elements=1000,     │ bf.add("data");                         │
    │     false_positives=0.01   │ bf.contains("data"); // true            │
    │ )                         │                                         │
    │ bf.add("data")            │                                         │
    │ "data" in bf  # True      │                                         │
    └───────────────────────────┴─────────────────────────────────────────┘
    """
    print("=== 3. 分布式数据结构 ===")

    # --- RedisDict ---
    redis_client.delete("pottery:demo:dict")
    d = RedisDict(redis=redis_client, key="pottery:demo:dict")
    d["name"] = "pottery"
    d["version"] = "1.0"
    print(f"  RedisDict: name={d['name']}, version={d['version']}, size={len(d)}")

    # --- RedisList ---
    redis_client.delete("pottery:demo:list")
    lst = RedisList(redis=redis_client, key="pottery:demo:list")
    for i in range(3):
        lst.append(f"item-{i}")
    print(f"  RedisList: {list(lst)} (length={len(lst)})")

    # --- RedisSet ---
    redis_client.delete("pottery:demo:set")
    s = RedisSet(redis=redis_client, key="pottery:demo:set")
    s.add("apple")
    s.add("banana")
    s.add("apple")  # 重复添加，不会增加
    print(f"  RedisSet: {set(s)} (size={len(s)})")

    # --- BloomFilter ---
    redis_client.delete("pottery:demo:bloom")
    bf = BloomFilter(
        redis=redis_client,
        key="pottery:demo:bloom",
        num_elements=100,
        false_positives=0.01,
    )
    for i in range(10):
        bf.add(f"user-{i}")
    print(f"  BloomFilter: 'user-5' in bf = {'user-5' in bf}")
    print(f"  BloomFilter: 'user-99' in bf = {'user-99' in bf}")

    print("分布式数据结构测试完成\n")


# ==================== 4. 原子计数器（对比） ====================


def demo_atomic_counter():
    """
    原子计数器：Python 的正确做法 vs Java Redisson

    pottery 的 RedisCounter["key"] += 1 不是原子的（读→加→写三步），
    高并发下会丢失更新。正确的做法是直接用 redis_client.incr()。

    ┌───────────────────────────┬─────────────────────────────────────────┐
    │ Python (redis-py 原生)     │ Java (Redisson)                         │
    ├───────────────────────────┼─────────────────────────────────────────┤
    │ redis_client.incr("count")│ RAtomicLong counter =                   │
    │ # 原子操作，底层 INCR      │     redisson.getAtomicLong("count");    │
    │                           │ counter.incrementAndGet();              │
    │                           │ // 原子 Lua 脚本                        │
    └───────────────────────────┴─────────────────────────────────────────┘
    """
    print("=== 4. 原子计数器对比 ===")

    # --- 错误做法：RedisCounter += （有竞态） ---
    redis_client.delete("pottery:demo:counter_bad")
    counter = RedisCounter(redis=redis_client, key="pottery:demo:counter_bad")

    def increment_bad(n: int):
        for _ in range(n):
            counter["total"] += 1  # 读→加→写，不是原子的

    num_threads = 10
    per_thread = 100

    threads = [threading.Thread(target=increment_bad, args=(per_thread,)) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"  RedisCounter += 方式:")
    print(f"    期望值: {num_threads * per_thread}")
    print(f"    实际值: {counter['total']}（会有丢失）")

    # --- 正确做法：redis_client.incr()（原子） ---
    redis_client.delete("pottery:demo:counter_good")

    def increment_good(n: int):
        for _ in range(n):
            redis_client.incr("pottery:demo:counter_good:total")  # 原子 INCR

    threads = [threading.Thread(target=increment_good, args=(per_thread,)) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    actual = int(redis_client.get("pottery:demo:counter_good:total"))
    print(f"  redis_client.incr() 方式:")
    print(f"    期望值: {num_threads * per_thread}")
    print(f"    实际值: {actual}（准确）")

    print("原子计数器对比完成\n")


# ==================== 5. 分布式队列 ====================


def demo_queue():
    """
    分布式队列：Python Pottery vs Java Redisson

    ┌───────────────────────────┬─────────────────────────────────────────┐
    │ Python (Pottery)          │ Java (Redisson)                         │
    ├───────────────────────────┼─────────────────────────────────────────┤
    │ q = RedisSimpleQueue(     │ RQueue<String> queue =                  │
    │     redis=client,          │     redisson.getQueue("my-queue");      │
    │     key="my-queue"         │ queue.add("msg");                       │
    │ )                         │ queue.poll();                           │
    │ q.put("msg")              │                                         │
    │ msg = q.get()             │                                         │
    └───────────────────────────┴─────────────────────────────────────────┘
    """
    from pottery import RedisSimpleQueue

    print("=== 5. 分布式队列 (RedisSimpleQueue) ===")

    redis_client.delete("pottery:demo:queue")
    q = RedisSimpleQueue(redis=redis_client, key="pottery:demo:queue")

    # 生产者
    for i in range(5):
        q.put(f"msg-{i}")
        print(f"  生产: msg-{i}")

    print(f"  队列大小: {q.qsize()}")

    # 消费者
    for _ in range(5):
        msg = q.get()
        print(f"  消费: {msg}")

    print("分布式队列测试完成\n")


# ==================== 主入口 ====================


if __name__ == "__main__":
    try:
        redis_client.ping()
        print("[OK] Redis 连接成功")
    except redis.ConnectionError:
        print("[FAIL] Redis 连接失败")
        exit(1)

    demo_redlock()
    demo_semaphore()
    demo_distributed_collections()
    demo_atomic_counter()
    demo_queue()

    print("=== 全部测试完成 ===")
