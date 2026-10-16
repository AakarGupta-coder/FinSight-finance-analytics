"""Dashboard, analytics and intelligence (insights) endpoints."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Query

from app.api.deps import UserContext, get_context
from app.domain.dates import add_months, month_bounds, month_key, parse_month, shift_month, today_in
from app.errors import ValidationFailed
from app.services import analytics, budgets
from app.services.anomalies import list_alerts_with_expenses
from app.services.goals import serialize_goal
from app.services.insights import generate_insights
from app.services.preferences import category_names

router = APIRouter(tags=["analytics"])


def _month(ctx: UserContext, month: str | None) -> str:
    current = month_key(today_in(ctx.prefs.timezone))
    if month is None:
        return current
    try:
        parse_month(month)
    except ValueError as exc:
        raise ValidationFailed(str(exc)) from exc
    if month > current:
        raise ValidationFailed("Month cannot be in the future.")
    return month


def _insights(ctx: UserContext, month: str) -> dict:
    today = today_in(ctx.prefs.timezone)
    start = month_bounds(shift_month(month, -6))[0]
    _, end = month_bounds(month)
    expenses = ctx.repo.list_expenses(ctx.user_id, start, min(end, today))
    return generate_insights(expenses, ctx.repo.list_budgets(ctx.user_id), ctx.repo.list_goals(ctx.user_id),
                             ctx.prefs, month, today)


@router.get("/dashboard")
def dashboard(ctx: UserContext = Depends(get_context), month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$")):
    """Everything the dashboard shows, computed from one consistent dataset and date range."""
    month = _month(ctx, month)
    today = today_in(ctx.prefs.timezone)
    start, end = month_bounds(month)
    history_start = month_bounds(shift_month(month, -5))[0]
    expenses = ctx.repo.list_expenses(ctx.user_id, history_start, min(end, today))
    month_expenses = [e for e in expenses if start <= e.date <= end]
    names = category_names(ctx.prefs)
    recent = sorted(month_expenses, key=lambda e: (e.date, e.created_at), reverse=True)[:6]
    goals = [serialize_goal(g, today) for g in ctx.repo.list_goals(ctx.user_id) if not g.archived]
    upcoming = sorted([g for g in goals if g["target_date"] and not g["completed"]], key=lambda g: g["target_date"])[:3]
    alerts = [a for a in list_alerts_with_expenses(ctx.repo, ctx.prefs, "open")]
    insight_data = _insights(ctx, month)
    return {
        "month": month,
        "currency": ctx.prefs.currency,
        "summary": analytics.month_summary(expenses, month, today),
        "budget": budgets.month_overview(ctx.repo, ctx.prefs, month),
        "categories": analytics.category_breakdown(month_expenses, names),
        "daily": analytics.daily_series(month_expenses, start, min(end, today) if month == month_key(today) else end),
        "monthly": analytics.monthly_series(expenses, [shift_month(month, -i) for i in range(5, -1, -1)]),
        "recent_transactions": [e.model_dump(mode="json", exclude={"user_id"}) for e in recent],
        "insights": insight_data["insights"][:4],
        "anomalies": {"open_count": len(alerts), "items": alerts[:3]},
        "goals": sorted(goals, key=lambda g: -g["progress_pct"])[:4],
        "upcoming_targets": upcoming,
        "category_names": names,
    }


@router.get("/analytics")
def range_analytics(ctx: UserContext = Depends(get_context), start: dt.date | None = None, end: dt.date | None = None):
    today = today_in(ctx.prefs.timezone)
    end = end or today
    start = start or add_months(end, -3) + dt.timedelta(days=1)
    return analytics.range_analytics(ctx.repo, ctx.prefs, start, end)


@router.get("/insights")
def insights(ctx: UserContext = Depends(get_context), month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$")):
    return _insights(ctx, _month(ctx, month))
