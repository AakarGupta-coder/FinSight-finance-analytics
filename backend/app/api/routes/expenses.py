from __future__ import annotations

import datetime as dt
import logging

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import UserContext, get_context
from app.api.schemas import ExpenseIn, ExpenseMutationOut, ExpenseOut, ExpensePage
from app.services import anomalies, budgets
from app.services import expenses as svc

router = APIRouter(prefix="/expenses", tags=["expenses"])
logger = logging.getLogger("app.expenses")


def _data(body: ExpenseIn) -> svc.ExpenseData:
    return svc.ExpenseData(**body.model_dump())


def _after_change(ctx: UserContext, expense) -> tuple[int, list[dict]]:
    """Run anomaly detection and budget threshold checks after a change.

    Failures here must never lose the user's saved transaction, so they are
    logged and skipped.
    """
    created, alerts = 0, []
    try:
        created = anomalies.scan_expense(ctx.repo, ctx.prefs, expense)
    except Exception:  # noqa: BLE001
        logger.exception("anomaly scan failed")
    try:
        alerts = budgets.check_alerts_for_date(ctx.repo, ctx.prefs, expense.date)
    except Exception:  # noqa: BLE001
        logger.exception("budget alert check failed")
    return created, alerts


@router.get("", response_model=ExpensePage)
def list_expenses(
    ctx: UserContext = Depends(get_context),
    start: dt.date | None = None,
    end: dt.date | None = None,
    category: list[str] = Query(default=[]),
    payment_method: list[str] = Query(default=[]),
    search: str | None = Query(default=None, max_length=100),
    min_amount_minor: int | None = Query(default=None, ge=0),
    max_amount_minor: int | None = Query(default=None, ge=0),
    sort: str = "date",
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    filters = svc.ExpenseFilters(start=start, end=end, categories=category, payment_methods=payment_method,
                                 search=search, min_amount_minor=min_amount_minor, max_amount_minor=max_amount_minor,
                                 sort=sort, order=order, page=page, page_size=page_size)
    return svc.query_expenses(ctx.repo, ctx.user_id, filters)


@router.post("", response_model=ExpenseMutationOut, status_code=201)
def create_expense(body: ExpenseIn, ctx: UserContext = Depends(get_context)):
    expense = svc.create_expense(ctx.repo, ctx.prefs, _data(body))
    created, alerts = _after_change(ctx, expense)
    return {"expense": expense, "new_anomalies": created, "budget_alerts": alerts}


@router.get("/{expense_id}", response_model=ExpenseOut)
def get_expense(expense_id: str, ctx: UserContext = Depends(get_context)):
    return svc.get_expense(ctx.repo, ctx.user_id, expense_id)


@router.put("/{expense_id}", response_model=ExpenseMutationOut)
def update_expense(expense_id: str, body: ExpenseIn, ctx: UserContext = Depends(get_context)):
    expense = svc.update_expense(ctx.repo, ctx.prefs, expense_id, _data(body))
    created, alerts = _after_change(ctx, expense)
    return {"expense": expense, "new_anomalies": created, "budget_alerts": alerts}


@router.delete("/{expense_id}", status_code=204)
def delete_expense(expense_id: str, ctx: UserContext = Depends(get_context)):
    expense = svc.delete_expense(ctx.repo, ctx.user_id, expense_id)
    try:
        anomalies.refresh_category_spikes(ctx.repo, ctx.prefs, expense.date)
    except Exception:  # noqa: BLE001
        logger.exception("spike refresh failed")
    return Response(status_code=204)
