"""Clearly-labelled synthetic demo data for development and demonstrations.

Every record created here has ``is_demo=True`` so it can be removed with one
action. Disabled when ALLOW_DEMO_DATA is false (the production default).
"""

from __future__ import annotations

import datetime as dt
import random

from app.domain.dates import add_months, month_key, today_in
from app.domain.models import Budget, Expense, Goal, GoalContribution, Preferences
from app.repositories.base import Repository
from app.services.anomalies import scan_all


def _rupees(value: float) -> int:
    return int(round(value)) * 100


def generate_demo_expenses(user_id: str, today: dt.date, seed: int = 7) -> list[Expense]:
    rng = random.Random(seed)
    expenses: list[Expense] = []

    def add(day: dt.date, amount: int, category: str, description: str, merchant: str | None, method: str):
        if day <= today:
            expenses.append(Expense(user_id=user_id, amount_minor=amount, date=day, category=category,
                                    description=description, merchant=merchant, payment_method=method,
                                    notes="Demo data", is_demo=True))

    first_month = add_months(today.replace(day=1), -5)
    for offset in range(6):
        month_start = add_months(first_month, offset)
        is_current = month_key(month_start) == month_key(today)
        last_day = (add_months(month_start, 1) - dt.timedelta(days=1)).day

        def day(n: int) -> dt.date:
            return month_start.replace(day=min(n, last_day))

        add(day(1), _rupees(15000), "housing", "Monthly rent", "Sunrise Apartments", "net_banking")
        add(day(5), 64900, "subscriptions", "Netflix subscription", "Netflix", "credit_card")
        if offset >= 4:  # a new recurring payment in the last two months
            add(day(12), 11900, "subscriptions", "Spotify Premium", "Spotify", "credit_card")
        add(day(8), 79900, "utilities", "Broadband bill", "AirFiber", "upi")
        add(day(10), _rupees(rng.randint(1100, 1800)), "utilities", "Electricity bill", "State Power Co", "upi")

        for week in range(4):
            add(day(3 + week * 7), _rupees(rng.randint(1400, 2800)), "groceries", "Weekly groceries",
                rng.choice(["FreshMart", "BigBasket", "Daily Needs Store"]), rng.choice(["upi", "debit_card"]))

        food_count = 16 if is_current else 11
        for _ in range(food_count):
            add(day(rng.randint(1, last_day)), _rupees(rng.randint(160, 620)), "food",
                rng.choice(["Dinner delivery", "Lunch", "Coffee", "Snacks"]),
                rng.choice(["Swiggy", "Zomato", "Cafe Coffee Day", "Campus Canteen"]), "upi")
        for _ in range(rng.randint(8, 12)):
            description, merchant = rng.choice([("Cab ride", "Uber"), ("Cab ride", "Ola"), ("Metro card recharge", "Metro"),
                                                ("Auto ride", None)])
            add(day(rng.randint(1, last_day)), _rupees(rng.randint(60, 380)), "transportation", description, merchant, "upi")
        for _ in range(rng.randint(1, 3)):
            add(day(rng.randint(1, last_day)), _rupees(rng.randint(450, 2400)), "shopping",
                rng.choice(["Clothes", "Household items", "Phone accessories"]), rng.choice(["Amazon", "Myntra", "Flipkart"]),
                rng.choice(["credit_card", "upi"]))
        add(day(rng.randint(14, 26)), _rupees(rng.randint(300, 750)), "entertainment", "Movie tickets", "PVR Cinemas", "upi")
        if rng.random() < 0.5:
            add(day(rng.randint(1, last_day)), _rupees(rng.randint(200, 900)), "healthcare", "Pharmacy", "Apollo Pharmacy", "cash")
        if offset == 2:
            add(day(18), _rupees(4500), "education", "Online course", "Coursera", "credit_card")

    # Items that should be noticed by anomaly detection in the current month.
    current_start = today.replace(day=1)
    add(min(current_start + dt.timedelta(days=4), today), _rupees(18999), "shopping", "Wireless headphones",
        "Electronics Hub", "credit_card")
    dup_day = min(current_start + dt.timedelta(days=2), today)
    add(dup_day, _rupees(486), "food", "Dinner delivery", "Swiggy", "upi")
    add(dup_day, _rupees(486), "food", "Dinner delivery", "Swiggy", "upi")
    return expenses


def load_demo_data(repo: Repository, prefs: Preferences) -> dict:
    clear_demo_data(repo, prefs)
    today = today_in(prefs.timezone)
    expenses = generate_demo_expenses(prefs.user_id, today)
    for e in expenses:
        repo.put_expense(e)

    start = month_key(add_months(today.replace(day=1), -5))
    for category, amount in [(None, 60000), ("food", 5000), ("shopping", 4000), ("transportation", 2500),
                             ("entertainment", 1500)]:
        repo.put_budget(Budget(user_id=prefs.user_id, category=category, amount_minor=_rupees(amount),
                               effective_from=start, is_demo=True))

    laptop = Goal(user_id=prefs.user_id, name="New laptop", target_minor=_rupees(80000),
                  target_date=add_months(today, 8), is_demo=True)
    fund = Goal(user_id=prefs.user_id, name="Emergency fund", target_minor=_rupees(150000),
                target_date=add_months(today, 18), is_demo=True)
    for goal, monthly in ((laptop, 5500), (fund, 6000)):
        for i in range(4, 0, -1):
            contribution_day = add_months(today, -i).replace(day=2)
            goal.contributions.append(GoalContribution(amount_minor=_rupees(monthly), date=contribution_day,
                                                       note="Demo contribution"))
        goal.saved_minor = sum(c.amount_minor for c in goal.contributions)
        repo.put_goal(goal)

    scan = scan_all(repo, prefs)
    for alert in repo.list_alerts(prefs.user_id):
        if not alert.is_demo and any(alert.expense_id == e.id for e in expenses):
            alert.is_demo = True
            repo.put_alert(alert)
    return {"expenses": len(expenses), "budgets": 5, "goals": 2, "alerts": scan["created"]}


def clear_demo_data(repo: Repository, prefs: Preferences) -> dict:
    uid = prefs.user_id
    demo_expense_ids = set()
    removed = {"expenses": 0, "budgets": 0, "goals": 0, "alerts": 0}
    for e in repo.list_expenses(uid):
        if e.is_demo:
            demo_expense_ids.add(e.id)
            repo.delete_expense(uid, e.id)
            removed["expenses"] += 1
    for b in repo.list_budgets(uid):
        if b.is_demo:
            repo.delete_budget(uid, b.id)
            removed["budgets"] += 1
    for g in repo.list_goals(uid):
        if g.is_demo:
            repo.delete_goal(uid, g.id)
            removed["goals"] += 1
    for a in repo.list_alerts(uid):
        if a.is_demo or a.expense_id in demo_expense_ids:
            repo.delete_alert(uid, a.id)
            removed["alerts"] += 1
    if removed["expenses"] or removed["budgets"]:
        # Threshold events were derived from demo records; re-arm them.
        repo.delete_budget_alert_events(uid)
    return removed
