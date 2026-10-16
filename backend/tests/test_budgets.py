import datetime as dt

from app.domain.dates import month_key
from app.domain.models import Budget
from app.services.budgets import budgets_for_month, evaluate
from tests.conftest import add_expense

TODAY = dt.date(2026, 10, 15)
TH = [75, 90, 100]


def test_normal_utilization():
    r = evaluate(1000000, 400000, TH, month="2026-10", today=TODAY)
    assert r["utilization_pct"] == 40.0
    assert r["remaining_minor"] == 600000
    assert r["status"] == "ok"
    assert r["thresholds_crossed"] == []


def test_thresholds_and_warning():
    r = evaluate(100000, 91000, TH, month="2026-09", today=TODAY)
    assert r["status"] == "warning"
    assert r["thresholds_crossed"] == [75, 90]


def test_exceeded_vs_projected_overrun():
    exceeded = evaluate(100000, 120000, TH, month="2026-10", today=TODAY)
    assert exceeded["status"] == "exceeded" and exceeded["remaining_minor"] == -20000
    assert exceeded["projected_overrun"] is False  # already exceeded, not a projection

    # 60% used by day 15 of 31 -> projected 124% -> projected overrun but not exceeded
    projected = evaluate(100000, 60000, TH, month="2026-10", today=TODAY)
    assert projected["status"] == "ok"
    assert projected["projected_overrun"] is True
    assert projected["projected_spend_minor"] == 124000


def test_no_projection_for_past_months_or_too_early():
    assert evaluate(100000, 60000, TH, month="2026-09", today=TODAY)["projected_spend_minor"] is None
    early = evaluate(100000, 30000, TH, month="2026-10", today=dt.date(2026, 10, 2))
    assert early["projected_spend_minor"] is None


def test_zero_budget():
    assert evaluate(0, 0, TH, month="2026-10", today=TODAY)["status"] == "ok"
    r = evaluate(0, 500, TH, month="2026-10", today=TODAY)
    assert r["status"] == "exceeded" and r["utilization_pct"] is None


def test_at_limit():
    assert evaluate(1000, 1000, TH, month="2026-09", today=TODAY)["status"] == "at_limit"


def test_budget_versions_by_month():
    old = Budget(user_id="u", category="food", amount_minor=500, effective_from="2026-01", effective_to="2026-08")
    new = Budget(user_id="u", category="food", amount_minor=800, effective_from="2026-09")
    assert budgets_for_month([old, new], "2026-05")["food"].amount_minor == 500
    assert budgets_for_month([old, new], "2026-10")["food"].amount_minor == 800
    assert budgets_for_month([old, new], "2025-12") == {}


def test_budget_api_flow_and_alert_dedup(client, auth, today):
    overall = client.post("/api/v1/budgets", json={"amount_minor": 100000}, headers=auth)
    assert overall.status_code == 201
    food = client.post("/api/v1/budgets", json={"category": "food", "amount_minor": 10000}, headers=auth).json()
    dup = client.post("/api/v1/budgets", json={"category": "food", "amount_minor": 5}, headers=auth)
    assert dup.status_code == 409
    assert client.post("/api/v1/budgets", json={"category": "nope", "amount_minor": 5}, headers=auth).status_code == 422
    assert client.post("/api/v1/budgets", json={"amount_minor": -1}, headers=auth).status_code == 422

    resp = client.post("/api/v1/expenses", headers=auth, json={
        "amount_minor": 9500, "date": today.isoformat(), "category": "food", "description": "Feast"})
    alerts = resp.json()["budget_alerts"]
    assert {(a["category_name"], a["threshold"]) for a in alerts} >= {("Food & Dining", 75), ("Food & Dining", 90)}

    # Another small expense: thresholds already reported must not be reported again.
    resp = client.post("/api/v1/expenses", headers=auth, json={
        "amount_minor": 100, "date": today.isoformat(), "category": "food", "description": "Gum"})
    assert all(a["threshold"] not in (75, 90) or a["category_name"] != "Food & Dining" for a in resp.json()["budget_alerts"])

    data = client.get("/api/v1/budgets", headers=auth).json()
    food_row = next(c for c in data["categories"] if c["category"] == "food")
    assert food_row["spent_minor"] == 9600
    assert food_row["remaining_minor"] == 400
    assert data["overall"]["spent_minor"] == 9600

    updated = client.put(f"/api/v1/budgets/{food['id']}", json={"amount_minor": 20000}, headers=auth)
    assert updated.status_code == 200
    data = client.get("/api/v1/budgets", headers=auth).json()
    assert next(c for c in data["categories"] if c["category"] == "food")["amount_minor"] == 20000


def test_missing_budget_reports_unbudgeted_spending(client, auth, today):
    add_expense(client, auth, 5000, today, "travel", "Bus")
    data = client.get("/api/v1/budgets", headers=auth).json()
    assert data["overall"] is None
    assert data["unbudgeted"][0]["category"] == "travel"


def test_budget_history(client, auth, today):
    client.post("/api/v1/budgets", json={"amount_minor": 100000}, headers=auth)
    add_expense(client, auth, 30000, today)
    rows = client.get("/api/v1/budgets/history?months=3", headers=auth).json()["months"]
    assert len(rows) == 3
    current = rows[-1]
    assert current["month"] == month_key(today) and current["spent_minor"] == 30000
    assert current["utilization_pct"] == 30.0
    assert rows[0]["overall_budget_minor"] is None  # budget did not exist then
