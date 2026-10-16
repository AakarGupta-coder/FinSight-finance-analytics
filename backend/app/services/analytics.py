"""Aggregations over stored transactions used by the dashboard and analytics."""

from __future__ import annotations

import datetime as dt
from collections import defaultdict

from app.domain.categories import PAYMENT_METHODS
from app.domain.dates import (
    daterange,
    month_bounds,
    month_key,
    months_between,
    shift_month,
    short_month_label,
    today_in,
)
from app.domain.models import Expense, Preferences
from app.domain.money import divide, pct_change, percent
from app.errors import ValidationFailed
from app.repositories.base import Repository
from app.services.preferences import category_names

MAX_RANGE_DAYS = 366 * 3


def total(expenses: list[Expense]) -> int:
    return sum(e.amount_minor for e in expenses)


def category_breakdown(expenses: list[Expense], names: dict[str, str]) -> list[dict]:
    totals: dict[str, int] = defaultdict(int)
    counts: dict[str, int] = defaultdict(int)
    for e in expenses:
        totals[e.category] += e.amount_minor
        counts[e.category] += 1
    grand = sum(totals.values())
    rows = [
        {"category": cat, "category_name": names.get(cat, cat), "amount_minor": amt,
         "share_pct": percent(amt, grand), "count": counts[cat]}
        for cat, amt in totals.items()
    ]
    return sorted(rows, key=lambda r: -r["amount_minor"])


def payment_method_breakdown(expenses: list[Expense]) -> list[dict]:
    names = {p["id"]: p["name"] for p in PAYMENT_METHODS}
    totals: dict[str, int] = defaultdict(int)
    counts: dict[str, int] = defaultdict(int)
    for e in expenses:
        totals[e.payment_method] += e.amount_minor
        counts[e.payment_method] += 1
    grand = sum(totals.values())
    return sorted(
        [{"payment_method": k, "name": names.get(k, k), "amount_minor": v, "share_pct": percent(v, grand),
          "count": counts[k]} for k, v in totals.items()],
        key=lambda r: -r["amount_minor"],
    )


def daily_series(expenses: list[Expense], start: dt.date, end: dt.date) -> list[dict]:
    totals: dict[dt.date, int] = defaultdict(int)
    for e in expenses:
        totals[e.date] += e.amount_minor
    return [{"date": d.isoformat(), "amount_minor": totals.get(d, 0)} for d in daterange(start, end)]


def monthly_series(expenses: list[Expense], months: list[str]) -> list[dict]:
    by_month: dict[str, dict[str, int]] = {m: defaultdict(int) for m in months}
    for e in expenses:
        key = month_key(e.date)
        if key in by_month:
            by_month[key][e.category] += e.amount_minor
    return [
        {"month": m, "label": short_month_label(m), "total_minor": sum(by_month[m].values()),
         "by_category": dict(by_month[m])}
        for m in months
    ]


def top_merchants(expenses: list[Expense], limit: int = 5) -> list[dict]:
    totals: dict[str, int] = defaultdict(int)
    counts: dict[str, int] = defaultdict(int)
    display: dict[str, str] = {}
    for e in expenses:
        if not e.merchant:
            continue
        key = e.merchant.strip().lower()
        display.setdefault(key, e.merchant.strip())
        totals[key] += e.amount_minor
        counts[key] += 1
    rows = sorted(totals.items(), key=lambda kv: -kv[1])[:limit]
    return [{"merchant": display[k], "amount_minor": v, "count": counts[k]} for k, v in rows]


def month_summary(expenses: list[Expense], month: str, today: dt.date) -> dict:
    """Summary for a month, including a like-for-like comparison with the previous month.

    For the current (incomplete) month the comparison uses the same day range
    of the previous month (e.g. 1-15 Oct vs 1-15 Sep) so partial months are not
    compared against complete ones.
    """
    start, end = month_bounds(month)
    prev = shift_month(month, -1)
    p_start, p_end = month_bounds(prev)
    is_current = month == month_key(today)
    effective_end = min(end, today) if is_current else end
    current = [e for e in expenses if start <= e.date <= effective_end]
    previous_full = [e for e in expenses if p_start <= e.date <= p_end]

    if is_current:
        cutoff_day = min(today.day, p_end.day)
        cmp_end = p_start.replace(day=cutoff_day)
        previous_cmp = [e for e in previous_full if e.date <= cmp_end]
        comparison_label = f"1-{cutoff_day} of previous month"
    else:
        cmp_end = p_end
        previous_cmp = previous_full
        comparison_label = "full previous month"

    days_elapsed = (effective_end - start).days + 1 if effective_end >= start else 0
    cur_total = total(current)
    largest = max(current, key=lambda e: e.amount_minor, default=None)
    return {
        "month": month,
        "is_current_month": is_current,
        "period_start": start.isoformat(),
        "period_end": effective_end.isoformat(),
        "total_minor": cur_total,
        "transaction_count": len(current),
        "days_elapsed": days_elapsed,
        "average_daily_minor": divide(cur_total, days_elapsed) if days_elapsed else 0,
        "previous_month": prev,
        "previous_month_total_minor": total(previous_full),
        "previous_comparable_total_minor": total(previous_cmp),
        "comparison_period": {"start": p_start.isoformat(), "end": cmp_end.isoformat(), "label": comparison_label},
        "change_pct": pct_change(cur_total, total(previous_cmp)),
        "largest_expense": (
            {"id": largest.id, "description": largest.description, "amount_minor": largest.amount_minor,
             "date": largest.date.isoformat(), "category": largest.category}
            if largest else None
        ),
    }


def range_analytics(repo: Repository, prefs: Preferences, start: dt.date, end: dt.date) -> dict:
    if start > end:
        raise ValidationFailed("Start date must be on or before end date.")
    if (end - start).days > MAX_RANGE_DAYS:
        raise ValidationFailed("Date range is too large (maximum 3 years).")
    expenses = repo.list_expenses(prefs.user_id, start, end)
    names = category_names(prefs)
    days = (end - start).days + 1
    grand = total(expenses)
    months = months_between(month_key(start), month_key(end))
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "days": days,
        "total_minor": grand,
        "transaction_count": len(expenses),
        "average_daily_minor": divide(grand, days),
        "average_transaction_minor": divide(grand, len(expenses)) if expenses else 0,
        "categories": category_breakdown(expenses, names),
        "payment_methods": payment_method_breakdown(expenses),
        "daily": daily_series(expenses, start, end) if days <= 120 else [],
        "monthly": monthly_series(expenses, months),
        "top_merchants": top_merchants(expenses),
        "category_names": names,
    }


def recent_months_history(repo: Repository, prefs: Preferences, months: int = 6) -> list[dict]:
    today = today_in(prefs.timezone)
    end_month = month_key(today)
    start_month = shift_month(end_month, -(months - 1))
    start, _ = month_bounds(start_month)
    expenses = repo.list_expenses(prefs.user_id, start, today)
    return monthly_series(expenses, months_between(start_month, end_month))
