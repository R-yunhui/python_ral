"""
Python 装饰器用法学习

装饰器：在不改函数源码的前提下，给函数增加“前/后”逻辑（如日志、计时、鉴权等）。
本质是 func = decorator(func)，把原函数替换成包装后的函数。
"""

import asyncio
import functools
from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


# ==================== 一、同步函数装饰器 ====================


def simple_decorator(func: F) -> F:
    """最简形式：无参装饰器，包装同步函数。"""

    @functools.wraps(func)  # 重要：把原函数的 __name__、__doc__ 等拷到 wrapper，避免调试时丢失
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        print("  [装饰器] 调用前")
        result = func(*args, **kwargs)
        print("  [装饰器] 调用后")
        return result

    return wrapper  # type: ignore[return-value]


@simple_decorator
def add(a: int, b: int) -> int:
    """两数相加。"""
    return a + b


# ==================== 二、带参数的装饰器 ====================


def repeat(times: int):
    """带参数的装饰器：外层接收参数，内层才是接收 func 的装饰器。"""

    def deco(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for i in range(times):
                print(f"  [repeat] 第 {i + 1}/{times} 次")
                result = func(*args, **kwargs)
            return result

        return wrapper  # type: ignore[return-value]

    return deco


@repeat(times=2)
def greet(name: str) -> str:
    """打招呼。"""
    s = f"Hello, {name}!"
    print(f"    {s}")
    return s


# ==================== 三、异步函数装饰器 ====================


def async_decorator(func: F) -> F:
    """包装异步函数时，wrapper 必须是 async def，并在内部 await 原函数。"""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        print("  [async 装饰器] 调用前")
        result = await func(*args, **kwargs)  # 必须 await 异步函数
        print("  [async 装饰器] 调用后")
        return result

    return wrapper  # type: ignore[return-value]


@async_decorator
async def fetch_data(delay: float) -> str:
    """模拟异步请求。"""
    await asyncio.sleep(delay)
    return "data"


# ==================== 四、内置 / 标准库装饰器 ====================


# ---------- 4.1 @staticmethod：不需要 self，类命名空间下的普通函数 ----------
class MathUtils:
    @staticmethod
    def add(a: int, b: int) -> int:
        """不访问实例也不访问类，只是挂在类上便于归类。调用：MathUtils.add(1, 2)。"""
        return a + b


# ---------- 4.2 @classmethod：第一个参数是 cls，常用于工厂方法或操作类属性 ----------
class Person:
    def __init__(self, name: str, age: int) -> None:
        self.name = name
        self.age = age

    @classmethod
    def from_birth_year(cls, name: str, birth_year: int) -> "Person":
        """工厂方法：用出生年份构造。调用：Person.from_birth_year("Alice", 1990)。"""
        from datetime import datetime
        year = datetime.now().year
        return cls(name, age=year - birth_year)


# ---------- 4.3 @property：把方法当“属性”读；可配合 .setter / .deleter ----------
class Circle:
    def __init__(self, radius: float) -> None:
        self._radius = radius

    @property
    def radius(self) -> float:
        """读属性：c.radius"""
        return self._radius

    @radius.setter
    def radius(self, value: float) -> None:
        """写属性：c.radius = 2.0"""
        if value < 0:
            raise ValueError("半径不能为负")
        self._radius = value

    @property
    def area(self) -> float:
        """只读属性：由当前 radius 计算。"""
        return 3.14159 * self._radius ** 2


# ---------- 4.4 @functools.lru_cache：缓存无参或 hashable 参数的函数结果 ----------
@functools.lru_cache(maxsize=128)
def fib(n: int) -> int:
    """斐波那契，同样 n 只算一次。"""
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)


# ---------- 4.5 @functools.cache：无大小限制的缓存（Python 3.9+）----------
@functools.cache
def factorial(n: int) -> int:
    """阶乘，结果永久缓存。"""
    if n <= 1:
        return 1
    return n * factorial(n - 1)


# ---------- 4.6 @abstractmethod：抽象方法，子类必须实现（需配合 ABC）----------
class Animal(ABC):
    @abstractmethod
    def speak(self) -> str:
        """子类必须实现。"""
        ...


class Dog(Animal):
    def speak(self) -> str:
        return "汪汪"


# ==================== 主流程：按顺序跑一遍 ====================

async def main() -> None:
    print("=== 1. 同步装饰器 ===")
    c = add(2, 4)
    print(f"add(2, 4) = {c}\n")

    print("=== 2. 带参装饰器 repeat(2) ===")
    greet("World")
    print()

    print("=== 3. 异步装饰器 ===")
    out = await fetch_data(0.1)
    print(f"fetch_data 返回: {out}\n")

    print("=== 4. 内置装饰器示例 ===")
    print("  MathUtils.add(1, 2) =", MathUtils.add(1, 2))
    p = Person.from_birth_year("Bob", 1995)
    print("  Person.from_birth_year ->", p.name, p.age)

    circle = Circle(3.0)
    print("  Circle(3).area =", circle.area)
    circle.radius = 2.0
    print("  radius=2 后 area =", circle.area)

    print("  fib(35) 第一次（会算）:", fib(35))
    print("  fib(35) 第二次（走缓存）:", fib(35))
    print("  factorial(10) =", factorial(10))

    print("  Dog().speak() =", Dog().speak())


if __name__ == "__main__":
    asyncio.run(main())
