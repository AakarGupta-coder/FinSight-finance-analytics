"""Detection of recurring payments (subscriptions, rent, bills).

A group of transactions is considered recurring when they share a merchant
(or description), have similar amounts (within 15% of the median) and occur at
regular weekly or monthly intervals.
"""

from __future__ import annotations

import datetime as dt
import re
import statistics
from collections import defaultdict

from app.domain.models import Expense
from app.domain.money import scale

CADENCES = {
    "weekly": (6, 8, 52 / 12),
    "monthly": (26, 35, 1.0),
}
AMOUNT_TOLERANCE = 0.15


def merchant_key(expense: Expense) -> str:
    source = expense.merchant or expense.description
    return re.sub(r"[^a-z0-9]+", " ", source.lower()).strip()


def detect_recurring(expenses: list[Expense], today: dt.date) -> list[dict]:
    groups: dict[tuple[str, str], list[Expense]] = defaultdict(list)
    for e in expenses:
        key = merchant_key(e)
        if key:
            groups[(key, e.category)].append(e)

    results = []
    for (key, category), items in groups.items():
        if len(items) < 2:
            continue
        items.sort(key=lambda e: e.date)
        amounts = [e.amount_minor for e in items]
        median = statistics.median(amounts)
        if median <= 0 or any(abs(a - median) > AMOUNT_TOLERANCE * median for a in amounts):
            continue
        intervals = [(b.date - a.date).days for a, b in zip(items, items[1:])]
        for cadence, (low, high, per_month) in CADENCES.items():
            if all(low <= gap <= high for gap in intervals):
                typical = int(round(median))
                last = items[-1].date
                expected_gap = round(statistics.mean(intervals))
                next_expected = last + dt.timedelta(days=expected_gap)
                # A series is "active" if the next payment is not long overdue.
                active = (today - next_expected).days <= expected_gap // 2 + 3
                results.append({
                    "key": key,
                    "name": items[-1].merchant or items[-1].description,
                    "category": category,
                    "cadence": cadence,
                    "typical_amount_minor": typical,
                    "monthly_equivalent_minor": scale(typical, per_month),
                    "occurrences": len(items),
                    "confidence": "high" if len(items) >= 3 else "low",
                    "first_date": items[0].date.isoformat(),
                    "last_date": last.isoformat(),
                    "next_expected": next_expected.isoformat(),
                    "active": active,
                    "expense_ids": [e.id for e in items],
                })
                break
    return sorted(results, key=lambda r: -r["monthly_equivalent_minor"])
