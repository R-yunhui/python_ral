"""
Redis 信号量（Semaphore）三种实现方案

信号量用于控制同时访问某资源的最大并发数，在分布式场景下需要 Redis 来保证原子性。

三种方案对比：
| 方案      | 核心命令        | 优点                  | 缺点                    | 适用场景         |
|-----------|-----------------|-----------------------|-------------------------|------------------|
| LIST 令牌 | BLPOP/LPUSH     | 原生阻塞、公平 FIFO   | 需预创建 token          | 推荐，最稳妥     |
| INCR 计数 | INCR/DECR       | 简单轻量              | 需轮询、可能饿死        | 低并发、临时用   |
| ZSET 排序 | ZADD/ZRANK      | 公平 + 可加 TTL 防死锁 | 实现稍复杂              | 高可靠要求场景   |
"""

import redis
import time
import uuid
import threading
from typing import Optional
from contextlib import contextmanager


# ==================== 方案一：LIST 令牌池（推荐） ====================


class ListSemaphore:
    """
    基于 Redis LIST 的信号量实现。

    核心思路：
    - 初始化时往 list 里 LPUSH N 个 token
    - acquire: BLPOP 弹出一个 token（无 token 时阻塞等待）
    - release: LPUSH 把 token 还回去

    优点：
    - BLPOP 原生阻塞，无需轮询，CPU 友好
    - FIFO 公平，先等先获得
    - 实现简单，最稳妥
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        name: str,
        permits: int,
        auto_init: bool = True,
    ):
        self.r = redis_client
        self.key = f"sem:list:{name}"
        self.permits = permits
        self._token_prefix = "token"

        if auto_init:
            self._init_tokens()

    def _init_tokens(self) -> None:
        """初始化令牌池（幂等：如果已有 token 则跳过）。"""
        # 检查是否已初始化
        if self.r.exists(self.key):
            current_len = self.r.llen(self.key)
            if current_len >= self.permits:
                return

        # 用 pipeline 批量插入，原子操作
        pipe = self.r.pipeline()
        # 先清空（防止残留）
        pipe.delete(self.key)
        # 插入 N 个 token
        for i in range(self.permits):
            pipe.lpush(self.key, f"{self._token_prefix}-{i}-{uuid.uuid4().hex[:8]}")
        pipe.execute()

    def acquire(self, timeout: float = 0) -> bool:
        """
        获取一个许可。

        :param timeout: 超时时间（秒），0 表示无限等待
        :return: 成功获取返回 True，超时返回 False
        """
        # BLPOP 是阻塞式原子弹出，timeout=0 表示一直等
        result = self.r.blpop(self.key, timeout=timeout if timeout > 0 else 0)
        if result is None:
            return False
        return True

    def release(self) -> None:
        """释放一个许可（把 token 还回池中）。"""
        self.r.lpush(self.key, f"{self._token_prefix}-{uuid.uuid4().hex[:8]}")

    @contextmanager
    def __call__(self, timeout: float = 0):
        """上下文管理器用法。"""
        if not self.acquire(timeout=timeout):
            raise TimeoutError(f"获取信号量超时（{timeout}s）")
        try:
            yield
        finally:
            self.release()

    def get_available_permits(self) -> int:
        """当前可用的许可数。"""
        return self.r.llen(self.key)

    def destroy(self) -> None:
        """销毁信号量。"""
        self.r.delete(self.key)


# ==================== 方案二：INCR 计数器 ====================


class IncrSemaphore:
    """
    基于 Redis INCR 的信号量实现。

    核心思路：
    - key 存储当前已使用的许可数
    - acquire: INCR 后判断是否 <= N，超过则 DECR 回滚并重试
    - release: DECR 减少计数

    优点：
    - 实现极简，一个 key 搞定
    - 无需预初始化

    缺点：
    - 高并发时需反复 INCR+DECR，浪费资源
    - 不公平，可能饿死
    - 需要轮询或配合 pub/sub
    """

    def __init__(self, redis_client: redis.Redis, name: str, permits: int):
        self.r = redis_client
        self.key = f"sem:incr:{name}"
        self.permits = permits

    def acquire(self, timeout: float = 0, retry_interval: float = 0.05) -> bool:
        """
        获取一个许可。

        :param timeout: 超时时间（秒），0 表示无限等待
        :param retry_interval: 重试间隔（秒）
        :return: 成功获取返回 True，超时返回 False
        """
        start_time = time.time()

        while True:
            # 原子 INCR
            current = self.r.incr(self.key)

            if current <= self.permits:
                # 在许可范围内，获取成功
                return True
            else:
                # 超出限制，回滚
                self.r.decr(self.key)

                # 检查超时
                if timeout > 0 and (time.time() - start_time) > timeout:
                    return False

                # 等待后重试
                time.sleep(retry_interval)

    def release(self) -> None:
        """释放一个许可。"""
        self.r.decr(self.key)

    @contextmanager
    def __call__(self, timeout: float = 0):
        """上下文管理器用法。"""
        if not self.acquire(timeout=timeout):
            raise TimeoutError(f"获取信号量超时（{timeout}s）")
        try:
            yield
        finally:
            self.release()

    def get_available_permits(self) -> int:
        """当前可用的许可数。"""
        current = self.r.get(self.key)
        if current is None:
            return self.permits
        return max(0, self.permits - int(current))

    def destroy(self) -> None:
        """销毁信号量。"""
        self.r.delete(self.key)


# ==================== 方案三：ZSET 排序集合（公平 + 防死锁） ====================


class ZsetSemaphore:
    """
    基于 Redis ZSET 的信号量实现。

    核心思路：
    - 每个请求者用唯一 ID（uuid）作为 member，时间戳作为 score 加入 ZSET
    - 计算自己的排名（ZRANK），排名 < N 则获取成功
    - 排名 >= N 则 ZREM 退出并重试
    - 可以给每个 member 设置过期时间，防止持有者崩溃导致死锁

    优点：
    - FIFO 公平（按时间戳排序）
    - 可加 TTL 防死锁
    - 可查询自己的排队位置

    缺点：
    - 实现最复杂
    - ZSET 操作比 LIST 稍慢
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        name: str,
        permits: int,
        ttl: Optional[int] = None,
    ):
        self.r = redis_client
        self.key = f"sem:zset:{name}"
        self.permits = permits
        self.ttl = ttl  # 过期时间（秒），None 表示永不过期
        self._member_id: Optional[str] = None  # 当前持有的 member ID

    def acquire(self, timeout: float = 0, retry_interval: float = 0.05) -> bool:
        """
        获取一个许可。

        :param timeout: 超时时间（秒），0 表示无限等待
        :param retry_interval: 重试间隔（秒）
        :return: 成功获取返回 True，超时返回 False
        """
        start_time = time.time()
        self._member_id = f"{uuid.uuid4().hex}"
        timestamp = time.time()

        while True:
            # 用当前时间戳作为 score，保证 FIFO
            self.r.zadd(self.key, {self._member_id: timestamp})

            # 获取自己的排名（从小到大）
            rank = self.r.zrank(self.key, self._member_id)
            if rank is None:
                # 可能已被其他线程移除，重试
                continue

            if rank < self.permits:
                # 排名在许可范围内，获取成功
                # 设置过期时间（防死锁）
                if self.ttl:
                    self.r.expire(self.key, self.ttl)
                return True
            else:
                # 超出许可范围，退出队列
                self.r.zrem(self.key, self._member_id)

                # 检查超时
                if timeout > 0 and (time.time() - start_time) > timeout:
                    self._member_id = None
                    return False

                # 等待后重试
                time.sleep(retry_interval)
                # 更新时间戳重新排队
                timestamp = time.time()
                self._member_id = f"{uuid.uuid4().hex}"

    def release(self) -> None:
        """释放一个许可。"""
        if self._member_id:
            self.r.zrem(self.key, self._member_id)
            self._member_id = None

    @contextmanager
    def __call__(self, timeout: float = 0):
        """上下文管理器用法。"""
        if not self.acquire(timeout=timeout):
            raise TimeoutError(f"获取信号量超时（{timeout}s）")
        try:
            yield
        finally:
            self.release()

    def get_available_permits(self) -> int:
        """当前可用的许可数。"""
        current = self.r.zcard(self.key)
        return max(0, self.permits - current)

    def get_queue_position(self) -> Optional[int]:
        """获取当前排队位置（如果在队列中）。"""
        if not self._member_id:
            return None
        rank = self.r.zrank(self.key, self._member_id)
        return rank + 1 if rank is not None else None

    def destroy(self) -> None:
        """销毁信号量。"""
        self.r.delete(self.key)


# ==================== 测试 Demo ====================


def create_redis_client() -> redis.Redis:
    """创建 Redis 客户端。"""
    return redis.Redis(
        host="192.168.2.137",
        port=6379,
        db=3,
        decode_responses=True,
    )


def test_list_semaphore():
    """测试 LIST 方案。"""
    print("\n" + "=" * 60)
    print("【测试方案一：LIST 令牌池】")
    print("=" * 60)

    r = create_redis_client()
    sem = ListSemaphore(r, "test_resource", permits=2)

    print(f"初始可用许可：{sem.get_available_permits()}")

    # 模拟 3 个并发任务，只有 2 个许可能同时执行
    def task(task_id: int):
        print(f"  [Task-{task_id}] 尝试获取许可...")
        with sem(timeout=3) as _:
            print(
                f"  [Task-{task_id}] 获取成功，剩余许可：{sem.get_available_permits()}"
            )
            time.sleep(1)
            print(f"  [Task-{task_id}] 执行完成，释放许可")

    threads = [threading.Thread(target=task, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"最终可用许可：{sem.get_available_permits()}")
    sem.destroy()
    print("LIST 方案测试完成 ✓")


def test_incr_semaphore():
    """测试 INCR 方案。"""
    print("\n" + "=" * 60)
    print("【测试方案二：INCR 计数器】")
    print("=" * 60)

    r = create_redis_client()
    sem = IncrSemaphore(r, "test_resource", permits=2)

    print(f"初始可用许可：{sem.get_available_permits()}")

    def task(task_id: int):
        print(f"  [Task-{task_id}] 尝试获取许可...")
        with sem(timeout=3) as _:
            print(
                f"  [Task-{task_id}] 获取成功，剩余许可：{sem.get_available_permits()}"
            )
            time.sleep(1)
            print(f"  [Task-{task_id}] 执行完成，释放许可")

    threads = [threading.Thread(target=task, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"最终可用许可：{sem.get_available_permits()}")
    sem.destroy()
    print("INCR 方案测试完成 ✓")


def test_zset_semaphore():
    """测试 ZSET 方案。"""
    print("\n" + "=" * 60)
    print("【测试方案三：ZSET 排序集合】")
    print("=" * 60)

    r = create_redis_client()
    sem = ZsetSemaphore(r, "test_resource", permits=2, ttl=30)

    print(f"初始可用许可：{sem.get_available_permits()}")

    def task(task_id: int):
        print(f"  [Task-{task_id}] 尝试获取许可...")
        with sem(timeout=3) as _:
            pos = sem.get_queue_position()
            print(
                f"  [Task-{task_id}] 获取成功 (排队位置：{pos}), 剩余许可：{sem.get_available_permits()}"
            )
            time.sleep(1)
            print(f"  [Task-{task_id}] 执行完成，释放许可")

    threads = [threading.Thread(target=task, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"最终可用许可：{sem.get_available_permits()}")
    sem.destroy()
    print("ZSET 方案测试完成 ✓")


def compare_performance():
    """简单性能对比。"""
    print("\n" + "=" * 60)
    print("【性能对比：三种方案获取/释放 100 次耗时】")
    print("=" * 60)

    r = create_redis_client()

    for SemClass, name in [
        (ListSemaphore, "LIST"),
        (IncrSemaphore, "INCR"),
        (ZsetSemaphore, "ZSET"),
    ]:
        if SemClass == ListSemaphore:
            sem = SemClass(r, f"perf_{name}", permits=10)
        elif SemClass == ZsetSemaphore:
            sem = SemClass(r, f"perf_{name}", permits=10)
        else:
            sem = SemClass(r, f"perf_{name}", permits=10)

        start = time.perf_counter()
        for _ in range(100):
            sem.acquire(timeout=1)
            sem.release()
        elapsed = (time.perf_counter() - start) * 1000  # ms

        print(f"  {name}: {elapsed:.2f} ms")
        sem.destroy()


if __name__ == "__main__":
    # 检查 Redis 连接
    try:
        r = create_redis_client()
        r.ping()
        print("✓ Redis 连接成功")
    except redis.ConnectionError:
        print("✗ Redis 连接失败，请确保 Redis 服务已启动（192.168.2.137:6379）")
        exit(1)

    # 运行测试
    test_list_semaphore()
    test_incr_semaphore()
    test_zset_semaphore()
    compare_performance()

    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)
