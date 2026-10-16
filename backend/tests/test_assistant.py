import datetime as dt

import pytest

from app.domain.dates import add_months
from app.services.assistant.nlu import detect_intent, normalize, resolve_period
from tests.conftest import add_expense, headers, register

TODAY = dt.date(2026, 10, 15)


@pytest.mark.parametrize("question,intent", [
    ("How much did I spend this month?", "total_spent"),
    ("How much did I spend on food last month?", "total_spent"),
    ("Which category increased the most?", "category_change"),
    ("What is my remaining monthly budget?", "budget_remaining"),
    ("Which transactions were unusually large?", "unusual_transactions"),
    ("How much could I save by reducing shopping expenses?", "simulate_saving"),
    ("How much do I need to save each month to reach my goal?", "goal_requirement"),
    ("Which expenses were recorded between 2026-09-01 and 2026-09-10?", "list_transactions"),
    ("Am I approaching my monthly budget limit?", "budget_status"),
    ("What is my salary?", "unsupported"),
    ("Tell me a joke", "unsupported"),
])
def test_intents(question, intent):
    assert detect_intent(normalize(question)) == intent


def test_date_resolution():
    p = resolve_period("last month", TODAY)
    assert (p.start, p.end) == (dt.date(2026, 9, 1), dt.date(2026, 9, 30))
    p = resolve_period("this month", TODAY)
    assert (p.start, p.end) == (dt.date(2026, 10, 1), TODAY)
    p = resolve_period("in november", TODAY)  # future month name -> most recent past November
    assert p.start == dt.date(2025, 11, 1)
    p = resolve_period("between 2026-09-01 and 2026-09-10", TODAY)
    assert (p.start, p.end) == (dt.date(2026, 9, 1), dt.date(2026, 9, 10))
    p = resolve_period("last 7 days", TODAY)
    assert p.start == dt.date(2026, 10, 9)
    assert resolve_period("may i see my spending", TODAY) is None  # 'may' as a verb
    assert resolve_period("in may", TODAY).start == dt.date(2026, 5, 1)


def ask(client, auth, q):
    resp = client.post("/api/v1/assistant/query", headers=auth, json={"question": q})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_empty_dataset_answers_clearly(client, auth):
    r = ask(client, auth, "How much did I spend this month?")
    assert "No expenses" in r["answer"]
    assert "not financial advice" in r["disclaimer"]


def test_correct_calculations(client, auth, today):
    last = add_months(today.replace(day=1), -1)
    add_expense(client, auth, 30000, today, "food", "Lunch")
    add_expense(client, auth, 20050, today, "transportation", "Cab")
    add_expense(client, auth, 10000, last + dt.timedelta(days=2), "food", "Old lunch")
    r = ask(client, auth, "How much did I spend this month?")
    assert "₹500.50" in r["answer"] and "2 transaction" in r["answer"]
    assert r["data"]["total_minor"] == 50050
    r = ask(client, auth, "How much did I spend on food last month?")
    assert "₹100" in r["answer"] and r["period"]["start"] == last.isoformat()


def test_ambiguous_date_asks_for_clarification(client, auth):
    r = ask(client, auth, "What did I spend recently?")
    assert r["needs_clarification"] is True


def test_unsupported_question_lists_capabilities(client, auth):
    r = ask(client, auth, "Should I buy Tesla stock?")
    assert r["intent"] == "unsupported" and r["suggestions"]
    assert "not a financial advisor" in r["answer"]


def test_budget_and_goal_questions(client, auth, today):
    r = ask(client, auth, "What is my remaining monthly budget?")
    assert "haven't set" in r["answer"]
    client.post("/api/v1/budgets", headers=auth, json={"amount_minor": 1000000})
    add_expense(client, auth, 250000, today, "food", "Groceries run")
    r = ask(client, auth, "What is my remaining monthly budget?")
    assert "₹7,500" in r["answer"]

    client.post("/api/v1/goals", headers=auth, json={"name": "Laptop", "target_minor": 1200000,
                                                       "target_date": add_months(today, 12).isoformat()})
    client.post("/api/v1/goals", headers=auth, json={"name": "Trip", "target_minor": 500000,
                                                       "target_date": add_months(today, 5).isoformat()})
    r = ask(client, auth, "How much do I need to save each month to reach my goal?")
    assert r["needs_clarification"] and "Laptop" in r["answer"]
    r = ask(client, auth, "How much do I need to save each month for the laptop goal?")
    # ₹12,000 over 12 months -> ₹1,000 per month
    assert r["intent"] == "goal_requirement" and "₹1,000 per month" in r["answer"]


def test_simulation_question(client, auth, today):
    last = add_months(today.replace(day=1), -1)
    add_expense(client, auth, 400000, last + dt.timedelta(days=1), "shopping", "Clothes")
    r = ask(client, auth, "How much could I save by reducing shopping by 25%?")
    assert r["data"]["monthly_savings_minor"] == 100000
    assert "₹12,000" in r["answer"]
    r = ask(client, auth, "How much could I save by reducing it?")
    assert r["needs_clarification"]


def test_user_data_isolation(client, today):
    alice = headers(register(client, "a@example.com", "A"))
    bob = headers(register(client, "b@example.com", "B"))
    add_expense(client, alice, 999900, today, "shopping", "Alice secret purchase")
    r = ask(client, bob, "How much did I spend this month?")
    assert "No expenses" in r["answer"]
    r = ask(client, bob, "Show my largest expenses this month")
    assert "Alice" not in str(r)
