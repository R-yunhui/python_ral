def function_one() -> tuple[int, str]:
    return 15, "Mike"


def function_two():
    fruits = ["apple", "banana", "cherry", "peach"]
    print(f"前2个水果: {fruits[:2]}")
    print(f"后2个水果: {fruits[2:]}")
    

def function_three() -> dict[str, int]:
    return {"apple": 1, "banana": 2, "cherry": 3, "peach": 4}


def main():
    age, name = function_one()
    print(f"年龄: {age}, 姓名: {name}")

    function_two()
    
    fruits = function_three()
    # 获取西瓜的数量，如果没有则返回0，不会出现 KeyError
    watermelon = fruits.get("watermelon", 0)
    print(f"西瓜: {watermelon}")
    
    try:
        # 使用 KeyError 捕获异常
        watermelon = fruits["watermelon"]
    except KeyError:
        print("西瓜不存在")
    print(f"西瓜: {watermelon}")
    
    


if __name__ == "__main__":
    main()
