from functools import lru_cache
import json

from array import array
from random import random
from typing import Any
from datetime import datetime


class User:

    def __init__(self, name: str, age: int, gender: str, phone: str):
        self.name = name
        self.age = age
        self.gender = gender
        self.phone = phone

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        # 自定义 name 属性的 setter 方法，可以进行参数校验
        if value is None or value == "":
            raise ValueError("name cannot be empty")
        self._name = "@" + value + "@"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "User":
        """
        从字典创建 User 对象
        :param data: 字典
        :return: User 对象
        """
        return cls(**data)

    def __str__(self):
        return f"User(name={self.name}, age={self.age}, gender={self.gender}, phone={self.phone})"


class MathUtils:

    @staticmethod
    def add(a: int, b: int) -> int:
        return a + b

    @staticmethod
    def subtract(a: int, b: int) -> int:
        return a - b

    @staticmethod
    def multiply(a: int, b: int) -> int:
        return a * b

    @staticmethod
    def divide(a: int, b: int) -> float:
        return a / b


def data_structure():
    # py 基础数据结构
    # 1.数值类型
    num: int = 10
    float_num: float = 10.5
    complex_num: complex = 10 + 2j
    bool_num: bool = True
    print(
        f"num: {num}, float_num: {float_num}, complex_num: {complex_num}, bool_num: {bool_num}"
    )

    # 2.字符串类型
    str_num: str = "10"
    print(f"str_num: {str_num}")

    # 3.列表类型
    list_num: list[int] = [1, 2, 3, 4, 5]
    print(f"list_num: {list_num}")

    # 4.元组类型
    tuple_num: tuple[int, str, float] = (1, "2", 3.0)
    print(f"tuple_num: {tuple_num}")

    # 5.字典类型
    dict_num: dict[str, int] = {"a": 1, "b": 2, "c": 3}
    print(f"dict_num: {dict_num}")

    # 6.集合类型
    set_num: set[int] = {1, 2, 3, 4, 5}

    # 集合操作 交集 并集 差集
    intersection: set[int] = set_num & {3, 4, 5, 6}
    union: set[int] = set_num | {3, 4, 5, 6}
    difference: set[int] = set_num - {3, 4, 5, 6}
    print(f"intersection: {intersection}, union: {union}, difference: {difference}")
    print(f"set_num: {set_num}")

    # 7.数组类型
    array_num: array[int] = array("i", [1, 2, 3, 4, 5])
    print(f"array_num: {array_num}")

    hello_str: str = "hello"
    hello_list: list[str] = list(hello_str)  # 字符串转字符数组（列表）
    print(f"hello_list: {hello_list}")


def get_user() -> tuple[str, int, str, str]:
    return "张三", 21, "男", "13800138000"


def create_user(*args: Any) -> User:
    """
    创建用户对象
    :param args: 用户信息 位置参数
    :return: 用户对象
    """
    print(f"args: {args}")
    return User(*args)


def create_user_kwargs(**kwargs: Any) -> User:
    """
    创建用户对象
    :param kwargs: 用户信息 关键字参数
    :return: 用户对象
    """
    print(f"kwargs: {kwargs}")
    return User(**kwargs)


def json_demo():
    user_dict: dict[str, Any] = {
        "name": "张三",
        "age": 21,
        "gender": "男",
        "phone": "13800138000",
    }
    # 将字典序列化为 JSON 字符串
    # json.dumps 默认不支持直接序列化自定义对象如 User，需要先转换为 dict 或实现自定义序列化方法。
    user_json: str = json.dumps(user_dict, ensure_ascii=False, indent=2)
    print(f"user_json: {user_json}")

    # 将 JSON 字符串反序列化为 user
    # 两步：1. 将 JSON 字符串反序列化为字典 2. 将字典转为 User 对象
    user_dict: dict[str, Any] = json.loads(user_json)
    user: User = User(**user_dict)
    print(f"user: {user.__dict__}")


@lru_cache(maxsize=1)
def get_number(n: int = 1) -> int:
    """
    获取随机数
    :return: 随机数
    """
    return int(random() * 100) + 1


def main():
    # 基础数据结构
    # data_structure()

    # # 通过元组直接接收
    # name, age, gender, phone = get_user()
    # print(f"name: {name}, age: {age}, gender: {gender}, phone: {phone}")

    # # 使用位置参数创建用户对象，参数顺序必须要保持一致，不能多传递或者少传递，否则会导致值出错
    # user = create_user(name, age, gender, phone)
    # print(f"user: {user.__dict__}")

    # # 使用关键字参数创建用户对象时，参数名必须与类属性名一致，参数多传递或者少传递都会报错
    # user2 = create_user_kwargs(
    #     name="李四",
    #     age=22,
    #     gender="女",
    #     phone="13800138001",
    # )
    # print(f"user: {user2.__dict__}")

    # json_demo()

    # # 通过 @staticmethod 装饰器创建静态方法，静态方法不需要实例化，可以直接通过类名调用
    # print(MathUtils.add(1, 2))
    # print(MathUtils.subtract(1, 2))
    # print(MathUtils.multiply(1, 2))
    # print(MathUtils.divide(1, 2))
    
    # # 通过 @classmethod 装饰器创建类方法，类方法不需要实例化，可以直接通过类名调用
    # user_dict: dict[str, Any] = {
    #     "name": "张三",
    #     "age": 21,
    #     "gender": "男",
    #     "phone": "13800138000",
    # }
    # user: User = User.from_dict(user_dict)
    # print(f"user: {user.__dict__}")
    
    # user.name = "李四"
    # print(f"user: {user.__dict__}")
    
    # lru_cache 缓存函数结果，当参数相同时，直接从缓存中获取结果，不会重新计算
    # 当参数不同时，会重新计算并缓存结果，maxsize：缓存大小，当缓存大小达到最大值时，会删除最久未使用的缓存
    # typed：是否缓存不同类型的参数，当 typed 为 True 时，不同类型的参数会缓存不同的结果
    number = get_number(1)
    print(f"number: {number}")
    number = get_number(2)
    print(f"number: {number}")
    number = get_number(2)   
    print(f"number: {number}")
    number = get_number(1)   
    print(f"number: {number}")
    number = get_number(2)   
    print(f"number: {number}")


if __name__ == "__main__":
    main()
