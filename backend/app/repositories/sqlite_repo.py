"""SQLite implementation of the repository for local development.

Each entity table keeps the columns needed for lookups and constraints plus a
JSON ``data`` column holding the full record. A new connection is opened per
operation so the repository is safe to use from FastAPI's thread pool.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, TypeVar

from pydantic import BaseModel

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
from app.errors import Conflict
from app.repositories.base import Repository

T = TypeVar("T", bound=BaseModel)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS expenses (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    date TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, date);
CREATE TABLE IF NOT EXISTS budgets (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_budgets_user ON budgets(user_id);
CREATE TABLE IF NOT EXISTS budget_alert_events (
    user_id TEXT NOT NULL,
    month TEXT NOT NULL,
    budget_key TEXT NOT NULL,
    threshold INTEGER NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (user_id, month, budget_key, threshold)
);
CREATE TABLE IF NOT EXISTS goals (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_goals_user ON goals(user_id);
CREATE TABLE IF NOT EXISTS anomaly_alerts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    dedup_key TEXT NOT NULL,
    data TEXT NOT NULL,
    UNIQUE (user_id, dedup_key)
);
CREATE TABLE IF NOT EXISTS receipts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_receipts_user ON receipts(user_id);
CREATE TABLE IF NOT EXISTS preferences (
    user_id TEXT PRIMARY KEY,
    data TEXT NOT NULL
);
"""


class SQLiteRepository(Repository):
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=10)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _load(model: type[T], rows) -> list[T]:
        return [model.model_validate_json(row[0]) for row in rows]

    # ---- users ----
    def create_user(self, user: User) -> None:
        try:
            with self._conn() as conn:
                conn.execute(
                    "INSERT INTO users (id, email, data) VALUES (?, ?, ?)",
                    (user.id, user.email.lower(), user.model_dump_json()),
                )
        except sqlite3.IntegrityError as exc:
            raise Conflict("An account with this email already exists.") from exc

    def get_user(self, user_id: str) -> User | None:
        with self._conn() as conn:
            rows = conn.execute("SELECT data FROM users WHERE id = ?", (user_id,)).fetchall()
        return next(iter(self._load(User, rows)), None)

    def get_user_by_email(self, email: str) -> User | None:
        with self._conn() as conn:
            rows = conn.execute("SELECT data FROM users WHERE email = ?", (email.lower(),)).fetchall()
        return next(iter(self._load(User, rows)), None)

    def update_user(self, user: User) -> None:
        with self._conn() as conn:
            conn.execute("UPDATE users SET data = ? WHERE id = ?", (user.model_dump_json(), user.id))

    # ---- expenses ----
    def put_expense(self, expense: Expense) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO expenses (id, user_id, date, data) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET date = excluded.date, data = excluded.data "
                "WHERE expenses.user_id = excluded.user_id",
                (expense.id, expense.user_id, expense.date.isoformat(), expense.model_dump_json()),
            )

    def get_expense(self, user_id: str, expense_id: str) -> Expense | None:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT data FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id)
            ).fetchall()
        return next(iter(self._load(Expense, rows)), None)

    def delete_expense(self, user_id: str, expense_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id))
            return cur.rowcount > 0

    def list_expenses(self, user_id: str, start: dt.date | None = None, end: dt.date | None = None) -> list[Expense]:
        query = "SELECT data FROM expenses WHERE user_id = ?"
        params: list = [user_id]
        if start:
            query += " AND date >= ?"
            params.append(start.isoformat())
        if end:
            query += " AND date <= ?"
            params.append(end.isoformat())
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return self._load(Expense, rows)

    # ---- budgets ----
    def put_budget(self, budget: Budget) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO budgets (id, user_id, data) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data = excluded.data WHERE budgets.user_id = excluded.user_id",
                (budget.id, budget.user_id, budget.model_dump_json()),
            )

    def get_budget(self, user_id: str, budget_id: str) -> Budget | None:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT data FROM budgets WHERE id = ? AND user_id = ?", (budget_id, user_id)
            ).fetchall()
        return next(iter(self._load(Budget, rows)), None)

    def delete_budget(self, user_id: str, budget_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM budgets WHERE id = ? AND user_id = ?", (budget_id, user_id))
            return cur.rowcount > 0

    def list_budgets(self, user_id: str) -> list[Budget]:
        with self._conn() as conn:
            rows = conn.execute("SELECT data FROM budgets WHERE user_id = ?", (user_id,)).fetchall()
        return self._load(Budget, rows)

    def record_budget_alert_event(self, event: BudgetAlertEvent) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT OR IGNORE INTO budget_alert_events (user_id, month, budget_key, threshold, data) "
                "VALUES (?, ?, ?, ?, ?)",
                (event.user_id, event.month, event.budget_key, event.threshold, event.model_dump_json()),
            )
            return cur.rowcount > 0

    def list_budget_alert_events(self, user_id: str, month: str | None = None) -> list[BudgetAlertEvent]:
        query = "SELECT data FROM budget_alert_events WHERE user_id = ?"
        params: list = [user_id]
        if month:
            query += " AND month = ?"
            params.append(month)
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return self._load(BudgetAlertEvent, rows)

    def delete_budget_alert_events(self, user_id: str, month: str | None = None, budget_key: str | None = None) -> int:
        query = "DELETE FROM budget_alert_events WHERE user_id = ?"
        params: list = [user_id]
        if month:
            query += " AND month = ?"
            params.append(month)
        if budget_key:
            query += " AND budget_key = ?"
            params.append(budget_key)
        with self._conn() as conn:
            return conn.execute(query, params).rowcount

    # ---- goals ----
    def put_goal(self, goal: Goal) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO goals (id, user_id, data) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data = excluded.data WHERE goals.user_id = excluded.user_id",
                (goal.id, goal.user_id, goal.model_dump_json()),
            )

    def get_goal(self, user_id: str, goal_id: str) -> Goal | None:
        with self._conn() as conn:
            rows = conn.execute("SELECT data FROM goals WHERE id = ? AND user_id = ?", (goal_id, user_id)).fetchall()
        return next(iter(self._load(Goal, rows)), None)

    def delete_goal(self, user_id: str, goal_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM goals WHERE id = ? AND user_id = ?", (goal_id, user_id))
            return cur.rowcount > 0

    def list_goals(self, user_id: str) -> list[Goal]:
        with self._conn() as conn:
            rows = conn.execute("SELECT data FROM goals WHERE user_id = ?", (user_id,)).fetchall()
        return self._load(Goal, rows)

    # ---- anomaly alerts ----
    def create_alert_if_absent(self, alert: AnomalyAlert) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT OR IGNORE INTO anomaly_alerts (id, user_id, dedup_key, data) VALUES (?, ?, ?, ?)",
                (alert.id, alert.user_id, alert.dedup_key, alert.model_dump_json()),
            )
            return cur.rowcount > 0

    def put_alert(self, alert: AnomalyAlert) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE anomaly_alerts SET data = ? WHERE id = ? AND user_id = ?",
                (alert.model_dump_json(), alert.id, alert.user_id),
            )

    def get_alert(self, user_id: str, alert_id: str) -> AnomalyAlert | None:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT data FROM anomaly_alerts WHERE id = ? AND user_id = ?", (alert_id, user_id)
            ).fetchall()
        return next(iter(self._load(AnomalyAlert, rows)), None)

    def delete_alert(self, user_id: str, alert_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM anomaly_alerts WHERE id = ? AND user_id = ?", (alert_id, user_id))
            return cur.rowcount > 0

    def list_alerts(self, user_id: str) -> list[AnomalyAlert]:
        with self._conn() as conn:
            rows = conn.execute("SELECT data FROM anomaly_alerts WHERE user_id = ?", (user_id,)).fetchall()
        return self._load(AnomalyAlert, rows)

    # ---- receipts ----
    def put_receipt(self, receipt: Receipt) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO receipts (id, user_id, data) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data = excluded.data WHERE receipts.user_id = excluded.user_id",
                (receipt.id, receipt.user_id, receipt.model_dump_json()),
            )

    def get_receipt(self, user_id: str, receipt_id: str) -> Receipt | None:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT data FROM receipts WHERE id = ? AND user_id = ?", (receipt_id, user_id)
            ).fetchall()
        return next(iter(self._load(Receipt, rows)), None)

    def delete_receipt(self, user_id: str, receipt_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM receipts WHERE id = ? AND user_id = ?", (receipt_id, user_id))
            return cur.rowcount > 0

    def list_receipts(self, user_id: str) -> list[Receipt]:
        with self._conn() as conn:
            rows = conn.execute("SELECT data FROM receipts WHERE user_id = ?", (user_id,)).fetchall()
        return self._load(Receipt, rows)

    # ---- preferences ----
    def get_preferences(self, user_id: str) -> Preferences | None:
        with self._conn() as conn:
            rows = conn.execute("SELECT data FROM preferences WHERE user_id = ?", (user_id,)).fetchall()
        return next(iter(self._load(Preferences, rows)), None)

    def put_preferences(self, prefs: Preferences) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO preferences (user_id, data) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET data = excluded.data",
                (prefs.user_id, prefs.model_dump_json()),
            )

    # ---- bulk ----
    def delete_all_user_data(self, user_id: str, *, include_user: bool = False) -> None:
        tables = ["expenses", "budgets", "budget_alert_events", "goals", "anomaly_alerts", "receipts", "preferences"]
        with self._conn() as conn:
            for table in tables:
                conn.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))  # noqa: S608 - fixed names
            if include_user:
                conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

    def health_check(self) -> bool:
        with self._conn() as conn:
            conn.execute("SELECT 1").fetchone()
        return True
