import redis
import time
import uuid
import threading


class RedisSemaphore:
    def __init__(self, client: redis.Redis, name: str, limit: int, timeout: int = 10):
        """
        初始化分布式信号量

        :param client: Redis 客户端实例
        :param name: 信号量的名称 (作为 Redis Key)
        :param limit: 允许的最大并发数
        :param timeout: 超时时间(秒)，超过此时间未释放的锁将被自动清理（防止持有者崩溃死锁）
        """
        self.client = client
        self.name = f"semaphore:{name}"
        self.limit = limit
        self.timeout = timeout

        # 注册 Lua 脚本，保证操作的原子性
        # KEYS[1] = 信号量的 ZSet Key
        # ARGV[1] = 允许的最大并发数 (limit)
        # ARGV[2] = 过期时间差 (timeout)
        # ARGV[3] = 唯一的标识符 (identifier)
        # ARGV[4] = 当前的时间戳 (now)
        self._acquire_script = self.client.register_script(
            """
            -- 1. 清理超时的死锁记录
            redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[4] - ARGV[2])
            
            -- 2. 尝试将自己加入到 ZSet 中
            redis.call('ZADD', KEYS[1], ARGV[4], ARGV[3])
            
            -- 3. 获取自己的排名（从0开始）
            local rank = redis.call('ZRANK', KEYS[1], ARGV[3])
            
            -- 4. 判断是否在名额内
            if rank < tonumber(ARGV[1]) then
                return 1 -- 成功获取
            else
                -- 名额满了，获取失败，把自己清理掉
                redis.call('ZREM', KEYS[1], ARGV[3])
                return 0 -- 获取失败
            end
        """
        )

        # 注册用于续期的 Lua 脚本 (Watchdog)
        self._renew_script = self.client.register_script(
            """
            -- 如果该标识符还存在（说明没被释放也没被清理）
            if redis.call('ZSCORE', KEYS[1], ARGV[1]) then
                -- 刷新时间戳为最新时间
                redis.call('ZADD', KEYS[1], ARGV[2], ARGV[1])
                return 1
            end
            return 0
        """
        )
        self._watchdogs = {}  # 记录正在运行的 watchdog 线程

    def acquire(self, identifier: str) -> bool:
        """
        尝试获取信号量
        返回 True 表示获取成功，False 表示获取失败
        """
        now = time.time()
        # 执行 Lua 脚本
        result = self._acquire_script(
            keys=[self.name], args=[self.limit, self.timeout, identifier, now]
        )
        if result == 1:
            # 获取成功的话，开启后台心跳线程自动续期
            self._start_watchdog(identifier)
            return True
        return False

    def release(self, identifier: str):
        """
        释放信号量
        """
        self._stop_watchdog(identifier)
        self.client.zrem(self.name, identifier)

    def _start_watchdog(self, identifier: str):
        """启动看门狗线程，定期刷新标识符的时间戳"""
        stop_event = threading.Event()
        self._watchdogs[identifier] = stop_event

        def _watchdog_task():
            # 续期周期(秒)，设置为超时时间的 1/3
            interval = max(1, self.timeout / 3)
            while not stop_event.is_set():
                # 睡眠指定周期，如果被提前唤醒(stop_event.wait返回 True)说明任务结束了
                if stop_event.wait(interval):
                    break
                # 执行续期，更新时间戳为最新
                current_time = time.time()
                self._renew_script(keys=[self.name], args=[identifier, current_time])

        t = threading.Thread(target=_watchdog_task, daemon=True)
        t.start()

    def _stop_watchdog(self, identifier: str):
        """停止看门狗线程"""
        if identifier in self._watchdogs:
            self._watchdogs[identifier].set()
            del self._watchdogs[identifier]


# ==============================
# 测试 Demo 代码
# ==============================
def worker(worker_id, r_client):
    # 初始化一个允许 3 个并发的信号量
    semaphore = RedisSemaphore(r_client, name="my_task_sema", limit=3, timeout=5)

    # 每个 worker 生成一个唯一的 ID（防止误删别人的记录）
    identifier = str(uuid.uuid4())

    print(f"[Worker {worker_id}] 尝试获取信号量...")
    if semaphore.acquire(identifier):
        try:
            print(f"[Worker {worker_id}] 🟢 获取成功！正在处理任务 (预计需要8秒)...")
            # 模拟业务耗时处理，我们故意让时间(8s)大于 timeout(5s)
            # 因为有了 watchdog 的存在，虽然超过了5秒，但依然不会被释放！
            for i in range(8):
                time.sleep(1)
                print(f"[Worker {worker_id}] 任务执行中... ({i+1}/8)")
        finally:
            # 处理完成后释放信号量
            semaphore.release(identifier)
            print(f"[Worker {worker_id}] 🔴 执行完毕，释放信号量。")
    else:
        print(f"[Worker {worker_id}] ❌ 获取失败，当前并发数已满。")


if __name__ == "__main__":
    # 请确保本地开启了 Redis 服务，或者替换为实际的 Redis 配置
    redis_client = redis.Redis(
        host="192.168.2.137", port=6379, db=3, decode_responses=True
    )

    # 清理掉之前的测试数据（仅为演示方便）
    redis_client.delete("semaphore:my_task_sema")

    # 启动 5 个线程模拟并发请求（但信号量限制最多只能 3 个同时执行）
    threads = []
    for i in range(5):
        t = threading.Thread(target=worker, args=(i, redis_client))
        threads.append(t)
        t.start()
        # 稍微错开一点启动时间
        time.sleep(0.1)

    for t in threads:
        t.join()

    print("所有测试完毕！")
