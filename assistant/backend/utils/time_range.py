from datetime import datetime, timedelta
import zoneinfo


TZ = zoneinfo.ZoneInfo("Asia/Shanghai")


def parse_date_range(expr: str) -> tuple[datetime, datetime]:
    """解析中文时间表达式，返回 (start, end) 元组（上海时区）"""
    now = datetime.now(TZ)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if expr == "今天":
        return today, today.replace(hour=23, minute=59, second=59)
    elif expr == "昨天":
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday.replace(hour=23, minute=59, second=59)
    elif expr == "这周":
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        return monday, sunday.replace(hour=23, minute=59, second=59)
    elif expr == "上周":
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        return last_monday, last_sunday.replace(hour=23, minute=59, second=59)
    elif expr == "这个月":
        return today.replace(day=1), (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
    elif expr == "上个月":
        first_this = today.replace(day=1)
        first_last = (first_this - timedelta(days=1)).replace(day=1)
        return first_last, first_this - timedelta(seconds=1)
    elif expr.startswith("最近"):
        days = int(expr.replace("最近", "").replace("天", ""))
        return today - timedelta(days=days - 1), now
    else:
        # 默认今天
        return today, today.replace(hour=23, minute=59, second=59)
