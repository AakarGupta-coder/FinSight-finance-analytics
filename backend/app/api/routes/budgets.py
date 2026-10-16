from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import UserContext, get_context
from app.api.schemas import BudgetIn, BudgetUpdateIn
from app.domain.dates import month_key, parse_month, today_in
from app.errors import ValidationFailed
from app.services import budgets as svc

router = APIRouter(prefix="/budgets", tags=["budgets"])


def _month(ctx: UserContext, month: str | None) -> str:
    if month is None:
        return month_key(today_in(ctx.prefs.timezone))
    try:
        parse_month(month)
    except ValueError as exc:
        raise ValidationFailed(str(exc)) from exc
    return month


@router.get("")
def overview(ctx: UserContext = Depends(get_context), month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$")):
    """Budget utilization for a month (defaults to the current month)."""
    return svc.month_overview(ctx.repo, ctx.prefs, _month(ctx, month))


@router.get("/history")
def history(ctx: UserContext = Depends(get_context), months: int = Query(default=6, ge=1, le=24)):
    return {"months": svc.history(ctx.repo, ctx.prefs, months)}


@router.post("", status_code=201)
def create(body: BudgetIn, ctx: UserContext = Depends(get_context)):
    budget = svc.create_budget(ctx.repo, ctx.prefs, body.category, body.amount_minor)
    return budget.model_dump(mode="json", exclude={"user_id"})


@router.put("/{budget_id}")
def update(budget_id: str, body: BudgetUpdateIn, ctx: UserContext = Depends(get_context)):
    budget = svc.update_budget(ctx.repo, ctx.prefs, budget_id, body.amount_minor)
    return budget.model_dump(mode="json", exclude={"user_id"})


@router.delete("/{budget_id}", status_code=204)
def delete(budget_id: str, ctx: UserContext = Depends(get_context)):
    svc.delete_budget(ctx.repo, ctx.prefs, budget_id)
    return Response(status_code=204)
