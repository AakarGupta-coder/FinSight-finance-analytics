"""Data-access contract.

Services depend only on this interface. Two implementations exist:
``SQLiteRepository`` for local development and ``DynamoDBRepository`` for AWS.

Every user-scoped method takes ``user_id`` explicitly and implementations
must scope all reads and writes to that user (partition key in DynamoDB,
WHERE clause in SQLite). The user id always comes from the validated
authentication context, never from client input.
"""

from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod

from app.domain.models import (
    AnomalyAlert,
    Budget,
    BudgetAlertEvent,
    Expense,
    Goal,
    Preferences,
    Receipt,
    User,
)


class Repository(ABC):
    # ---- users (local authentication only) ----
    @abstractmethod
    def create_user(self, user: User) -> None:
        """Create a user. Raises Conflict if the email is taken."""

    @abstractmethod
    def get_user(self, user_id: str) -> User | None: ...

    @abstractmethod
    def get_user_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    def update_user(self, user: User) -> None: ...

    # ---- expenses ----
    @abstractmethod
    def put_expense(self, expense: Expense) -> None: ...

    @abstractmethod
    def get_expense(self, user_id: str, expense_id: str) -> Expense | None: ...

    @abstractmethod
    def delete_expense(self, user_id: str, expense_id: str) -> bool: ...

    @abstractmethod
    def list_expenses(
        self, user_id: str, start: dt.date | None = None, end: dt.date | None = None
    ) -> list[Expense]:
        """Expenses with start <= date <= end (bounds optional), any order."""

    # ---- budgets ----
    @abstractmethod
    def put_budget(self, budget: Budget) -> None: ...

    @abstractmethod
    def get_budget(self, user_id: str, budget_id: str) -> Budget | None: ...

    @abstractmethod
    def delete_budget(self, user_id: str, budget_id: str) -> bool: ...

    @abstractmethod
    def list_budgets(self, user_id: str) -> list[Budget]: ...

    @abstractmethod
    def record_budget_alert_event(self, event: BudgetAlertEvent) -> bool:
        """Insert unless (user, month, budget_key, threshold) exists. Returns True if inserted."""

    @abstractmethod
    def list_budget_alert_events(self, user_id: str, month: str | None = None) -> list[BudgetAlertEvent]: ...

    @abstractmethod
    def delete_budget_alert_events(self, user_id: str, month: str | None = None, budget_key: str | None = None) -> int:
        """Remove recorded threshold events (re-arms alerts), optionally for one month / budget."""

    # ---- goals ----
    @abstractmethod
    def put_goal(self, goal: Goal) -> None: ...

    @abstractmethod
    def get_goal(self, user_id: str, goal_id: str) -> Goal | None: ...

    @abstractmethod
    def delete_goal(self, user_id: str, goal_id: str) -> bool: ...

    @abstractmethod
    def list_goals(self, user_id: str) -> list[Goal]: ...

    # ---- anomaly alerts ----
    @abstractmethod
    def create_alert_if_absent(self, alert: AnomalyAlert) -> bool:
        """Insert unless an alert with the same dedup_key exists for the user."""

    @abstractmethod
    def put_alert(self, alert: AnomalyAlert) -> None: ...

    @abstractmethod
    def get_alert(self, user_id: str, alert_id: str) -> AnomalyAlert | None: ...

    @abstractmethod
    def delete_alert(self, user_id: str, alert_id: str) -> bool: ...

    @abstractmethod
    def list_alerts(self, user_id: str) -> list[AnomalyAlert]: ...

    # ---- receipts ----
    @abstractmethod
    def put_receipt(self, receipt: Receipt) -> None: ...

    @abstractmethod
    def get_receipt(self, user_id: str, receipt_id: str) -> Receipt | None: ...

    @abstractmethod
    def delete_receipt(self, user_id: str, receipt_id: str) -> bool: ...

    @abstractmethod
    def list_receipts(self, user_id: str) -> list[Receipt]: ...

    # ---- preferences ----
    @abstractmethod
    def get_preferences(self, user_id: str) -> Preferences | None: ...

    @abstractmethod
    def put_preferences(self, prefs: Preferences) -> None: ...

    # ---- bulk ----
    @abstractmethod
    def delete_all_user_data(self, user_id: str, *, include_user: bool = False) -> None: ...

    def health_check(self) -> bool:
        return True
