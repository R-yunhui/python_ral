# 自定义 mcp_server — 展示动态工具增删 + 实时通知推送
from typing import Literal

import mcp.types as mcp_types
from fastmcp import Context, FastMCP
from fastmcp.tools.function_tool import FunctionTool

mcp = FastMCP("mcp_server")


@mcp.tool(
    name="calculator",
    description="计算器工具, 可以计算两个数的加减乘除",
    version="1.0.0",
)
async def calculate(
    a: float, b: float, operation: Literal["add", "subtract", "multiply", "divide"]
) -> float:
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b


@mcp.tool(
    name="echo",
    description="回显工具，原样返回输入文本",
)
async def echo(message: str) -> str:
    return f"Echo: {message}"


# ==================== 动态工具管理 ====================


def _tool_exists(name: str) -> bool:
    """检查工具是否已注册"""
    key = f"tool:{name}@"
    return key in mcp.local_provider._components


@mcp.tool(
    name="register_weather",
    description="动态注册天气查询工具",
)
async def register_weather(ctx: Context) -> str:
    if _tool_exists("weather"):
        return "weather 工具已存在"

    async def weather(city: str) -> str:
        import random

        conditions = ["晴天", "多云", "小雨", "阴天", "大风"]
        temp = random.randint(10, 35)
        return f"{city} 天气: {random.choice(conditions)}, {temp}°C"

    mcp.add_tool(
        FunctionTool.from_function(
            weather,
            name="weather",
            description="查询指定城市的天气信息",
        )
    )
    # 手动推送通知
    await ctx.send_notification(mcp_types.ToolListChangedNotification())
    return "weather 工具已注册成功"


@mcp.tool(
    name="register_converter",
    description="动态注册单位转换工具（温度/长度）",
)
async def register_converter(ctx: Context) -> str:
    if _tool_exists("unit_converter"):
        return "unit_converter 工具已存在"

    async def unit_converter(value: float, from_unit: str, to_unit: str) -> str:
        conversions = {
            ("celsius", "fahrenheit"): lambda v: v * 9 / 5 + 32,
            ("fahrenheit", "celsius"): lambda v: (v - 32) * 5 / 9,
            ("meter", "foot"): lambda v: v * 3.28084,
            ("foot", "meter"): lambda v: v / 3.28084,
            ("kilometer", "mile"): lambda v: v * 0.621371,
            ("mile", "kilometer"): lambda v: v / 0.621371,
        }
        key = (from_unit.lower(), to_unit.lower())
        if key not in conversions:
            supported = ", ".join(f"{a} -> {b}" for a, b in conversions)
            return f"不支持的转换: {from_unit} -> {to_unit}。支持的转换: {supported}"
        result = conversions[key](value)
        return f"{value} {from_unit} = {result:.2f} {to_unit}"

    mcp.add_tool(
        FunctionTool.from_function(
            unit_converter,
            name="unit_converter",
            description="单位转换工具，支持温度(celsius/fahrenheit)和长度(meter/foot/kilometer/mile)转换",
        )
    )
    await ctx.send_notification(mcp_types.ToolListChangedNotification())
    return "unit_converter 工具已注册成功"


@mcp.tool(
    name="remove_tool",
    description="按名称动态移除已注册的工具",
)
async def remove_tool(ctx: Context, name: str) -> str:
    try:
        mcp.local_provider.remove_tool(name)
        await ctx.send_notification(mcp_types.ToolListChangedNotification())
        return f"工具 '{name}' 已移除"
    except KeyError:
        return f"工具 '{name}' 不存在"


@mcp.tool(
    name="list_registered_tools",
    description="列出当前所有可用工具",
)
async def list_registered_tools() -> str:
    tools = await mcp.list_tools()
    if not tools:
        return "当前没有可用工具"
    lines = [f"  - {t.name}: {t.description or '无描述'}" for t in tools]
    return f"当前可用工具 ({len(tools)} 个):\n" + "\n".join(lines)


@mcp.tool(
    name="toggle_echo",
    description="切换 echo 工具的启用/禁用状态",
)
async def toggle_echo(ctx: Context) -> str:
    key = "tool:echo@"
    if key not in mcp.local_provider._components:
        return "echo 工具不存在"

    current_tools = await mcp.list_tools()
    names = [t.name for t in current_tools]

    if "echo" in names:
        mcp.disable(keys={key})
    else:
        mcp.enable(keys={key})
    await ctx.send_notification(mcp_types.ToolListChangedNotification())

    return "echo 工具已禁用" if "echo" in names else "echo 工具已启用"


if __name__ == "__main__":
    mcp.run(transport="streamable-http", port=10010, path="/mcp")
