"""Budget management, utilization, threshold alerts and history."""

from __future__ import annotations

import datetime as dt
from collections import defaultdict

from app.domain.categories import OVERALL_BUDGET_KEY
from app.domain.dates import (
    days_in_month,
    month_bounds,
    month_key,
    months_between,
    parse_month,
    shift_month,
    today_in,
    utc_now,
)
from app.domain.models import Budget, BudgetAlertEvent, Expense, Preferences
from app.domain.money import MAX_AMOUNT_MINOR, divide, percent
from app.errors import Conflict, NotFound, ValidationFailed
from app.repositories.base import Repository
from app.services.preferences import category_ids, category_names

MIN_DAYS_FOR_PROJECTION = 3


def budget_key(budget: Budget) -> str:
    return budget.category or OVERALL_BUDGET_KEY


def applies_to(budget: Budget, month: str) -> bool:
    return budget.effective_from <= month and (budget.effective_to is None or budget.effective_to >= month)


def budgets_for_month(budgets: list[Budget], month: str) -> dict[str, Budget]:
    """The budget version in effect for each key during ``month``."""
    active: dict[str, Budget] = {}
    for budget in budgets:
        if not applies_to(budget, month):
            continue
        key = budget_key(budget)
        if key not in active or budget.effective_from > active[key].effective_from:
            active[key] = budget
    return active


def _validate_amount(amount_minor: int) -> None:
    if not isinstance(amount_minor, int) or amount_minor < 0:
        raise ValidationFailed("Budget amount cannot be negative.")
    if amount_minor > MAX_AMOUNT_MINOR:
        raise ValidationFailed("Budget amount is unrealistically large.")


def create_budget(repo: Repository, prefs: Preferences, category: str | None, amount_minor: int,
                  *, is_demo: bool = False, effective_from: str | None = None) -> Budget:
    _validate_amount(amount_minor)
    if category is not None and category not in category_ids(prefs):
        raise ValidationFailed("Unknown category.")
    current = month_key(today_in(prefs.timezone))
    start = effective_from or current
    parse_month(start)
    existing = budgets_for_month(repo.list_budgets(prefs.user_id), start)
    key = category or OVERALL_BUDGET_KEY
    if key in existing:
        raise Conflict("A budget for this category already exists. Edit it instead.")
    budget = Budget(user_id=prefs.user_id, category=category, amount_minor=amount_minor,
                    effective_from=start, is_demo=is_demo)
    repo.put_budget(budget)
    return budget


def update_budget(repo: Repository, prefs: Preferences, budget_id: str, amount_minor: int) -> Budget:
    """Change a budget amount from the current month onward.

    If the budget already applied to earlier months, those months keep the old
    amount (a new version starts this month) so history remains accurate.
    """
    _validate_amount(amount_minor)
    budget = repo.get_budget(prefs.user_id, budget_id)
    if not budget:
        raise NotFound("Budget not found.")
    current = month_key(today_in(prefs.timezone))
    if budget.effective_to is not None and budget.effective_to < current:
        raise ValidationFailed("This budget has ended and can no longer be edited.")
    # A new amount re-arms this month's threshold alerts for the budget.
    repo.delete_budget_alert_events(prefs.user_id, current, budget_key(budget))
    if budget.effective_from >= current:
        budget.amount_minor = amount_minor
        budget.updated_at = utc_now()
        repo.put_budget(budget)
        return budget
    budget.effective_to = shift_month(current, -1)
    budget.updated_at = utc_now()
    repo.put_budget(budget)
    new_version = Budget(user_id=prefs.user_id, category=budget.category, amount_minor=amount_minor,
                         effective_from=current, is_demo=budget.is_demo)
    repo.put_budget(new_version)
    return new_version


def delete_budget(repo: Repository, prefs: Preferences, budget_id: str) -> None:
    budget = repo.get_budget(prefs.user_id, budget_id)
    if not budget:
        raise NotFound("Budget not found.")
    current = month_key(today_in(prefs.timezone))
    repo.delete_budget_alert_events(prefs.user_id, current, budget_key(budget))
    if budget.effective_from >= current:
        repo.delete_budget(prefs.user_id, budget_id)
    else:
        # Keep the record for past months; stop applying it from this month.
        budget.effective_to = shift_month(current, -1)
        budget.updated_at = utc_now()
        repo.put_budget(budget)


def evaluate(amount_minor: int, spent_minor: int, thresholds: list[int], *, month: str, today: dt.date) -> dict:
    """Pure budget evaluation used by the API, insights and tests."""
    current_month = month_key(today)
    is_current = month == current_month
    is_future = month > current_month
    total_days = days_in_month(month)
    if is_current:
        days_elapsed = today.day
    elif is_future:
        days_elapsed = 0
    else:
        days_elapsed = total_days

    utilization = percent(spent_minor, amount_minor)
    remaining = amount_minor - spent_minor

    if amount_minor == 0:
        status = "exceeded" if spent_minor > 0 else "ok"
    elif spent_minor > amount_minor:
        status = "exceeded"
    elif spent_minor == amount_minor:
        status = "at_limit"
    elif utilization is not None and thresholds and utilization >= min(thresholds):
        status = "warning"
    else:
        status = "ok"

    crossed = [t for t in sorted(thresholds) if amount_minor > 0 and spent_minor * 100 >= amount_minor * t]
    if amount_minor == 0 and spent_minor > 0:
        crossed = sorted(thresholds)

    projected = None
    projected_overrun = False
    if is_current and days_elapsed >= MIN_DAYS_FOR_PROJECTION and spent_minor > 0:
        projected = divide(spent_minor * total_days, days_elapsed)
        projected_overrun = status not in ("exceeded",) and projected > amount_minor

    return {
        "amount_minor": amount_minor,
        "spent_minor": spent_minor,
        "remaining_minor": remaining,
        "utilization_pct": utilization,
        "status": status,
        "thresholds_crossed": crossed,
        "projected_spend_minor": projected,
        "projected_overrun": projected_overrun,
        "days_elapsed": days_elapsed,
        "days_in_month": total_days,
        "daily_allowance_minor": (
            divide(max(remaining, 0), total_days - days_elapsed + 1)
            if is_current and total_days - days_elapsed + 1 > 0 else None
        ),
    }


def spending_by_category(expenses: list[Expense]) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for e in expenses:
        totals[e.category] += e.amount_minor
    return dict(totals)


def month_overview(repo: Repository, prefs: Preferences, month: str, *, record_events: bool = True) -> dict:
    start, end = month_bounds(month)
    today = today_in(prefs.timezone)
    expenses = repo.list_expenses(prefs.user_id, start, end)
    by_cat = spending_by_category(expenses)
    total_spent = sum(by_cat.values())
    budgets = budgets_for_month(repo.list_budgets(prefs.user_id), month)
    names = category_names(prefs)
    thresholds = prefs.budget_thresholds

    overall = None
    if OVERALL_BUDGET_KEY in budgets:
        b = budgets[OVERALL_BUDGET_KEY]
        overall = {"budget_id": b.id, "category": None, "category_name": "Overall",
                   "effective_from": b.effective_from,
                   **evaluate(b.amount_minor, total_spent, thresholds, month=month, today=today)}

    categories = []
    for key, b in budgets.items():
        if key == OVERALL_BUDGET_KEY:
            continue
        categories.append({"budget_id": b.id, "category": key, "category_name": names.get(key, key),
                           "effective_from": b.effective_from,
                           **evaluate(b.amount_minor, by_cat.get(key, 0), thresholds, month=month, today=today)})
    categories.sort(key=lambda c: (-(c["utilization_pct"] or 0), c["category_name"]))

    unbudgeted = [
        {"category": cat, "category_name": names.get(cat, cat), "spent_minor": amt}
        for cat, amt in sorted(by_cat.items(), key=lambda kv: -kv[1])
        if cat not in budgets
    ]

    new_alerts = []
    if record_events and month == month_key(today):
        new_alerts = record_threshold_events(repo, prefs, month, overall, categories)
    events = repo.list_budget_alert_events(prefs.user_id, month)

    return {
        "month": month,
        "total_spent_minor": total_spent,
        "overall": overall,
        "categories": categories,
        "unbudgeted": unbudgeted,
        "thresholds": thresholds,
        "new_alerts": new_alerts,
        "alert_events": [
            {"budget_key": ev.budget_key, "category_name": "Overall" if ev.budget_key == OVERALL_BUDGET_KEY
             else names.get(ev.budget_key, ev.budget_key), "threshold": ev.threshold,
             "spent_minor": ev.spent_minor, "budget_minor": ev.budget_minor, "created_at": ev.created_at}
            for ev in sorted(events, key=lambda e: e.created_at, reverse=True)
        ],
    }


def record_threshold_events(repo: Repository, prefs: Preferences, month: str, overall: dict | None,
                            categories: list[dict]) -> list[dict]:
    """Persist newly crossed thresholds once per (month, budget, threshold)."""
    new_alerts = []
    for row in ([overall] if overall else []) + categories:
        key = row["category"] or OVERALL_BUDGET_KEY
        for threshold in row["thresholds_crossed"]:
            event = BudgetAlertEvent(user_id=prefs.user_id, month=month, budget_key=key, threshold=threshold,
                                     spent_minor=row["spent_minor"], budget_minor=row["amount_minor"])
            if repo.record_budget_alert_event(event):
                new_alerts.append({"category_name": row["category_name"], "threshold": threshold,
                                   "spent_minor": row["spent_minor"], "budget_minor": row["amount_minor"]})
    return new_alerts


def check_alerts_for_date(repo: Repository, prefs: Preferences, day: dt.date) -> list[dict]:
    """Re-evaluate thresholds after a transaction change in the current month."""
    month = month_key(day)
    if month != month_key(today_in(prefs.timezone)):
        return []
    return month_overview(repo, prefs, month)["new_alerts"]


def history(repo: Repository, prefs: Preferences, months: int = 6) -> list[dict]:
    if not (1 <= months <= 24):
        raise ValidationFailed("months must be between 1 and 24")
    today = today_in(prefs.timezone)
    end_month = month_key(today)
    start_month = shift_month(end_month, -(months - 1))
    start, _ = month_bounds(start_month)
    _, end = month_bounds(end_month)
    expenses = repo.list_expenses(prefs.user_id, start, end)
    all_budgets = repo.list_budgets(prefs.user_id)
    rows = []
    for month in months_between(start_month, end_month):
        m_start, m_end = month_bounds(month)
        month_exp = [e for e in expenses if m_start <= e.date <= m_end]
        spent = sum(e.amount_minor for e in month_exp)
        active = budgets_for_month(all_budgets, month)
        overall = active.get(OVERALL_BUDGET_KEY)
        category_budget_total = sum(b.amount_minor for k, b in active.items() if k != OVERALL_BUDGET_KEY)
        by_cat = spending_by_category(month_exp)
        categories_over = [k for k, b in active.items() if k != OVERALL_BUDGET_KEY and by_cat.get(k, 0) > b.amount_minor]
        rows.append({
            "month": month,
            "spent_minor": spent,
            "overall_budget_minor": overall.amount_minor if overall else None,
            "category_budget_total_minor": category_budget_total or None,
            "utilization_pct": percent(spent, overall.amount_minor) if overall else None,
            "within_budget": (spent <= overall.amount_minor) if overall else None,
            "categories_over_budget": categories_over,
            "is_current": month == end_month,
        })
    return rows
