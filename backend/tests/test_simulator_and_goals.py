import datetime as dt
from decimal import Decimal

import pytest

from app.domain.dates import add_months
from app.domain.models import Goal, GoalContribution
from app.errors import ValidationFailed
from app.services.goals import goal_metrics
from app.services.simulator import Adjustment, apply_adjustment, compute_baseline
from tests.conftest import add_expense, make_expense

TODAY = dt.date(2026, 10, 15)


def test_percentage_reduction():
    new, warnings = apply_adjustment(400000, Adjustment("food", "percent", Decimal(25)))
    assert new == 300000 and warnings == []


def test_fixed_reduction_and_cap():
    assert apply_adjustment(400000, Adjustment("shopping", "amount", Decimal(100000)))[0] == 300000
    new, warnings = apply_adjustment(50000, Adjustment("shopping", "amount", Decimal(100000)))
    assert new == 0 and warnings


def test_target_mode_can_increase():
    assert apply_adjustment(1000, Adjustment("entertainment", "target", Decimal(2500)))[0] == 2500


@pytest.mark.parametrize("adj", [
    Adjustment("food", "percent", Decimal(150)),
    Adjustment("food", "percent", Decimal(-5)),
    Adjustment("food", "amount", Decimal(-1)),
    Adjustment("food", "bogus", Decimal(1)),
])
def test_invalid_scenarios(adj):
    with pytest.raises(ValidationFailed):
        apply_adjustment(1000, adj)


def test_baselines():
    exp = [make_expense(3000, dt.date(2026, 9, 5), "food"), make_expense(1000, dt.date(2026, 8, 5), "food"),
           make_expense(500, dt.date(2026, 10, 5), "food")]
    last, info = compute_baseline(exp, "last_month", TODAY)
    assert last["food"] == 300000 and info["months"] == 1
    avg, info = compute_baseline(exp, "avg_3_months", TODAY)
    assert avg["food"] == 200000 and info["months"] == 2  # only months with records count
    proj, _ = compute_baseline(exp, "current_month_projection", TODAY)
    assert proj["food"] == 103333  # 500 / 15 days * 31


def test_simulation_api_monthly_annual_and_no_side_effects(client, auth, today):
    last_month = add_months(today.replace(day=1), -1)
    add_expense(client, auth, 400000, last_month + dt.timedelta(days=3), "food", "Food month")
    add_expense(client, auth, 200000, last_month + dt.timedelta(days=4), "shopping", "Shopping month")
    before = client.get("/api/v1/expenses", headers=auth).json()["total_count"]
    resp = client.post("/api/v1/simulations", headers=auth, json={
        "baseline": "last_month",
        "scenarios": [
            {"name": "Cut food 25%", "adjustments": [{"category": "food", "mode": "percent", "value": 25}]},
            {"name": "Shopping -1000", "adjustments": [{"category": "shopping", "mode": "amount", "value": 100000}]},
        ]})
    assert resp.status_code == 200, resp.text
    a, b = resp.json()["scenarios"]
    assert a["monthly_savings_minor"] == 100000 and a["annual_savings_minor"] == 1200000
    assert a["current_total_minor"] == 600000 and a["new_total_minor"] == 500000
    assert "12 months" in a["explanation"]
    assert b["monthly_savings_minor"] == 100000
    assert client.get("/api/v1/expenses", headers=auth).json()["total_count"] == before

    bad = client.post("/api/v1/simulations", headers=auth, json={
        "scenarios": [{"adjustments": [{"category": "food", "mode": "percent", "value": 120}]}]})
    assert bad.status_code == 422
    unknown = client.post("/api/v1/simulations", headers=auth, json={
        "scenarios": [{"adjustments": [{"category": "zzz", "mode": "percent", "value": 10}]}]})
    assert unknown.status_code == 422


def test_goal_metrics_and_edge_cases():
    goal = Goal(user_id="u", name="Laptop", target_minor=8000000, saved_minor=2000000,
                target_date=add_months(TODAY, 6))
    m = goal_metrics(goal, TODAY)
    assert m["remaining_minor"] == 6000000
    assert m["progress_pct"] == 25.0
    assert m["required_monthly_minor"] == 1000000

    done = Goal(user_id="u", name="Done", target_minor=1000, saved_minor=1500)
    m = goal_metrics(done, TODAY)
    assert m["completed"] and m["status"] == "completed" and m["remaining_minor"] == 0 and m["progress_pct"] == 100.0

    past = Goal(user_id="u", name="Late", target_minor=1000, saved_minor=10, target_date=TODAY - dt.timedelta(days=1))
    assert goal_metrics(past, TODAY)["status"] == "overdue"

    behind = Goal(user_id="u", name="Slow", target_minor=1200000, saved_minor=10000, target_date=add_months(TODAY, 3),
                  contributions=[GoalContribution(amount_minor=10000, date=TODAY - dt.timedelta(days=10))])
    assert goal_metrics(behind, TODAY)["status"] == "behind"


def test_starting_balance_is_not_saving_pace(client, auth, today):
    future = (today + dt.timedelta(days=200)).isoformat()
    g = client.post("/api/v1/goals", headers=auth, json={
        "name": "Trip", "target_minor": 3000000, "saved_minor": 500000, "target_date": future}).json()
    assert g["contributions"][0]["kind"] == "starting_balance"
    assert g["recent_monthly_contribution_minor"] == 0
    assert g["status"] == "not_started" and g["projected_completion_date"] is None
    g = client.post(f"/api/v1/goals/{g['id']}/contributions", headers=auth, json={"amount_minor": 300000}).json()
    assert g["recent_monthly_contribution_minor"] == 100000  # 3,000 over the 90-day window = 1,000/month
    assert g["status"] == "behind"


def test_goal_api(client, auth, today):
    future = (today + dt.timedelta(days=200)).isoformat()
    assert client.post("/api/v1/goals", headers=auth, json={"name": "X", "target_minor": 0}).status_code == 422
    assert client.post("/api/v1/goals", headers=auth, json={
        "name": "X", "target_minor": 100, "target_date": "2020-01-01"}).status_code == 422
    g = client.post("/api/v1/goals", headers=auth, json={
        "name": "Laptop", "target_minor": 8000000, "saved_minor": 1000000, "target_date": future}).json()
    assert g["progress_pct"] == 12.5 and len(g["contributions"]) == 1

    g = client.post(f"/api/v1/goals/{g['id']}/contributions", headers=auth, json={"amount_minor": 500000}).json()
    assert g["saved_minor"] == 1500000
    too_much = client.post(f"/api/v1/goals/{g['id']}/contributions", headers=auth, json={"amount_minor": -9999999})
    assert too_much.status_code == 422

    # Ordinary expenses never count as savings contributions.
    add_expense(client, auth, 300000, today, "shopping", "Gadget")
    assert client.get(f"/api/v1/goals/{g['id']}", headers=auth).json()["saved_minor"] == 1500000

    req = client.post("/api/v1/simulations/required-savings", headers=auth, json={"goal_id": g["id"]}).json()
    assert req["required_monthly_minor"] > 0 and req["amount_minor"] == 6500000

    completed = client.post(f"/api/v1/goals/{g['id']}/contributions", headers=auth, json={"amount_minor": 6500000}).json()
    assert completed["status"] == "completed"
    req = client.post("/api/v1/simulations/required-savings", headers=auth, json={"goal_id": g["id"]}).json()
    assert req["goal_completed"] is True

    upd = client.put(f"/api/v1/goals/{g['id']}", headers=auth, json={"name": "Gaming laptop", "archived": True}).json()
    assert upd["name"] == "Gaming laptop" and upd["status"] == "archived"
    assert client.delete(f"/api/v1/goals/{g['id']}", headers=auth).status_code == 204
