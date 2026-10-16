"""Shared fixtures. Every test uses an isolated temporary database and receipt folder."""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")

from app.config import Settings  # noqa: E402
from app.domain.dates import today_in  # noqa: E402
from app.domain.models import Expense, Preferences  # noqa: E402
from app.main import create_app  # noqa: E402
from app.repositories.sqlite_repo import SQLiteRepository  # noqa: E402
from app.services.receipts.storage import LocalReceiptStorage  # noqa: E402

TZ = "Asia/Kolkata"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        environment="test",
        sqlite_path=tmp_path / "test.db",
        receipt_dir=tmp_path / "receipts",
        jwt_secret="test-secret-that-is-long-enough-for-hs256-signing",
        cors_origins=["http://localhost:5173"],
        allow_demo_data=True,
        max_receipt_bytes=1024 * 1024,
    )


@pytest.fixture
def repo(settings: Settings) -> SQLiteRepository:
    return SQLiteRepository(settings.sqlite_path)


@pytest.fixture
def app(settings, repo):
    return create_app(settings=settings, repo=repo, storage=LocalReceiptStorage(settings.receipt_dir))


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


def register(client: TestClient, email: str = "alice@example.com", name: str = "Alice") -> dict:
    resp = client.post("/api/v1/auth/register", json={"name": name, "email": email, "password": "Passw0rd!"})
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}", "_user_id": resp.json()["user"]["id"]}


def headers(auth: dict) -> dict:
    return {k: v for k, v in auth.items() if not k.startswith("_")}


@pytest.fixture
def auth(client) -> dict:
    return headers(register(client))


@pytest.fixture
def today() -> dt.date:
    return today_in(TZ)


def make_expense(amount_rupees: float, day: dt.date, category: str = "food", description: str = "Item",
                 merchant: str | None = None, user_id: str = "u1", **kw) -> Expense:
    return Expense(user_id=user_id, amount_minor=int(round(amount_rupees * 100)), date=day, category=category,
                   description=description, merchant=merchant, **kw)


def prefs(user_id: str = "u1", **kw) -> Preferences:
    return Preferences(user_id=user_id, timezone=TZ, **kw)


def add_expense(client: TestClient, auth: dict, amount_minor: int, day: dt.date, category: str = "food",
                description: str = "Lunch", **kw) -> dict:
    body = {"amount_minor": amount_minor, "date": day.isoformat(), "category": category,
            "description": description, **kw}
    resp = client.post("/api/v1/expenses", json=body, headers=auth)
    assert resp.status_code == 201, resp.text
    return resp.json()["expense"]
