"""Request and response schemas for the HTTP API (also drive the OpenAPI docs)."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.money import MAX_AMOUNT_MINOR


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ---- auth ----
class RegisterIn(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        import re

        v = v.lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
            raise ValueError("Enter a valid email address")
        return v


class LoginIn(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordIn(StrictModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


# ---- expenses ----
class ExpenseIn(StrictModel):
    amount_minor: int = Field(gt=0, le=MAX_AMOUNT_MINOR, description="Amount in minor units (paise for INR)")
    date: dt.date
    category: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=1, max_length=120)
    merchant: str | None = Field(default=None, max_length=80)
    payment_method: str = Field(default="upi", max_length=20)
    notes: str | None = Field(default=None, max_length=500)
    receipt_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")


class ExpenseOut(BaseModel):
    id: str
    amount_minor: int
    date: dt.date
    category: str
    description: str
    merchant: str | None
    payment_method: str
    notes: str | None
    receipt_id: str | None
    is_demo: bool
    created_at: dt.datetime
    updated_at: dt.datetime


class ExpensePage(BaseModel):
    items: list[ExpenseOut]
    total_count: int
    total_amount_minor: int
    page: int
    page_size: int
    total_pages: int


class ExpenseMutationOut(BaseModel):
    expense: ExpenseOut
    new_anomalies: int = 0
    budget_alerts: list[dict] = []


# ---- budgets ----
class BudgetIn(StrictModel):
    category: str | None = Field(default=None, max_length=40, description="Omit or null for the overall budget")
    amount_minor: int = Field(ge=0, le=MAX_AMOUNT_MINOR)


class BudgetUpdateIn(StrictModel):
    amount_minor: int = Field(ge=0, le=MAX_AMOUNT_MINOR)


# ---- goals ----
class GoalIn(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    target_minor: int = Field(gt=0, le=MAX_AMOUNT_MINOR)
    saved_minor: int = Field(default=0, ge=0, le=MAX_AMOUNT_MINOR)
    target_date: dt.date | None = None


class GoalUpdateIn(StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    target_minor: int | None = Field(default=None, gt=0, le=MAX_AMOUNT_MINOR)
    target_date: dt.date | None = None
    clear_target_date: bool = False
    archived: bool | None = None


class ContributionIn(StrictModel):
    amount_minor: int = Field(ge=-MAX_AMOUNT_MINOR, le=MAX_AMOUNT_MINOR)
    date: dt.date | None = None
    note: str | None = Field(default=None, max_length=200)


# ---- anomalies ----
class ReviewIn(StrictModel):
    action: Literal["reviewed", "legitimate", "dismissed", "open"]
    note: str | None = Field(default=None, max_length=300)


# ---- simulations ----
class AdjustmentIn(StrictModel):
    category: str = Field(min_length=1, max_length=40)
    mode: Literal["percent", "amount", "target"]
    value: Decimal = Field(description="Percent (0-100) for 'percent'; minor units for 'amount' and 'target'")


class ScenarioIn(StrictModel):
    name: str = Field(default="Scenario", max_length=60)
    adjustments: list[AdjustmentIn] = Field(min_length=1, max_length=20)


class SimulationIn(StrictModel):
    baseline: Literal["last_month", "avg_3_months", "current_month_projection"] = "avg_3_months"
    scenarios: list[ScenarioIn] = Field(min_length=1, max_length=4)
    goal_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")


class RequiredReductionIn(StrictModel):
    goal_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    target_minor: int | None = Field(default=None, gt=0, le=MAX_AMOUNT_MINOR)
    months: int | None = Field(default=None, ge=1, le=600)
    baseline: Literal["last_month", "avg_3_months", "current_month_projection"] = "avg_3_months"


# ---- receipts ----
class PresignIn(StrictModel):
    content_type: Literal["image/jpeg", "image/png", "image/webp"]
    size_bytes: int = Field(gt=0)


class ReceiptConfirmIn(ExpenseIn):
    receipt_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")


# ---- assistant ----
class AssistantQueryIn(StrictModel):
    question: str = Field(min_length=1, max_length=500)


# ---- preferences ----
class PreferencesIn(StrictModel):
    display_name: str | None = Field(default=None, max_length=80)
    currency: str | None = Field(default=None, max_length=3)
    timezone: str | None = Field(default=None, max_length=64)
    budget_thresholds: list[int] | None = Field(default=None, max_length=5)
    anomaly_sensitivity: Literal["conservative", "balanced", "sensitive"] | None = None


class CategoryIn(StrictModel):
    name: str = Field(min_length=1, max_length=40)


class DeleteAccountIn(StrictModel):
    confirm: Literal["DELETE"]
    password: str | None = Field(default=None, max_length=128)


class Message(BaseModel):
    message: str
    details: Any = None
