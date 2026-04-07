"""
电商订单处理系统 - 异步/并发编程完整示例

场景：一个电商平台的订单处理流水线
- 异步 HTTP 请求获取订单数据
- 异步数据库操作
- 并发控制 (信号量限流)
- 生产者 - 消费者模式
- CPU 密集型任务 offload 到线程池/进程池
- 任务取消和优雅关闭
"""

import asyncio
import time
import random
import hashlib
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


# ==================== 数据模型 ====================

class OrderStatus(Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Order:
    order_id: str
    user_id: int
    amount: float
    items: List[Dict]
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)


# ==================== 模拟异步服务 ====================

class AsyncHTTPClient:
    """模拟异步 HTTP 客户端 - 调用外部 API"""

    async def fetch_order_list(self, page: int) -> List[Dict]:
        """从订单服务获取订单列表"""
        await asyncio.sleep(random.uniform(0.1, 0.3))  # 模拟网络延迟

        # 模拟偶尔的网络错误
        if random.random() < 0.1:
            raise Exception(f"Network timeout on page {page}")

        return [
            {
                "order_id": hashlib.md5(f"{page}-{i}".encode()).hexdigest()[:10],
                "user_id": random.randint(1000, 9999),
                "amount": random.uniform(50, 2000),
                "items": [{"product_id": i, "qty": random.randint(1, 5)} for i in range(random.randint(1, 4))]
            }
            for i in range(5)
        ]


class AsyncDatabase:
    """模拟异步数据库连接"""

    def __init__(self):
        self.connection_pool_size = 10
        self._connected = False

    async def connect(self):
        """建立数据库连接"""
        await asyncio.sleep(0.1)
        self._connected = True
        print("[DB] Connected to database")

    async def close(self):
        """关闭数据库连接"""
        await asyncio.sleep(0.05)
        self._connected = False
        print("[DB] Connection closed")

    async def insert_order(self, order: Order) -> bool:
        """插入订单"""
        if not self._connected:
            raise RuntimeError("Database not connected")
        await asyncio.sleep(random.uniform(0.05, 0.15))
        print(f"[DB] Inserted order: {order.order_id}")
        return True

    async def update_status(self, order_id: str, status: OrderStatus) -> bool:
        """更新订单状态"""
        await asyncio.sleep(random.uniform(0.03, 0.1))
        print(f"[DB] Order {order_id} -> {status.value}")
        return True

    async def fetch_user_info(self, user_id: int) -> Dict:
        """获取用户信息"""
        await asyncio.sleep(random.uniform(0.05, 0.1))
        return {
            "user_id": user_id,
            "name": f"User_{user_id}",
            "vip_level": random.randint(1, 5),
            "credit_score": random.randint(300, 800)
        }


class PaymentGateway:
    """模拟异步支付网关"""

    async def process_payment(self, order: Order) -> bool:
        """处理支付"""
        await asyncio.sleep(random.uniform(0.2, 0.5))

        # 90% 成功率
        success = random.random() < 0.9
        if success:
            print(f"[Payment] Order {order.order_id} paid ${order.amount:.2f}")
        else:
            print(f"[Payment] Order {order.order_id} payment FAILED")
        return success


# ==================== CPU 密集型任务 (需要 offload) ====================

def calculate_order_hash(data: bytes) -> str:
    """CPU 密集型：计算哈希 (同步函数，需要在线程池运行)"""
    # 模拟大量计算
    result = data
    for _ in range(100000):
        result = hashlib.sha256(result).digest()
    return hashlib.md5(result).hexdigest()


def generate_report_data(orders: List[Order]) -> Dict:
    """CPU 密集型：生成报表数据"""
    total = sum(o.amount for o in orders)
    avg = total / len(orders) if orders else 0

    # 模拟复杂计算
    time.sleep(0.1)

    return {
        "total_orders": len(orders),
        "total_amount": round(total, 2),
        "avg_order_value": round(avg, 2),
        "generated_at": datetime.now().isoformat()
    }


# ==================== 订单处理系统核心 ====================

class OrderProcessingSystem:
    """
    订单处理系统

    功能：
    1. 从 API 拉取订单 (异步 HTTP)
    2. 验证用户信息 (并发数据库查询)
    3. 处理支付 (异步 + 限流)
    4. 生成处理凭证 (CPU 密集型 offload)
    5. 持久化订单 (异步数据库)
    """

    def __init__(self, max_concurrent_payments: int = 5):
        self.http_client = AsyncHTTPClient()
        self.db = AsyncDatabase()
        self.payment_gateway = PaymentGateway()

        # 信号量：限制并发支付数量
        self._payment_semaphore = asyncio.Semaphore(max_concurrent_payments)

        # 队列：订单处理流水线
        self._order_queue: asyncio.Queue = asyncio.Queue(maxsize=100)

        # 状态
        self._running = False
        self._processed_count = 0
        self._lock = asyncio.Lock()

    async def start(self):
        """启动系统"""
        await self.db.connect()
        self._running = True
        print("[System] Order processing system started")

    async def stop(self):
        """优雅关闭系统"""
        self._running = False
        await self.db.close()
        print(f"[System] Shutdown complete. Processed: {self._processed_count}")

    async def fetch_orders_task(self):
        """生产者：持续从 API 拉取订单"""
        page = 0
        while self._running:
            try:
                page += 1
                orders_data = await self.http_client.fetch_order_list(page)

                for data in orders_data:
                    order = Order(**data)
                    await self._order_queue.put(order)
                    print(f"[Fetcher] Fetched order: {order.order_id}")

                # 每页之间短暂暂停
                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"[Fetcher] Error fetching page {page}: {e}")
                await asyncio.sleep(1)  # 错误后等待更久

    async def validate_user(self, order: Order) -> bool:
        """验证用户信息 (并发查询多个数据源)"""
        try:
            # 并发获取用户信息和信用分
            user_info = await self.db.fetch_user_info(order.user_id)

            # 验证逻辑
            if user_info["credit_score"] < 500:
                print(f"[Validate] Order {order.order_id} rejected: low credit")
                return False

            return True
        except Exception as e:
            print(f"[Validate] Order {order.order_id} validation error: {e}")
            return False

    async def process_payment_task(self, order: Order) -> bool:
        """消费者：处理订单支付 (带信号量限流)"""
        async with self._payment_semaphore:
            print(f"[Payment] Processing order: {order.order_id}")

            # 1. 验证用户
            if not await self.validate_user(order):
                return False

            # 2. 处理支付
            payment_success = await self.payment_gateway.process_payment(order)
            if not payment_success:
                return False

            # 3. 更新状态
            order.status = OrderStatus.PAID
            await self.db.update_status(order.order_id, OrderStatus.PAID)

            # 4. CPU 密集型任务 offload 到线程池
            loop = asyncio.get_running_loop()
            order_hash = await loop.run_in_executor(
                None,
                calculate_order_hash,
                f"{order.order_id}-{order.amount}".encode()
            )
            print(f"[Payment] Order {order.order_id} hash: {order_hash[:16]}")

            # 5. 持久化
            await self.db.insert_order(order)

            async with self._lock:
                self._processed_count += 1

            return True

    async def worker(self, worker_id: int):
        """工作协程：从队列取订单并处理"""
        print(f"[Worker-{worker_id}] Started")

        while self._running:
            try:
                # 从队列获取订单 (带超时)
                try:
                    order = await asyncio.wait_for(
                        self._order_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # 处理订单
                success = await self.process_payment_task(order)

                if success:
                    print(f"[Worker-{worker_id}] Completed: {order.order_id}")
                else:
                    print(f"[Worker-{worker_id}] Failed: {order.order_id}")

                self._order_queue.task_done()

            except asyncio.CancelledError:
                print(f"[Worker-{worker_id}] Cancelled")
                break
            except Exception as e:
                print(f"[Worker-{worker_id}] Error: {e}")

    async def report_generator(self, orders: List[Order]) -> Dict:
        """生成报表 (CPU 密集型 offload 到进程池)"""
        loop = asyncio.get_running_loop()

        # 使用进程池处理 CPU 密集型任务
        with ProcessPoolExecutor() as executor:
            report = await loop.run_in_executor(
                executor,
                generate_report_data,
                orders
            )
        return report

    async def run_demo(self, duration: int = 10):
        """运行演示"""
        await self.start()

        try:
            # 创建任务
            fetcher = asyncio.create_task(self.fetch_orders_task())
            workers = [
                asyncio.create_task(self.worker(i))
                for i in range(3)
            ]

            # 运行指定时间
            await asyncio.sleep(duration)

            # 停止
            self._running = False
            fetcher.cancel()

            # 等待队列清空
            await self._order_queue.join()

            # 取消 workers
            for w in workers:
                w.cancel()

            await asyncio.gather(fetcher, *workers, return_exceptions=True)

        finally:
            await self.stop()


# ==================== 其他实用模式 ====================

async def demo_gather_with_timeout():
    """演示：并发执行 + 超时控制"""
    print("\n=== Demo: gather with timeout ===")

    async def task(name: str, delay: float):
        await asyncio.sleep(delay)
        return f"{name} completed"

    tasks = [
        task("A", 0.5),
        task("B", 1.0),
        task("C", 2.0),  # 这个会超时
    ]

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=1.5
        )
        print(f"Results: {results}")
    except asyncio.TimeoutError:
        print("Operation timed out")


async def demo_async_context_manager():
    """演示：异步上下文管理器"""
    print("\n=== Demo: Async Context Manager ===")

    class AsyncResource:
        async def __aenter__(self):
            print("Acquiring resource...")
            await asyncio.sleep(0.1)
            print("Resource acquired")
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            print("Releasing resource...")
            await asyncio.sleep(0.1)
            print("Resource released")

    async with AsyncResource() as resource:
        print("Using resource")
        await asyncio.sleep(0.2)


async def demo_async_iterator():
    """演示：异步迭代器"""
    print("\n=== Demo: Async Iterator ===")

    async def async_data_stream():
        """模拟异步数据流"""
        for i in range(5):
            await asyncio.sleep(0.2)
            yield f"Data-{i}"

    async for data in async_data_stream():
        print(f"Received: {data}")


async def demo_mixed_concurrency():
    """演示：混合并发模式 (asyncio + threading + multiprocessing)"""
    print("\n=== Demo: Mixed Concurrency ===")

    loop = asyncio.get_running_loop()

    # 1. I/O 密集型 - 用 asyncio
    async def io_task():
        await asyncio.sleep(0.3)
        return "I/O done"

    # 2. CPU 密集型 - 用线程池 (如果会释放 GIL)
    def cpu_thread():
        time.sleep(0.3)
        return "CPU thread done"

    # 3. CPU 密集型 - 用进程池 (纯 Python CPU)
    def cpu_process():
        time.sleep(0.3)
        return "CPU process done"

    results = await asyncio.gather(
        io_task(),
        loop.run_in_executor(None, cpu_thread),
        loop.run_in_executor(None, cpu_process),
    )
    print(f"Results: {results}")


# ==================== 主入口 ====================

async def main():
    print("=" * 60)
    print("电商订单处理系统 - 异步/并发编程演示")
    print("=" * 60)

    # 主演示：订单处理系统
    system = OrderProcessingSystem(max_concurrent_payments=3)
    await system.run_demo(duration=5)

    print("\n" + "=" * 60)
    print("额外模式演示")
    print("=" * 60)

    # 其他模式演示
    await demo_gather_with_timeout()
    await demo_async_context_manager()
    await demo_async_iterator()
    await demo_mixed_concurrency()


if __name__ == "__main__":
    asyncio.run(main())
