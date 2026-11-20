"""Local time helpers. Turkey has used a fixed UTC+3 since 2016, which is the fallback when tz data is missing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
from functools import lru_cache


@lru_cache(maxsize=8)
def tz(name: str) -> tzinfo:
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(name)
    except Exception:  # noqa: BLE001 - no tz database (e.g. in the browser build)
        return timezone(timedelta(hours=3), "TRT")


def local(ts: float, name: str) -> datetime:
    return datetime.fromtimestamp(ts, tz(name))


def hour(ts: float, name: str) -> int:
    return local(ts, name).hour


def at(day: datetime, hour_: int, minute: int = 0) -> float:
    return day.replace(hour=hour_, minute=minute, second=0, microsecond=0).timestamp()
