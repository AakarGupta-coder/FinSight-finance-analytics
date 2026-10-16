"""Personal Finance Intelligence Engine.

Generates evidence-based insights from stored transactions using transparent,
deterministic rules. Each insight states its kind:

* fact           - directly observed in recorded data
* estimate       - a statistic derived from recorded data (e.g. an average)
* projection     - an extrapolation into the future; may not happen
* recommendation - a suggestion, with the calculation behind it
* data_gap       - an explanation that more data is needed

No insight is produced when the data needed to support it is missing.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict

from app.domain.categories import DISCRETIONARY_CATEGORIES, OVERALL_BUDGET_KEY
from app.domain.dates import (
    format_date,
    month_bounds,
    month_key,
    month_label,
    shift_month,
    short_month_label,
)
from app.domain.models import Budget, Expense, Goal, Preferences
from app.domain.money import divide, format_money, pct_change, percent, round_major, scale
from app.errors import ValidationFailed
from app.services.analytics import month_summary
from app.services.budgets import budgets_for_month, evaluate
from app.services.goals import goal_metrics
from app.services.preferences import category_names
from app.services.recurring import detect_recurring

SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2, "positive": 3}
KIND_ORDER = {"fact": 0, "projection": 1, "estimate": 2, "recommendation": 3, "data_gap": 4}
MIN_CHANGE_PCT = 20.0
MIN_CHANGE_SHARE_OF_TOTAL = 0.05
MIN_DAYS_FOR_PROJECTION = 5


def _txn_refs(expenses: list[Expense], limit: int = 5) -> list[dict]:
    top = sorted(expenses, key=lambda e: -e.amount_minor)[:limit]
    return [{"id": e.id, "date": e.date.isoformat(), "description": e.description,
             "amount_minor": e.amount_minor, "category": e.category} for e in top]


def _insight(id_: str, kind: str, severity: str, title: str, message: str, *, period: dict | None = None,
             calculation: str | None = None, values: dict | None = None, transactions: list[dict] | None = None,
             category: str | None = None, action: dict | None = None) -> dict:
    return {
        "id": id_, "kind": kind, "severity": severity, "title": title, "message": message,
        "category": category, "action": action,
        "evidence": {"period": period, "calculation": calculation, "values": values or {},
                     "transactions": transactions or []},
    }


def _sum_by_cat(expenses: list[Expense]) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for e in expenses:
        totals[e.category] += e.amount_minor
    return dict(totals)


def generate_insights(expenses: list[Expense], budgets: list[Budget], goals: list[Goal], prefs: Preferences,
                      month: str, today: dt.date) -> dict:
    if month > month_key(today):
        raise ValidationFailed("Insights are not available for future months.")
    names = category_names(prefs)
    money = lambda amount: format_money(amount, prefs.currency)  # noqa: E731
    approx = lambda amount: format_money(round_major(amount, prefs.currency), prefs.currency)  # noqa: E731
    insights: list[dict] = []

    start, end = month_bounds(month)
    summary = month_summary(expenses, month, today)
    period_end = dt.date.fromisoformat(summary["period_end"])
    is_current = summary["is_current_month"]
    period = {"start": start.isoformat(), "end": period_end.isoformat(),
              "label": f"{format_date(start)} - {format_date(period_end)}"}
    current = [e for e in expenses if start <= e.date <= period_end]
    cmp = summary["comparison_period"]
    cmp_start, cmp_end = dt.date.fromisoformat(cmp["start"]), dt.date.fromisoformat(cmp["end"])
    previous = [e for e in expenses if cmp_start <= e.date <= cmp_end]
    cmp_period = {"start": cmp["start"], "end": cmp["end"],
                  "label": f"{format_date(cmp_start)} - {format_date(cmp_end)}"}
    months_with_data = sorted({month_key(e.date) for e in expenses if e.date <= period_end})
    total = summary["total_minor"]

    # ---- data coverage ----
    if not current:
        insights.append(_insight(
            f"no-data-{month}", "data_gap", "info", f"No expenses recorded for {month_label(month)}",
            "Add transactions or scan a receipt to see insights for this month.", period=period))
    if len(months_with_data) < 2:
        insights.append(_insight(
            "history-needed", "data_gap", "info", "More history needed for comparisons",
            "Month-to-month comparisons and averages need records from at least two different months. "
            f"You currently have records for {len(months_with_data)} month(s).",
            values={"months_with_data": len(months_with_data)}))

    # ---- month over month (like-for-like period) ----
    prev_total = summary["previous_comparable_total_minor"]
    if current and prev_total > 0:
        change = summary["change_pct"]
        direction = "higher" if change > 0 else "lower"
        scope = "so far this month" if is_current else f"in {month_label(month)}"
        insights.append(_insight(
            f"mom-total-{month}", "fact", "warning" if change >= MIN_CHANGE_PCT else
            ("positive" if change <= -MIN_CHANGE_PCT else "info"),
            f"Spending is {abs(change):.0f}% {direction} than last month" if change else "Spending matches last month",
            f"You spent {money(total)} {scope}, compared with {money(prev_total)} during "
            f"{cmp_period['label']}.",
            period=period, calculation="(current - previous) / previous x 100",
            values={"current_minor": total, "previous_minor": prev_total, "change_pct": change,
                    "comparison_period": cmp_period}))
    elif current and len(months_with_data) >= 1 and prev_total == 0:
        insights.append(_insight(
            f"mom-missing-{month}", "data_gap", "info", "No previous-month data to compare",
            f"There are no recorded expenses during {cmp_period['label']}, so a month-to-month "
            "comparison is not possible.", period=cmp_period))

    # ---- category changes ----
    cur_by_cat, prev_by_cat = _sum_by_cat(current), _sum_by_cat(previous)
    changes = []
    for cat in set(cur_by_cat) | set(prev_by_cat):
        cur_amt, prev_amt = cur_by_cat.get(cat, 0), prev_by_cat.get(cat, 0)
        if cur_amt and prev_amt:
            pct = pct_change(cur_amt, prev_amt)
            if abs(pct) >= MIN_CHANGE_PCT and abs(cur_amt - prev_amt) >= MIN_CHANGE_SHARE_OF_TOTAL * prev_total:
                changes.append((cat, cur_amt, prev_amt, pct))
    increases = sorted([c for c in changes if c[3] > 0], key=lambda c: -(c[1] - c[2]))[:2]
    decreases = sorted([c for c in changes if c[3] < 0], key=lambda c: c[1] - c[2])[:1]
    for cat, cur_amt, prev_amt, pct in increases + decreases:
        up = pct > 0
        insights.append(_insight(
            f"cat-change-{cat}-{month}", "fact", "warning" if up else "positive",
            f"{names.get(cat, cat)} spending {'up' if up else 'down'} {abs(pct):.0f}%",
            f"{names.get(cat, cat)} expenditure is {abs(pct):.0f}% {'higher' if up else 'lower'} than the "
            f"previous month ({money(cur_amt)} vs {money(prev_amt)} for the same period).",
            period=period, category=cat, calculation="(current - previous) / previous x 100",
            values={"current_minor": cur_amt, "previous_minor": prev_amt, "change_pct": pct,
                    "comparison_period": cmp_period},
            transactions=_txn_refs([e for e in current if e.category == cat]),
            action={"label": "View transactions", "href": f"/transactions?category={cat}&start={start}&end={period_end}"}))

    for cat, cur_amt in cur_by_cat.items():
        if cat not in prev_by_cat and prev_total > 0 and total and cur_amt >= 0.1 * total:
            insights.append(_insight(
                f"cat-new-{cat}-{month}", "fact", "info", f"New spending in {names.get(cat, cat)}",
                f"You recorded {money(cur_amt)} in {names.get(cat, cat)} this period, with none in the "
                "same period last month.", period=period, category=cat,
                values={"current_minor": cur_amt, "previous_minor": 0},
                transactions=_txn_refs([e for e in current if e.category == cat])))

    # ---- category share / concentration ----
    if current and total:
        top_cat, top_amt = max(cur_by_cat.items(), key=lambda kv: kv[1])
        share = percent(top_amt, total)
        concentrated = share >= 50 and len(current) >= 5
        insights.append(_insight(
            f"top-share-{month}", "fact", "warning" if concentrated else "info",
            f"{names.get(top_cat, top_cat)} is your largest category",
            f"{names.get(top_cat, top_cat)} accounts for {share:.0f}% of your recorded expenses "
            f"({money(top_amt)} of {money(total)})."
            + (" Spending is heavily concentrated in one category." if concentrated else ""),
            period=period, category=top_cat, calculation="category total / month total x 100",
            values={"category_minor": top_amt, "total_minor": total, "share_pct": share},
            transactions=_txn_refs([e for e in current if e.category == top_cat])))

        insights.append(_insight(
            f"avg-daily-{month}", "estimate", "info", "Average daily spending",
            f"You spent an average of {approx(summary['average_daily_minor'])} per day across "
            f"{summary['days_elapsed']} day(s) and {len(current)} transaction(s).",
            period=period, calculation="total spent / days in period",
            values={"total_minor": total, "days": summary["days_elapsed"],
                    "average_daily_minor": summary["average_daily_minor"]}))

    # ---- average monthly spending over previous months ----
    prior_months = [shift_month(month, -i) for i in (1, 2, 3)]
    prior_totals = {}
    for m in prior_months:
        m_start, m_end = month_bounds(m)
        month_items = [e for e in expenses if m_start <= e.date <= m_end]
        if month_items:
            prior_totals[m] = sum(e.amount_minor for e in month_items)
    avg_monthly = None
    if len(prior_totals) >= 2:
        avg_monthly = divide(sum(prior_totals.values()), len(prior_totals))
        labels = ", ".join(short_month_label(m) for m in sorted(prior_totals))
        insights.append(_insight(
            f"avg-monthly-{month}", "estimate", "info", "Average monthly spending",
            f"Across {len(prior_totals)} previous month(s) with records ({labels}) you spent an average of "
            f"{approx(avg_monthly)} per month.",
            calculation="sum of monthly totals / number of months with records",
            values={"average_minor": avg_monthly, "months": {m: prior_totals[m] for m in sorted(prior_totals)}}))

    # ---- projections & budgets ----
    active_budgets = budgets_for_month(budgets, month)
    days = summary["days_elapsed"]
    projected = None
    if is_current and current and days >= MIN_DAYS_FOR_PROJECTION:
        projected = divide(total * end.day, days)
    overall = active_budgets.get(OVERALL_BUDGET_KEY)
    if overall and current:
        ev = evaluate(overall.amount_minor, total, prefs.budget_thresholds, month=month, today=today)
        if ev["status"] == "exceeded":
            insights.append(_insight(
                f"budget-exceeded-{month}", "fact", "critical", "Monthly budget exceeded",
                f"You have spent {money(total)}, which is {money(total - overall.amount_minor)} over your "
                f"{money(overall.amount_minor)} monthly budget.",
                period=period, calculation="spent - budget",
                values={"spent_minor": total, "budget_minor": overall.amount_minor},
                action={"label": "Review budgets", "href": "/budgets"}))
        elif projected is not None and projected > overall.amount_minor:
            remaining_days = end.day - today.day
            allowance = divide(max(overall.amount_minor - total, 0), remaining_days + 1)
            insights.append(_insight(
                f"budget-projection-{month}", "projection", "warning", "You may exceed your monthly budget",
                f"At your current pace of {approx(summary['average_daily_minor'])} per day, spending could reach "
                f"about {approx(projected)} by {format_date(end)}, above your {money(overall.amount_minor)} budget. "
                f"This is a projection, not a certainty.",
                period=period, calculation="spent so far / days elapsed x days in month",
                values={"spent_minor": total, "days_elapsed": days, "days_in_month": end.day,
                        "projected_minor": projected, "budget_minor": overall.amount_minor},
                action={"label": "Review budgets", "href": "/budgets"}))
            insights.append(_insight(
                f"budget-allowance-{month}", "recommendation", "info", "Daily limit to stay within budget",
                f"To stay within budget, keep spending to about {approx(allowance)} per day for the remaining "
                f"{remaining_days + 1} day(s) of the month (including today).",
                calculation="(budget - spent) / remaining days",
                values={"remaining_minor": overall.amount_minor - total, "remaining_days": remaining_days + 1,
                        "allowance_minor": allowance}))
        elif projected is not None:
            insights.append(_insight(
                f"budget-on-track-{month}", "projection", "positive", "On track for your monthly budget",
                f"At your current pace, spending is projected at about {approx(projected)}, within your "
                f"{money(overall.amount_minor)} budget.",
                period=period, calculation="spent so far / days elapsed x days in month",
                values={"projected_minor": projected, "budget_minor": overall.amount_minor}))
    elif projected is not None and avg_monthly:
        diff_pct = pct_change(projected, avg_monthly)
        if diff_pct is not None and abs(diff_pct) >= MIN_CHANGE_PCT:
            insights.append(_insight(
                f"pace-vs-average-{month}", "projection", "warning" if diff_pct > 0 else "positive",
                "This month's pace differs from your average",
                f"At the current pace this month may total about {approx(projected)}, "
                f"{abs(diff_pct):.0f}% {'above' if diff_pct > 0 else 'below'} your recent monthly average of "
                f"{approx(avg_monthly)}. This is a projection based on {days} day(s) of data.",
                calculation="spent so far / days elapsed x days in month",
                values={"projected_minor": projected, "average_minor": avg_monthly}))

    category_alerts = 0
    for key, budget in active_budgets.items():
        if key == OVERALL_BUDGET_KEY or category_alerts >= 3:
            continue
        spent = cur_by_cat.get(key, 0)
        ev = evaluate(budget.amount_minor, spent, prefs.budget_thresholds, month=month, today=today)
        cat_name = names.get(key, key)
        if ev["status"] == "exceeded":
            category_alerts += 1
            insights.append(_insight(
                f"cat-budget-exceeded-{key}-{month}", "fact", "critical", f"{cat_name} budget exceeded",
                f"{cat_name} spending is {money(spent)} against a budget of {money(budget.amount_minor)}.",
                category=key, period=period, values={"spent_minor": spent, "budget_minor": budget.amount_minor},
                transactions=_txn_refs([e for e in current if e.category == key])))
        elif ev["projected_overrun"]:
            category_alerts += 1
            insights.append(_insight(
                f"cat-budget-projection-{key}-{month}", "projection", "warning", f"{cat_name} budget at risk",
                f"At the current pace {cat_name} spending may reach about {approx(ev['projected_spend_minor'])}, "
                f"above its {money(budget.amount_minor)} budget ({ev['utilization_pct']:.0f}% used so far).",
                category=key, period=period, calculation="spent so far / days elapsed x days in month",
                values={"spent_minor": spent, "budget_minor": budget.amount_minor,
                        "projected_minor": ev["projected_spend_minor"]}))

    # ---- recurring payments ----
    lookback_start = shift_month(month, -6) + "-01"
    recurring = detect_recurring([e for e in expenses if lookback_start <= e.date.isoformat() <= period_end.isoformat()],
                                 period_end)
    active_recurring = [r for r in recurring if r["active"]]
    if active_recurring:
        monthly_total = sum(r["monthly_equivalent_minor"] for r in active_recurring)
        insights.append(_insight(
            f"recurring-{month}", "estimate", "info", f"{len(active_recurring)} recurring payment(s) detected",
            f"Recurring payments such as {', '.join(r['name'] for r in active_recurring[:3])} add up to about "
            f"{approx(monthly_total)} per month.",
            calculation="sum of typical amount x payments per month for each active recurring series",
            values={"monthly_total_minor": monthly_total,
                    "series": [{k: r[k] for k in ("name", "cadence", "typical_amount_minor", "occurrences",
                                                    "confidence", "next_expected")} for r in active_recurring]}))
    window_start = (start - dt.timedelta(days=35)).isoformat()
    for r in active_recurring:
        # "New" = the series started recently (second payment confirms it recurs).
        if r["first_date"] >= window_start and start.isoformat() <= r["last_date"]:
            cat = r["category"]
            # Compare the category in the month the series started with the month before it.
            started = month_key(dt.date.fromisoformat(r["first_date"]))
            s_start, s_end = month_bounds(started)
            b_start, b_end = month_bounds(shift_month(started, -1))
            s_end = min(s_end, period_end)
            after_amt = sum(e.amount_minor for e in expenses if e.category == cat and s_start <= e.date <= s_end)
            before_amt = sum(e.amount_minor for e in expenses if e.category == cat and b_start <= e.date <= b_end)
            increased = after_amt > before_amt and before_amt > 0
            insights.append(_insight(
                f"recurring-new-{r['key']}-{month}", "fact", "info", f"New recurring payment: {r['name']}",
                f"A new recurring payment to {r['name']} ({money(r['typical_amount_minor'])}, {r['cadence']}) "
                f"started on {format_date(dt.date.fromisoformat(r['first_date']))}."
                + (f" Your {names.get(cat, cat)} expenses increased from {money(before_amt)} in "
                   f"{month_label(shift_month(started, -1))} to {money(after_amt)} in {month_label(started)}"
                   f"{' (so far)' if s_end < month_bounds(started)[1] else ''}." if increased else ""),
                category=cat, period=period,
                values={"occurrences": r["occurrences"], "typical_amount_minor": r["typical_amount_minor"],
                        "category_before_minor": before_amt, "category_after_minor": after_amt}))

    # ---- savings goals ----
    for goal in goals:
        if goal.archived:
            continue
        metrics = goal_metrics(goal, today)
        if metrics["status"] == "behind" and metrics["required_monthly_minor"]:
            insights.append(_insight(
                f"goal-behind-{goal.id}", "projection", "warning", f"'{goal.name}' is behind schedule",
                f"Reaching {money(goal.target_minor)} by {format_date(goal.target_date)} needs about "
                f"{approx(metrics['required_monthly_minor'])} per month, but contributions over the last 90 days "
                f"average {approx(metrics['recent_monthly_contribution_minor'])} per month.",
                calculation="remaining / months until target date",
                values={"remaining_minor": metrics["remaining_minor"],
                        "required_monthly_minor": metrics["required_monthly_minor"],
                        "recent_monthly_minor": metrics["recent_monthly_contribution_minor"]},
                action={"label": "Open goals", "href": "/goals"}))
        elif metrics["status"] == "completed":
            insights.append(_insight(
                f"goal-done-{goal.id}", "fact", "positive", f"Goal reached: {goal.name}",
                f"You have saved {money(goal.saved_minor)} towards a {money(goal.target_minor)} target.",
                values={"saved_minor": goal.saved_minor, "target_minor": goal.target_minor}))

    # ---- recommendation from the largest discretionary increase ----
    discretionary_up = [c for c in increases if c[0] in DISCRETIONARY_CATEGORIES]
    if discretionary_up:
        cat, cur_amt, _, pct = discretionary_up[0]
        # Base the saving on the category's typical month, not an extrapolation of
        # this month (a single large purchase would otherwise inflate it).
        monthly_totals = []
        for m in prior_months:
            m_start, m_end = month_bounds(m)
            total_m = sum(e.amount_minor for e in expenses if e.category == cat and m_start <= e.date <= m_end)
            if total_m:
                monthly_totals.append(total_m)
        if len(monthly_totals) >= 2:
            base, base_label = divide(sum(monthly_totals), len(monthly_totals)), "your recent monthly average of"
        else:
            base, base_label = cur_amt, "this period's"
        saving = scale(base, 0.15)
        insights.append(_insight(
            f"rec-reduce-{cat}-{month}", "recommendation", "info", f"Consider reviewing {names.get(cat, cat)}",
            f"{names.get(cat, cat)} rose {pct:.0f}%. Reducing it by 15% from {base_label} {approx(base)} would "
            f"save roughly {approx(saving)} per month, or {approx(saving * 12)} per year if sustained for 12 months.",
            category=cat, calculation="typical monthly category spend x 15%; annual = monthly x 12",
            values={"monthly_base_minor": base, "monthly_saving_minor": saving, "annual_saving_minor": saving * 12},
            action={"label": "Try in simulator", "href": f"/simulator?category={cat}&percent=15"}))

    insights.sort(key=lambda i: (SEVERITY_ORDER[i["severity"]], KIND_ORDER[i["kind"]]))
    return {
        "month": month,
        "generated_for": period,
        "currency": prefs.currency,
        "coverage": {"months_with_data": len(months_with_data),
                     "first_month": months_with_data[0] if months_with_data else None,
                     "transactions_in_period": len(current)},
        "recurring": recurring,
        "insights": insights,
    }
