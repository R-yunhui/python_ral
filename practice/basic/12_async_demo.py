import asyncio
import time


async def task_with_result(name, duration, fail=False) -> str:
    """一个模拟异步任务，支持模拟成功、失败和耗时。"""
    print(f"[{name}] 任务开始 (预计耗时 {duration}秒)...")
    await asyncio.sleep(duration)
    if fail:
        print(f"[{name}] ❌ 任务抛出异常！")
        raise ValueError(f"任务 {name} 失败了")
    print(f"[{name}] ✅ 任务完成。")
    return f"{name} 的结果"


async def main():
    # --- 场景 1: asyncio.gather ---
    # 适用场景：你需要并发运行一组任务，并且需要等待它们全部结束提取结果。
    print("\n=== 场景 1: asyncio.gather (并行聚合) ===")
    try:
        results = await asyncio.gather(
            task_with_result("A", 1),
            task_with_result("B", 2),
            # task_with_result("C", 1, fail=True), # 取消注释可以查看报错行为
        )
        print(f"所有结果: {results}")
    except Exception as e:
        print(f"Gather 捕获到异常: {e}")

    # --- 场景 2: asyncio.create_task ---
    # 适用场景：类似于 Java 的 CompletableFuture，你想立即触发任务，但在之后某个时刻才等待它。
    print("\n=== 场景 2: asyncio.create_task (立即触发，异步等待) ===")
    t1 = asyncio.create_task(task_with_result("D", 2))
    t2 = asyncio.create_task(task_with_result("E", 1))

    # 你可以在任务运行期间做别的事
    print("... 主程序正在处理其他逻辑 ...")
    await asyncio.sleep(0.5)

    # 也可以手动添加类似 'whenComplete' 的回调
    t1.add_done_callback(lambda fut: print(f"任务 D 结束的回调：执行完毕了！"))

    res_e = await t2  # 先等耗时短的
    res_d = await t1  # 再等耗时长的
    print(f"单独获取结果: {res_d}, {res_e}")

    # --- 场景 3: asyncio.wait (更精细的控制) ---
    # 适用场景：例如“抢单”系统，只要有一个任务先完成就返回，或者想知道哪些成功了哪些还在跑。
    print("\n=== 场景 3: asyncio.wait (FIRST_COMPLETED) ===")
    tasks = [
        asyncio.create_task(task_with_result("F", 3)),
        asyncio.create_task(task_with_result("G", 1)),
    ]
    # return_when 支持 ALL_COMPLETED, FIRST_COMPLETED, FIRST_EXCEPTION
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    print(f"已有 {len(done)} 个任务完成，还有 {len(pending)} 个任务在后台继续运行。")
    for t in done:
        print(f"完成的任务结果: {t.result()}")

    # 记得清理或等待剩下的任务，否则主程序退出会报错
    await asyncio.gather(*pending)

    # --- 场景 4: asyncio.as_completed ---
    # 适用场景：谁先跑完就先处理谁，类似流式处理。
    print("\n=== 场景 4: asyncio.as_completed (谁快谁先出) ===")
    for fut in asyncio.as_completed(
        [task_with_result("H", 2), task_with_result("I", 1)]
    ):
        result = await fut
        print(f"流式获取到结果: {result}")

    # --- 场景 5: 现代 Python 推荐方式 (TaskGroup) ---
    # 适用场景：Python 3.11+ 推荐方式，更安全，如果一个出错会自动取消其他的。
    print("\n=== 场景 5: asyncio.TaskGroup (Python 3.11+) ===")
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(task_with_result("J", 1))
            tg.create_task(task_with_result("K", 0.5))
    except ExceptionGroup as eg:
        print(f"捕获到任务组异常: {eg}")
    print("任务组所有成员执行结束。")


if __name__ == "__main__":
    start_time = time.perf_counter()
    asyncio.run(main())
    end_time = time.perf_counter()
    print(f"\n--- 所有演示结束，总运行耗时: {end_time - start_time:.2f} 秒 ---")
