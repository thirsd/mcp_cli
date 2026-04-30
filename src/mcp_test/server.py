"""基于 FastMCP 的 HTTP 测试服务，提供天气查询和加减乘除工具."""

from fastmcp import FastMCP

server = FastMCP(name="mcp-test-server")

# ── 模拟天气数据 ──────────────────────────────────────────────

WEATHER_DATA = {
    "北京": {"temperature": 22, "humidity": 45, "condition": "晴", "wind": "北风 3级"},
    "上海": {"temperature": 26, "humidity": 72, "condition": "多云", "wind": "东风 2级"},
    "广州": {"temperature": 31, "humidity": 85, "condition": "雷阵雨", "wind": "南风 2级"},
    "深圳": {"temperature": 30, "humidity": 80, "condition": "阵雨", "wind": "东南风 3级"},
    "成都": {"temperature": 24, "humidity": 65, "condition": "阴", "wind": "微风"},
    "杭州": {"temperature": 25, "humidity": 70, "condition": "多云转晴", "wind": "东风 2级"},
    "武汉": {"temperature": 28, "humidity": 60, "condition": "晴", "wind": "南风 3级"},
    "西安": {"temperature": 20, "humidity": 40, "condition": "晴", "wind": "西北风 2级"},
    "重庆": {"temperature": 27, "humidity": 75, "condition": "多云", "wind": "微风"},
    "南京": {"temperature": 25, "humidity": 68, "condition": "晴转多云", "wind": "东风 2级"},
}


@server.tool
def get_weather(city: str) -> str:
    """查询指定城市的天气信息。

    Args:
        city: 城市名称，如：北京、上海、广州
    """
    if city in WEATHER_DATA:
        data = WEATHER_DATA[city]
        return (
            f"{city}天气：{data['condition']}，"
            f"气温 {data['temperature']}°C，"
            f"湿度 {data['humidity']}%，"
            f"{data['wind']}"
        )
    return f"未找到城市「{city}」的天气数据。支持的城市：{', '.join(WEATHER_DATA.keys())}"


@server.tool
def list_cities() -> str:
    """列出所有支持查询天气的城市。"""
    cities = ", ".join(WEATHER_DATA.keys())
    return f"支持查询的城市：{cities}"


# ── 计算器工具 ────────────────────────────────────────────────


@server.tool
def add(a: float, b: float) -> str:
    """计算两个数的和。

    Args:
        a: 第一个数
        b: 第二个数
    """
    return f"{a} + {b} = {a + b}"


@server.tool
def subtract(a: float, b: float) -> str:
    """计算两个数的差。

    Args:
        a: 被减数
        b: 减数
    """
    return f"{a} - {b} = {a - b}"


@server.tool
def multiply(a: float, b: float) -> str:
    """计算两个数的积。

    Args:
        a: 第一个因数
        b: 第二个因数
    """
    return f"{a} × {b} = {a * b}"


@server.tool
def divide(a: float, b: float) -> str:
    """计算两个数的商。

    Args:
        a: 被除数
        b: 除数（不能为 0）
    """
    if b == 0:
        return "错误：除数不能为 0"
    return f"{a} ÷ {b} = {a / b}"


if __name__ == "__main__":
    server.run(transport="streamable-http", host="127.0.0.1", port=9000, path="/mcp")
