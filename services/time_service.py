"""
time_service.py – All datetime helpers for the bot.
"""
from datetime import datetime, timedelta, timezone
from config import Config

ICT = timezone(timedelta(hours=Config.UTC_OFFSET_HOURS))


def now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)

def now_ict() -> datetime:
    return datetime.now(tz=ICT)


def calc_next_spawn(last_kill_time: datetime, cycle_minutes: int) -> datetime:
    """
    Tính next spawn tiếp theo còn trong tương lai.
    Nếu spawn đã qua (boss đã ra mà chưa có kill mới),
    tự cộng thêm cycle cho đến khi còn trong tương lai.
    """
    next_spawn = last_kill_time + timedelta(minutes=cycle_minutes)
    now = now_utc()

    # Nếu spawn đã qua → tiến lên cycle kế tiếp
    while next_spawn <= now:
        next_spawn += timedelta(minutes=cycle_minutes)

    return next_spawn


def calc_remain(next_spawn: datetime) -> timedelta:
    return next_spawn - now_utc()


def format_remain(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())

    if total_seconds <= 0:
        return "Spawned"
    if total_seconds < 60:
        return "< 1m"

    total_minutes = total_seconds // 60
    hours, minutes = divmod(total_minutes, 60)

    if hours > 0:
        return f"{hours}h{minutes:02d}m"
    return f"{minutes}m"


def format_datetime_ict(dt: datetime) -> str:
    return dt.astimezone(ICT).strftime("%m/%d/%y %H:%M (UTC+7)")


def format_time_ict(dt: datetime) -> str:
    return dt.astimezone(ICT).strftime("%H:%M")


def parse_kill_time(time_str: str) -> datetime:
    cleaned = time_str.strip().lower()

    if cleaned == "now":
        return now_utc()

    try:
        parsed_time = datetime.strptime(cleaned, "%H:%M").time()
    except ValueError:
        raise ValueError(
            f"Định dạng thời gian không hợp lệ: `{time_str}`. "
            "Dùng `now` hoặc `HH:mm` (vd: `17:40`)."
        )

    today_ict = now_ict().date()
    naive_ict = datetime.combine(today_ict, parsed_time)
    aware_ict = naive_ict.replace(tzinfo=ICT)
    return aware_ict.astimezone(timezone.utc)