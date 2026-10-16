"""Calendar helpers. Months are represented as 'YYYY-MM' strings."""

from __future__ import annotations

import calendar
import datetime as dt
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MONTH_NAMES = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]


def today_in(timezone: str) -> dt.date:
    try:
        return dt.datetime.now(ZoneInfo(timezone)).date()
    except (ZoneInfoNotFoundError, ValueError):
        return dt.datetime.now(dt.UTC).date()


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(microsecond=0)


def is_valid_timezone(name: str) -> bool:
    try:
        ZoneInfo(name)
        return True
    except (ZoneInfoNotFoundError, ValueError):
        return False


def month_key(day: dt.date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def parse_month(value: str) -> tuple[int, int]:
    try:
        year_s, month_s = value.split("-")
        year, month = int(year_s), int(month_s)
    except ValueError as exc:
        raise ValueError(f"Invalid month {value!r}; expected YYYY-MM") from exc
    if not (1 <= month <= 12 and 2000 <= year <= 2100):
        raise ValueError(f"Invalid month {value!r}")
    return year, month


def month_bounds(value: str) -> tuple[dt.date, dt.date]:
    year, month = parse_month(value)
    return dt.date(year, month, 1), dt.date(year, month, calendar.monthrange(year, month)[1])


def days_in_month(value: str) -> int:
    year, month = parse_month(value)
    return calendar.monthrange(year, month)[1]


def shift_month(value: str, delta: int) -> str:
    year, month = parse_month(value)
    index = year * 12 + (month - 1) + delta
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def months_between(start: str, end: str) -> list[str]:
    """Inclusive list of month keys from start to end."""
    result = []
    current = start
    while current <= end:
        result.append(current)
        current = shift_month(current, 1)
    return result


def month_label(value: str) -> str:
    year, month = parse_month(value)
    return f"{calendar.month_name[month]} {year}"


def short_month_label(value: str) -> str:
    year, month = parse_month(value)
    return f"{calendar.month_abbr[month]} {year}"


def add_months(day: dt.date, months: int) -> dt.date:
    index = day.year * 12 + (day.month - 1) + months
    year, month = index // 12, index % 12 + 1
    return dt.date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def months_until(start: dt.date, end: dt.date) -> float:
    """Approximate number of months between two dates (average month length)."""
    return (end - start).days / 30.4375


def daterange(start: dt.date, end: dt.date):
    current = start
    while current <= end:
        yield current
        current += dt.timedelta(days=1)


def format_date(day: dt.date) -> str:
    return f"{day.day} {calendar.month_abbr[day.month]} {day.year}"
