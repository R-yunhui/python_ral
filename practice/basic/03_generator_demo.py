"""
Python 生成器（Generator）的基本用法

生成器是一种惰性迭代器：用 yield 产出值，按需计算，节省内存。
"""

import os
from typing import Generator
import uuid


# ========== 1. 用 yield 定义生成器函数 ==========
def count_up_to(n: int) -> Generator[int, None, None]:
    """生成 0 到 n-1，每次 yield 一个值，下次从 yield 之后继续执行。"""
    i = 0
    while i < n:
        yield i
        i += 1


# ========== 2. 使用方式 ==========
def demo_basic() -> None:
    print("--- 用 next() 逐个取 ---")
    gen = count_up_to(3)
    print(next(gen))  # 0
    print(next(gen))  # 1
    print(next(gen))  # 2
    # print(next(gen))  # 再取会抛出 StopIteration

    print("\n--- 用 for 循环（推荐）---")
    for x in count_up_to(4):
        print(x, end=" ")
    print()


# ========== 3. 生成器表达式（类似列表推导，但惰性）==========
def demo_expression() -> None:
    print("\n--- 生成器表达式 ---")
    # 列表推导：一次性在内存里建好列表
    squares_list = [x * x for x in range(5)]
    # 生成器表达式：迭代时才计算
    squares_gen = (x * x for x in range(5))
    print("list:", squares_list)
    print("gen 转 list:", list(squares_gen))


# ========== 4. 惰性 / 省内存示例 ==========
def demo_lazy() -> None:
    print("\n--- 惰性：不会一次性算完 ---")

    def infinite_seq() -> Generator[int, None, None]:
        n = 0
        while True:
            yield n
            n += 1

    gen = infinite_seq()
    # 只取前 5 个，不会真的算到无穷
    first_five = [next(gen) for _ in range(5)]
    print("infinite 前 5 个:", first_five)


# ========== 5. 读取大文件/流式处理 ==========
def demo_read_large() -> None:
    print("\n--- 按行读取（生成器逐行，不占满内存）---")

    def lines_of_file(path: str) -> Generator[str, None, None]:
        with open(path, encoding="utf-8") as f:
            for line in f:
                yield line.rstrip("\n")

    # 示例：只处理前 3 行（文件很大也没关系）
    this_file = os.path.abspath(__file__)
    for i, line in enumerate(lines_of_file(this_file)):
        if i >= 3:
            break
        print(f"  {i}: {line[:60]}...")


def echo_roundtrip() -> Generator[str, int, str]:
    """
    产出 str，接收 int（通过 .send()），最后 return 一个 str。
    """
    first_received: int | None = None
    try:
        while True:
            # 第一次：next(gen) 时 sent 为 None；之后 .send(x) 时 sent 为传入的 int
            sent: int | None = yield "ready"  # 产出 "ready"，等待 send 进来的值
            if sent is not None:
                first_received = sent
                received = yield f"echo:{sent}"  # 产出 echo 字符串，再次等待
                if received is not None:
                    first_received = received
    except GeneratorExit:
        pass
    return f"final: got {first_received}"  # 生成器结束时通过 StopIteration.value 暴露


def generate_uuid() -> Generator[str, None, str]:
    count = 10
    while count > 0:
        yield str(uuid.uuid4())
        count -= 1
    return "done"


def gen_count_down() -> Generator[int, None, str]:
    count = 3
    while count > 0:
        yield count
        count -= 1
    return "done"


if __name__ == "__main__":
    
    gen = gen_count_down()
    for i in gen:
        print(i)
    print("倒计时结束！")
    
    # gen = generate_uuid()
    # for i in gen:
    #     print(i)
    
    # gen = echo_roundtrip()
    # # 必须先用 next() 把生成器推到第一个 yield
    # print(next(gen))  # 输出: ready
    # # .send(42) 把 42 传进去，并得到下一个 yield 的值
    # print(gen.send(42))  # 输出: echo:42
    # # 再 send 一次
    # print(gen.send(100))  # 输出: echo:100
    # # 关闭生成器，此时会执行到 return，返回值在 StopIteration.value 里
    # try:
    #     gen.close()
    # except StopIteration as e:
    #     print(e.value)  # 输出: final: got 100
    
    
    # demo_basic()
    # demo_expression()
    # demo_lazy()
    # demo_read_large()
