"""What-If financial simulator.

Purely computational: scenarios are evaluated against a baseline derived from
the user's real transactions, but nothing is written to storage. Hypothetical
changes never become expenses.
"""

from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from app.domain.categories import OVERALL_BUDGET_KEY
from app.domain.dates import add_months, month_bounds, month_key, shift_month, today_in
from app.domain.models import Expense, Preferences
from app.domain.money import MAX_AMOUNT_MINOR, divide, format_money, scale
from app.errors import ValidationFailed
from app.repositories.base import Repository
from app.services.budgets import budgets_for_month
from app.services.goals import get_goal, goal_metrics
from app.services.preferences import category_ids, category_names

BASELINES = {"last_month", "avg_3_months", "current_month_projection"}
MODES = {"percent", "amount", "target"}


@dataclass
class Adjustment:
    category: str
    mode: str  # percent: reduce by %, amount: reduce by fixed amount, target: set new monthly amount
    value: Decimal


@dataclass
class Scenario:
    name: str
    adjustments: list[Adjustment]


def compute_baseline(expenses: list[Expense], mode: str, today: dt.date) -> tuple[dict[str, int], dict]:
    """Monthly spending per category used as the 'current' figure."""
    if mode not in BASELINES:
        raise ValidationFailed(f"Baseline must be one of {sorted(BASELINES)}.")
    current_month = month_key(today)
    totals: dict[str, int] = defaultdict(int)
    if mode == "last_month":
        month = shift_month(current_month, -1)
        start, end = month_bounds(month)
        for e in expenses:
            if start <= e.date <= end:
                totals[e.category] += e.amount_minor
        info = {"mode": mode, "label": f"Spending in {month}", "start": start.isoformat(), "end": end.isoformat(),
                "months": 1}
    elif mode == "avg_3_months":
        months = [shift_month(current_month, -i) for i in (1, 2, 3)]
        start, _ = month_bounds(months[-1])
        _, end = month_bounds(months[0])
        with_data = {month_key(e.date) for e in expenses if start <= e.date <= end}
        divisor = max(len(with_data), 1)
        for e in expenses:
            if start <= e.date <= end:
                totals[e.category] += e.amount_minor
        totals = defaultdict(int, {k: divide(v, divisor) for k, v in totals.items()})
        info = {"mode": mode, "label": f"Average of {len(with_data)} month(s) with records",
                "start": start.isoformat(), "end": end.isoformat(), "months": len(with_data)}
    else:
        start, end = month_bounds(current_month)
        days = today.day
        for e in expenses:
            if start <= e.date <= today:
                totals[e.category] += e.amount_minor
        totals = defaultdict(int, {k: divide(v * end.day, days) for k, v in totals.items()})
        info = {"mode": mode, "label": f"This month projected from {days} day(s)", "start": start.isoformat(),
                "end": today.isoformat(), "months": 1, "is_projection": True}
    return dict(totals), info


def apply_adjustment(current: int, adj: Adjustment) -> tuple[int, list[str]]:
    warnings = []
    if adj.mode == "percent":
        if not (Decimal(0) <= adj.value <= Decimal(100)):
            raise ValidationFailed("Percentage reduction must be between 0 and 100.")
        new = current - scale(current, adj.value / 100)
    elif adj.mode == "amount":
        reduction = int(adj.value)
        if reduction < 0 or reduction > MAX_AMOUNT_MINOR:
            raise ValidationFailed("Reduction amount must be zero or positive.")
        if reduction > current:
            warnings.append("Reduction is larger than current spending; capped at current spending.")
            reduction = current
        new = current - reduction
    elif adj.mode == "target":
        target = int(adj.value)
        if target < 0 or target > MAX_AMOUNT_MINOR:
            raise ValidationFailed("Target monthly amount must be zero or positive.")
        new = target
    else:
        raise ValidationFailed("Adjustment mode must be percent, amount or target.")
    return new, warnings


def run_scenarios(repo: Repository, prefs: Preferences, scenarios: list[Scenario], baseline_mode: str,
                  goal_id: str | None = None) -> dict:
    if not scenarios:
        raise ValidationFailed("Provide at least one scenario.")
    if len(scenarios) > 4:
        raise ValidationFailed("Compare at most 4 scenarios at a time.")
    today = today_in(prefs.timezone)
    start = month_bounds(shift_month(month_key(today), -3))[0]
    expenses = repo.list_expenses(prefs.user_id, start, today)
    baseline, info = compute_baseline(expenses, baseline_mode, today)
    names = category_names(prefs)
    valid = category_ids(prefs)
    baseline_total = sum(baseline.values())
    money = lambda v: format_money(v, prefs.currency)  # noqa: E731

    budgets = budgets_for_month(repo.list_budgets(prefs.user_id), month_key(today))
    overall_budget = budgets.get(OVERALL_BUDGET_KEY)

    goal = None
    if goal_id:
        goal = get_goal(repo, prefs.user_id, goal_id)
        goal_info = goal_metrics(goal, today)

    results = []
    for scenario in scenarios:
        if not scenario.adjustments:
            raise ValidationFailed(f"Scenario '{scenario.name}' has no adjustments.")
        seen = set()
        rows, warnings = [], []
        for adj in scenario.adjustments:
            if adj.category not in valid:
                raise ValidationFailed(f"Unknown category: {adj.category}")
            if adj.category in seen:
                raise ValidationFailed(f"Category {adj.category} is adjusted twice in '{scenario.name}'.")
            seen.add(adj.category)
            current = baseline.get(adj.category, 0)
            new, w = apply_adjustment(current, adj)
            warnings += [f"{names.get(adj.category, adj.category)}: {msg}" for msg in w]
            if current == 0 and adj.mode != "target":
                warnings.append(f"{names.get(adj.category, adj.category)}: no spending in the baseline period.")
            rows.append({
                "category": adj.category, "category_name": names.get(adj.category, adj.category),
                "mode": adj.mode, "value": str(adj.value), "current_minor": current, "new_minor": new,
                "monthly_savings_minor": current - new,
            })
        monthly = sum(r["monthly_savings_minor"] for r in rows)
        new_total = baseline_total - monthly
        result = {
            "name": scenario.name[:60] or "Scenario",
            "rows": rows,
            "current_total_minor": baseline_total,
            "new_total_minor": new_total,
            "monthly_savings_minor": monthly,
            "annual_savings_minor": monthly * 12,
            "warnings": warnings,
            "explanation": (
                f"Monthly savings = current ({money(baseline_total)}) - new ({money(new_total)}) = {money(monthly)}. "
                f"Annual estimate assumes this monthly change continues for 12 months: {money(monthly)} x 12 = "
                f"{money(monthly * 12)}."
            ),
        }
        if overall_budget:
            result["budget"] = {
                "budget_minor": overall_budget.amount_minor,
                "remaining_current_minor": overall_budget.amount_minor - baseline_total,
                "remaining_new_minor": overall_budget.amount_minor - new_total,
            }
        if goal is not None:
            remaining = goal_info["remaining_minor"]
            current_rate = goal_info["recent_monthly_contribution_minor"]
            with_savings = current_rate + max(monthly, 0)
            months_needed = math.ceil(remaining / with_savings) if with_savings > 0 and remaining > 0 else (0 if remaining == 0 else None)
            result["goal"] = {
                "goal_id": goal.id, "name": goal.name, "remaining_minor": remaining,
                "required_monthly_minor": goal_info["required_monthly_minor"],
                "current_monthly_contribution_minor": current_rate,
                "monthly_with_savings_minor": with_savings,
                "months_to_goal": months_needed,
                "estimated_completion": add_months(today, months_needed).isoformat() if months_needed else None,
                "meets_target_date": (
                    goal_info["required_monthly_minor"] is not None and with_savings >= goal_info["required_monthly_minor"]
                ),
                "assumption": "Assumes all simulated savings are contributed to this goal each month, in addition "
                              "to your recent average contributions.",
            }
        results.append(result)

    best = max(results, key=lambda r: r["monthly_savings_minor"])
    return {
        "baseline": {**info, "total_minor": baseline_total,
                     "categories": [{"category": k, "category_name": names.get(k, k), "amount_minor": v}
                                    for k, v in sorted(baseline.items(), key=lambda kv: -kv[1])]},
        "scenarios": results,
        "best_scenario": best["name"] if len(results) > 1 else None,
        "disclaimer": "Simulation only. No transactions are created or changed. Estimates assume your baseline "
                      "spending pattern continues.",
    }


def required_reduction(repo: Repository, prefs: Preferences, *, goal_id: str | None, target_minor: int | None,
                       months: int | None, baseline_mode: str) -> dict:
    """How much monthly spending must fall to save a given amount in time."""
    today = today_in(prefs.timezone)
    if goal_id:
        goal = get_goal(repo, prefs.user_id, goal_id)
        metrics = goal_metrics(goal, today)
        amount = metrics["remaining_minor"]
        if metrics["completed"]:
            return {"goal_completed": True, "required_monthly_minor": 0,
                    "message": f"'{goal.name}' is already complete."}
        if not goal.target_date or goal.target_date <= today:
            raise ValidationFailed("The goal needs a future target date to calculate a monthly requirement.")
        n_months = max(1, math.ceil((goal.target_date - today).days / 30.4375))
        label = goal.name
    else:
        if not target_minor or target_minor <= 0 or not months or not (1 <= months <= 600):
            raise ValidationFailed("Provide a positive target amount and a number of months (1-600).")
        amount, n_months, label = target_minor, months, "your target"
    required = divide(amount, n_months)
    start = month_bounds(shift_month(month_key(today), -3))[0]
    baseline, info = compute_baseline(repo.list_expenses(prefs.user_id, start, today), baseline_mode, today)
    total = sum(baseline.values())
    names = category_names(prefs)
    pct = float(Decimal(required) / Decimal(total) * 100) if total else None
    return {
        "goal_completed": False,
        "label": label,
        "amount_minor": amount,
        "months": n_months,
        "required_monthly_minor": required,
        "baseline_total_minor": total,
        "baseline": info,
        "required_reduction_pct": round(pct, 1) if pct is not None else None,
        "feasible": pct is not None and pct <= 100,
        "per_category_if_even": [
            {"category": k, "category_name": names.get(k, k), "amount_minor": v,
             "reduction_minor": scale(v, Decimal(str(min(pct, 100))) / 100) if pct is not None else None}
            for k, v in sorted(baseline.items(), key=lambda kv: -kv[1])
        ],
        "explanation": f"{format_money(amount, prefs.currency)} over {n_months} month(s) requires saving "
                       f"{format_money(required, prefs.currency)} per month.",
    }
