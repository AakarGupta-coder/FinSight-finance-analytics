"""Expense management: validation, CRUD, filtering, sorting and pagination."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from app.domain.categories import PAYMENT_METHOD_IDS
from app.domain.dates import today_in, utc_now
from app.domain.models import Expense, Preferences
from app.domain.money import MAX_AMOUNT_MINOR
from app.errors import NotFound, ValidationFailed
from app.repositories.base import Repository
from app.services.preferences import category_ids

MIN_DATE = dt.date(2000, 1, 1)
SORT_FIELDS = {"date", "amount", "category", "merchant", "description", "created_at"}


@dataclass
class ExpenseData:
    amount_minor: int
    date: dt.date
    category: str
    description: str
    merchant: str | None = None
    payment_method: str = "upi"
    notes: str | None = None
    receipt_id: str | None = None


def _clean(text: str | None, limit: int) -> str | None:
    if text is None:
        return None
    text = " ".join(text.split())
    return text[:limit] if text else None


def validate_expense(data: ExpenseData, prefs: Preferences) -> ExpenseData:
    errors = []
    if not isinstance(data.amount_minor, int) or data.amount_minor <= 0:
        errors.append({"field": "amount_minor", "message": "Amount must be greater than zero."})
    elif data.amount_minor > MAX_AMOUNT_MINOR:
        errors.append({"field": "amount_minor", "message": "Amount is unrealistically large."})
    today = today_in(prefs.timezone)
    if data.date < MIN_DATE:
        errors.append({"field": "date", "message": "Date must be on or after 1 Jan 2000."})
    elif data.date > today:
        errors.append({"field": "date", "message": "Date cannot be in the future."})
    if data.category not in category_ids(prefs):
        errors.append({"field": "category", "message": "Unknown category."})
    if data.payment_method not in PAYMENT_METHOD_IDS:
        errors.append({"field": "payment_method", "message": "Unknown payment method."})
    description = _clean(data.description, 120)
    if not description:
        errors.append({"field": "description", "message": "Description is required."})
    if errors:
        raise ValidationFailed(errors[0]["message"], details=errors)
    data.description = description  # type: ignore[assignment]
    data.merchant = _clean(data.merchant, 80)
    data.notes = _clean(data.notes, 500)
    return data


def create_expense(repo: Repository, prefs: Preferences, data: ExpenseData, *, is_demo: bool = False) -> Expense:
    data = validate_expense(data, prefs)
    if data.receipt_id and not repo.get_receipt(prefs.user_id, data.receipt_id):
        raise ValidationFailed("Receipt not found.")
    expense = Expense(user_id=prefs.user_id, is_demo=is_demo, **data.__dict__)
    repo.put_expense(expense)
    return expense


def get_expense(repo: Repository, user_id: str, expense_id: str) -> Expense:
    expense = repo.get_expense(user_id, expense_id)
    if not expense:
        raise NotFound("Transaction not found.")
    return expense


def update_expense(repo: Repository, prefs: Preferences, expense_id: str, data: ExpenseData) -> Expense:
    existing = get_expense(repo, prefs.user_id, expense_id)
    data = validate_expense(data, prefs)
    if data.receipt_id and data.receipt_id != existing.receipt_id:
        if not repo.get_receipt(prefs.user_id, data.receipt_id):
            raise ValidationFailed("Receipt not found.")
    updated = existing.model_copy(update={**data.__dict__, "updated_at": utc_now()})
    repo.put_expense(updated)
    return updated


def delete_expense(repo: Repository, user_id: str, expense_id: str) -> Expense:
    expense = get_expense(repo, user_id, expense_id)
    repo.delete_expense(user_id, expense_id)
    # Remove alerts that referenced this transaction; they no longer apply.
    for alert in repo.list_alerts(user_id):
        if alert.expense_id == expense_id:
            repo.delete_alert(user_id, alert.id)
    if expense.receipt_id:
        receipt = repo.get_receipt(user_id, expense.receipt_id)
        if receipt and receipt.expense_id == expense_id:
            receipt.expense_id = None
            receipt.status = "processed" if receipt.extracted else "uploaded"
            repo.put_receipt(receipt)
    return expense


@dataclass
class ExpenseFilters:
    start: dt.date | None = None
    end: dt.date | None = None
    categories: list[str] = field(default_factory=list)
    payment_methods: list[str] = field(default_factory=list)
    search: str | None = None
    min_amount_minor: int | None = None
    max_amount_minor: int | None = None
    sort: str = "date"
    order: str = "desc"
    page: int = 1
    page_size: int = 20


def filter_expenses(expenses: list[Expense], f: ExpenseFilters) -> list[Expense]:
    result = expenses
    if f.start:
        result = [e for e in result if e.date >= f.start]
    if f.end:
        result = [e for e in result if e.date <= f.end]
    if f.categories:
        wanted = set(f.categories)
        result = [e for e in result if e.category in wanted]
    if f.payment_methods:
        wanted = set(f.payment_methods)
        result = [e for e in result if e.payment_method in wanted]
    if f.min_amount_minor is not None:
        result = [e for e in result if e.amount_minor >= f.min_amount_minor]
    if f.max_amount_minor is not None:
        result = [e for e in result if e.amount_minor <= f.max_amount_minor]
    if f.search and f.search.strip():
        terms = f.search.lower().split()

        def matches(e: Expense) -> bool:
            haystack = " ".join(filter(None, [e.description, e.merchant, e.notes, e.category])).lower()
            return all(term in haystack for term in terms)

        result = [e for e in result if matches(e)]
    return result


def sort_expenses(expenses: list[Expense], sort: str, order: str) -> list[Expense]:
    if sort not in SORT_FIELDS:
        raise ValidationFailed(f"Cannot sort by {sort!r}.")
    reverse = order != "asc"
    keyfuncs = {
        "date": lambda e: (e.date, e.created_at),
        "amount": lambda e: (e.amount_minor, e.date),
        "category": lambda e: (e.category, e.date),
        "merchant": lambda e: ((e.merchant or "").lower(), e.date),
        "description": lambda e: (e.description.lower(), e.date),
        "created_at": lambda e: e.created_at,
    }
    return sorted(expenses, key=keyfuncs[sort], reverse=reverse)


def query_expenses(repo: Repository, user_id: str, f: ExpenseFilters) -> dict:
    if f.start and f.end and f.start > f.end:
        raise ValidationFailed("Start date must be on or before end date.")
    if not (1 <= f.page_size <= 100):
        raise ValidationFailed("page_size must be between 1 and 100.")
    if f.page < 1:
        raise ValidationFailed("page must be 1 or greater.")
    expenses = repo.list_expenses(user_id, f.start, f.end)
    matched = sort_expenses(filter_expenses(expenses, f), f.sort, f.order)
    total = len(matched)
    offset = (f.page - 1) * f.page_size
    return {
        "items": matched[offset : offset + f.page_size],
        "total_count": total,
        "total_amount_minor": sum(e.amount_minor for e in matched),
        "page": f.page,
        "page_size": f.page_size,
        "total_pages": max(1, -(-total // f.page_size)),
    }
