"""Persistent domain records shared by services and repositories.

These are storage-agnostic: the SQLite and DynamoDB repositories both read and
write these exact shapes. API request/response schemas live in app.api.schemas.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.domain.dates import utc_now


def new_id() -> str:
    return uuid.uuid4().hex


class User(BaseModel):
    id: str
    email: str
    name: str
    password_hash: str = ""
    created_at: dt.datetime = Field(default_factory=utc_now)


class Expense(BaseModel):
    id: str = Field(default_factory=new_id)
    user_id: str
    amount_minor: int
    date: dt.date
    category: str
    description: str
    merchant: str | None = None
    payment_method: str = "upi"
    notes: str | None = None
    receipt_id: str | None = None
    is_demo: bool = False
    created_at: dt.datetime = Field(default_factory=utc_now)
    updated_at: dt.datetime = Field(default_factory=utc_now)


class Budget(BaseModel):
    """A recurring monthly budget.

    ``category`` None means the overall monthly budget. A budget applies to
    every month from ``effective_from`` up to ``effective_to`` (inclusive, or
    open-ended). Editing a budget that already applied to past months creates
    a new version so historical budget performance stays accurate.
    """

    id: str = Field(default_factory=new_id)
    user_id: str
    category: str | None = None
    amount_minor: int
    effective_from: str  # YYYY-MM
    effective_to: str | None = None  # YYYY-MM inclusive
    is_demo: bool = False
    created_at: dt.datetime = Field(default_factory=utc_now)
    updated_at: dt.datetime = Field(default_factory=utc_now)


class BudgetAlertEvent(BaseModel):
    """Records that a threshold was crossed, so it is only reported once."""

    user_id: str
    month: str
    budget_key: str  # category id or OVERALL_BUDGET_KEY
    threshold: int
    spent_minor: int
    budget_minor: int
    created_at: dt.datetime = Field(default_factory=utc_now)


class GoalContribution(BaseModel):
    id: str = Field(default_factory=new_id)
    amount_minor: int  # positive = contribution, negative = withdrawal
    date: dt.date
    note: str | None = None
    # "starting_balance" = amount already saved when the goal was created (not part of the saving pace)
    kind: Literal["contribution", "starting_balance"] = "contribution"
    created_at: dt.datetime = Field(default_factory=utc_now)


class Goal(BaseModel):
    id: str = Field(default_factory=new_id)
    user_id: str
    name: str
    target_minor: int
    saved_minor: int = 0
    target_date: dt.date | None = None
    archived: bool = False
    contributions: list[GoalContribution] = Field(default_factory=list)
    is_demo: bool = False
    created_at: dt.datetime = Field(default_factory=utc_now)
    updated_at: dt.datetime = Field(default_factory=utc_now)


AlertStatus = Literal["open", "reviewed", "legitimate", "dismissed"]
Severity = Literal["low", "medium", "high"]


class AnomalyAlert(BaseModel):
    id: str = Field(default_factory=new_id)
    user_id: str
    expense_id: str
    rule: str
    dedup_key: str
    severity: Severity
    reason: str
    comparison: dict[str, Any] = Field(default_factory=dict)
    detected_at: dt.datetime = Field(default_factory=utc_now)
    status: AlertStatus = "open"
    status_updated_at: dt.datetime | None = None
    note: str | None = None
    is_demo: bool = False


ReceiptStatus = Literal["pending_upload", "uploaded", "processed", "failed", "confirmed"]


class Receipt(BaseModel):
    id: str = Field(default_factory=new_id)
    user_id: str
    storage_key: str
    content_type: str
    size_bytes: int = 0
    status: ReceiptStatus = "uploaded"
    extracted: dict[str, Any] | None = None
    error: str | None = None
    expense_id: str | None = None
    uploaded_at: dt.datetime = Field(default_factory=utc_now)
    processed_at: dt.datetime | None = None


class CustomCategory(BaseModel):
    id: str
    name: str


class Preferences(BaseModel):
    user_id: str
    display_name: str | None = None
    currency: str = "INR"
    timezone: str = "Asia/Kolkata"
    budget_thresholds: list[int] = Field(default_factory=lambda: [75, 90, 100])
    anomaly_sensitivity: Literal["conservative", "balanced", "sensitive"] = "balanced"
    custom_categories: list[CustomCategory] = Field(default_factory=list)
    updated_at: dt.datetime = Field(default_factory=utc_now)
