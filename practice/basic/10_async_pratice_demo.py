import asyncio
from pdb import run


def say_number_with_event():
    # 多线程无限顺序打印 1 2 3（Event实现）
    import threading
    import time

    def print_number(num, event, next_event):
        while True:
            event.wait()
            print(num)
            event.clear()
            next_event.set()
            time.sleep(0.1)  # 防止输出过快

    # 创建3个事件，确保顺序：1->2->3
    e1 = threading.Event()
    e2 = threading.Event()
    e3 = threading.Event()
    e1.set()  # 让数字1线程最先触发

    # 创建3个线程
    t1 = threading.Thread(target=print_number, args=(1, e1, e2))
    t2 = threading.Thread(target=print_number, args=(2, e2, e3))
    t3 = threading.Thread(target=print_number, args=(3, e3, e1))

    t1.daemon = True
    t2.daemon = True
    t3.daemon = True

    t1.start()
    t2.start()
    t3.start()

    # 让主线程不退出
    while True:
        time.sleep(1)


def say_number_with_condition():
    # Condition+共享变量实现顺序打印
    import threading
    import time

    cond = threading.Condition()
    curr = {"num": 1}

    def print_number(num):
        while True:
            with cond:
                while curr["num"] != num:
                    cond.wait()
                print(num)
                curr["num"] = 1 if num == 3 else num + 1
                cond.notify_all()
            time.sleep(0.1)

    threads = []
    for i in range(1, 4):
        t = threading.Thread(target=print_number, args=(i,))
        t.daemon = True
        t.start()
        threads.append(t)
    while True:
        time.sleep(1)


def say_number_with_lock():
    # Lock+自旋实现顺序打印
    import threading
    import time

    lock1 = threading.Lock()
    lock2 = threading.Lock()
    lock3 = threading.Lock()

    lock2.acquire()
    lock3.acquire()

    def print_number(num, my_lock, next_lock):
        while True:
            my_lock.acquire()
            print(num)
            next_lock.release()
            time.sleep(0.1)

    threads = [
        threading.Thread(target=print_number, args=(1, lock1, lock2)),
        threading.Thread(target=print_number, args=(2, lock2, lock3)),
        threading.Thread(target=print_number, args=(3, lock3, lock1)),
    ]
    for t in threads:
        t.daemon = True
        t.start()

    lock1.release()  # 启动第一个
    while True:
        time.sleep(1)


def say_number_with_queue():
    # Queue实现顺序打印
    import threading
    import time
    from queue import Queue

    q = Queue(maxsize=1)
    q.put(1)

    def print_number(num):
        while True:
            val = q.get()
            if val == num:
                print(num)
                q.put(1 if num == 3 else num + 1)
            else:
                q.put(val)  # 放回去
            time.sleep(0.1)

    for i in range(1, 4):
        t = threading.Thread(target=print_number, args=(i,))
        t.daemon = True
        t.start()
    while True:
        time.sleep(1)


def say_number_with_asyncio():
    # asyncio协程顺序打印
    import asyncio

    async def print_number(num, me, next_me):
        while True:
            await me.wait()
            print(num)
            me.clear()
            next_me.set()
            await asyncio.sleep(0.1)

    async def main():
        e1 = asyncio.Event()
        e2 = asyncio.Event()
        e3 = asyncio.Event()
        e1.set()
        task1 = asyncio.create_task(print_number(1, e1, e2))
        task2 = asyncio.create_task(print_number(2, e2, e3))
        task3 = asyncio.create_task(print_number(3, e3, e1))
        await asyncio.gather(task1, task2, task3)

    asyncio.run(main())


async def main():
    asyncio.run(say_number_with_event())


if __name__ == "__main__":
    asyncio.run(main())
