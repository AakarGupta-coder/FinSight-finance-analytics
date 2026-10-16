import datetime as dt

from tests.conftest import add_expense


def test_create_get_update_delete(client, auth, today):
    created = add_expense(client, auth, 45050, today, "food", "Dinner", merchant="Swiggy", payment_method="upi")
    assert created["amount_minor"] == 45050

    got = client.get(f"/api/v1/expenses/{created['id']}", headers=auth).json()
    assert got["merchant"] == "Swiggy"

    body = {**{k: got[k] for k in ("date", "category", "description", "merchant", "payment_method")},
            "amount_minor": 50000, "notes": "corrected"}
    resp = client.put(f"/api/v1/expenses/{created['id']}", json=body, headers=auth)
    assert resp.status_code == 200
    assert resp.json()["expense"]["amount_minor"] == 50000

    assert client.delete(f"/api/v1/expenses/{created['id']}", headers=auth).status_code == 204
    assert client.get(f"/api/v1/expenses/{created['id']}", headers=auth).status_code == 404


def test_persistence_across_app_instances(settings, repo, client, auth, today):
    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.repositories.sqlite_repo import SQLiteRepository

    add_expense(client, auth, 1000, today)
    fresh = TestClient(create_app(settings=settings, repo=SQLiteRepository(settings.sqlite_path)))
    assert fresh.get("/api/v1/expenses", headers=auth).json()["total_count"] == 1


def test_invalid_amounts(client, auth, today):
    for amount in (0, -100, 10**15):
        resp = client.post("/api/v1/expenses", headers=auth, json={
            "amount_minor": amount, "date": today.isoformat(), "category": "food", "description": "x"})
        assert resp.status_code == 422, amount
    resp = client.post("/api/v1/expenses", headers=auth, json={
        "amount_minor": 12.5, "date": today.isoformat(), "category": "food", "description": "x"})
    assert resp.status_code == 422


def test_invalid_dates_and_fields(client, auth, today):
    future = today + dt.timedelta(days=3)
    cases = [
        {"date": future.isoformat()},
        {"date": "1999-12-31"},
        {"date": "2026-02-30"},
        {"category": "not-a-category"},
        {"payment_method": "bitcoin"},
        {"description": "   "},
    ]
    for override in cases:
        body = {"amount_minor": 100, "date": today.isoformat(), "category": "food", "description": "x", **override}
        resp = client.post("/api/v1/expenses", headers=auth, json=body)
        assert resp.status_code == 422, override
        assert resp.json()["error"]["code"] == "validation_error"


def test_empty_list(client, auth):
    data = client.get("/api/v1/expenses", headers=auth).json()
    assert data["items"] == [] and data["total_count"] == 0 and data["total_amount_minor"] == 0


def test_search_filter_sort_paginate_and_totals(client, auth, today):
    d1, d2 = today - dt.timedelta(days=10), today - dt.timedelta(days=2)
    add_expense(client, auth, 10000, d1, "food", "Pizza night", merchant="Dominos", payment_method="credit_card")
    add_expense(client, auth, 25050, d2, "groceries", "Weekly groceries", merchant="FreshMart")
    add_expense(client, auth, 5000, today, "food", "Coffee", merchant="Cafe")
    add_expense(client, auth, 99900, today, "shopping", "Shoes", payment_method="credit_card")

    data = client.get("/api/v1/expenses", headers=auth).json()
    assert data["total_count"] == 4
    assert data["total_amount_minor"] == 10000 + 25050 + 5000 + 99900

    food = client.get("/api/v1/expenses?category=food", headers=auth).json()
    assert food["total_count"] == 2 and food["total_amount_minor"] == 15000

    card = client.get("/api/v1/expenses?payment_method=credit_card", headers=auth).json()
    assert {i["description"] for i in card["items"]} == {"Pizza night", "Shoes"}

    search = client.get("/api/v1/expenses?search=fresh", headers=auth).json()
    assert search["total_count"] == 1 and search["items"][0]["merchant"] == "FreshMart"

    ranged = client.get(f"/api/v1/expenses?start={d2}&end={today}", headers=auth).json()
    assert ranged["total_count"] == 3

    by_amount = client.get("/api/v1/expenses?sort=amount&order=asc", headers=auth).json()
    assert [i["amount_minor"] for i in by_amount["items"]] == [5000, 10000, 25050, 99900]

    page2 = client.get("/api/v1/expenses?page=2&page_size=3", headers=auth).json()
    assert len(page2["items"]) == 1 and page2["total_pages"] == 2

    bad = client.get(f"/api/v1/expenses?start={today}&end={d1}", headers=auth)
    assert bad.status_code == 422
    assert client.get("/api/v1/expenses?sort=password", headers=auth).status_code == 422
