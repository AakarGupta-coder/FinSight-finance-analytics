import datetime as dt

from app.services.anomalies import SENSITIVITY, detect_category_spikes, detect_for_expense
from tests.conftest import add_expense, make_expense

NAMES = {"food": "Food", "housing": "Housing", "shopping": "Shopping", "subscriptions": "Subscriptions"}
BASE = dt.date(2026, 9, 1)


def _history(amounts, category="food"):
    return [make_expense(a, BASE + dt.timedelta(days=i), category, f"Meal {i}", f"Place {i}")
            for i, a in enumerate(amounts)]


def test_normal_transaction_not_flagged():
    history = _history([300, 350, 280, 420, 390, 310, 360])
    target = make_expense(450, BASE + dt.timedelta(days=20), "food", "Dinner", "Bistro")
    assert detect_for_expense(target, history + [target], "balanced", "INR", NAMES) == []


def test_unusually_large_transaction_flagged_with_comparison():
    history = _history([300, 350, 280, 420, 390, 310, 360])
    target = make_expense(4200, BASE + dt.timedelta(days=20), "food", "Party", "Hall")
    findings = detect_for_expense(target, history + [target], "balanced", "INR", NAMES)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule == "category_outlier"
    assert f.comparison["median_minor"] == 35000
    assert f.comparison["sample_size"] == 7
    assert f.severity == "high"
    assert "typical" in f.reason


def test_small_dataset_does_not_use_category_statistics():
    history = _history([300, 320])  # only 2 category samples, 2 overall
    target = make_expense(3000, BASE + dt.timedelta(days=5), "food", "Big", "X")
    assert detect_for_expense(target, history + [target], "balanced", "INR", NAMES) == []


def test_recurring_large_amount_like_rent_is_not_flagged():
    history = _history([200, 250, 300, 220, 180, 260, 240, 210, 230, 270, 190, 205])
    rent = [make_expense(15000, dt.date(2026, m, 1), "housing", "Rent", "Landlord") for m in (6, 7, 8)]
    target = make_expense(15000, dt.date(2026, 9, 1), "housing", "Rent", "Landlord")
    findings = detect_for_expense(target, history + rent + [target], "balanced", "INR", NAMES)
    assert [f for f in findings if f.rule in ("category_outlier", "overall_outlier")] == []


def test_identical_subscription_amounts_mad_zero_not_flagged():
    subs = [make_expense(649, dt.date(2026, m, 5), "subscriptions", "Netflix", "Netflix") for m in range(1, 9)]
    target = make_expense(649, dt.date(2026, 9, 5), "subscriptions", "Netflix", "Netflix")
    assert detect_for_expense(target, subs + [target], "balanced", "INR", NAMES) == []


def test_mad_zero_still_flags_large_jump():
    subs = [make_expense(649, dt.date(2026, m, 5), "subscriptions", "Netflix", f"S{m}") for m in range(1, 9)]
    target = make_expense(6490, dt.date(2026, 9, 6), "subscriptions", "Annual plan", "Netflix")
    findings = detect_for_expense(target, subs + [target], "balanced", "INR", NAMES)
    assert findings and findings[0].comparison["robust_z"] is None


def test_duplicate_candidates_flag_only_the_later_entry():
    a = make_expense(486, BASE, "food", "Dinner delivery", "Swiggy")
    b = make_expense(486, BASE, "food", "Dinner delivery", "Swiggy")
    b.created_at = a.created_at + dt.timedelta(seconds=5)
    first = detect_for_expense(a, [a, b], "balanced", "INR", NAMES)
    second = detect_for_expense(b, [a, b], "balanced", "INR", NAMES)
    assert [f.rule for f in first] == []
    assert [f.rule for f in second] == ["duplicate"]


def test_same_amount_different_merchant_is_not_duplicate():
    a = make_expense(100, BASE, "food", "Coffee", "Cafe A")
    b = make_expense(100, BASE, "food", "Coffee", "Cafe B")
    assert detect_for_expense(b, [a, b], "balanced", "INR", NAMES) == []


def test_category_spike():
    history = [make_expense(1000, dt.date(2026, m, 10), "shopping", "Stuff", "Shop") for m in (7, 8, 9)]
    current = [make_expense(1500, dt.date(2026, 10, d), "shopping", "Stuff", "Shop") for d in (2, 6)]
    findings = detect_category_spikes(history + current, "2026-10", SENSITIVITY["balanced"], "INR", NAMES)
    assert len(findings) == 1 and findings[0].comparison["ratio"] == 3.0


def test_sensitivity_changes_outcome():
    history = _history([300, 350, 280, 420, 390, 310, 360])
    target = make_expense(900, BASE + dt.timedelta(days=20), "food", "Dinner", "Fancy")
    assert detect_for_expense(target, history + [target], "conservative", "INR", NAMES) == []
    assert detect_for_expense(target, history + [target], "sensitive", "INR", NAMES)


def test_api_detect_review_and_correct(client, auth, today):
    start = today - dt.timedelta(days=40)
    for i, amount in enumerate([30000, 32000, 28000, 35000, 31000, 29000]):
        add_expense(client, auth, amount, start + dt.timedelta(days=i * 5), "food", f"Meal {i}", merchant=f"R{i}")
    resp = client.post("/api/v1/expenses", headers=auth, json={
        "amount_minor": 600000, "date": today.isoformat(), "category": "food", "description": "Catering"})
    assert resp.json()["new_anomalies"] == 1
    expense_id = resp.json()["expense"]["id"]

    alerts = client.get("/api/v1/anomalies?status=open", headers=auth).json()["items"]
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["expense"]["id"] == expense_id and alert["status"] == "open"
    assert {"reason", "severity", "comparison", "detected_at"} <= alert.keys()

    reviewed = client.post(f"/api/v1/anomalies/{alert['id']}/review", headers=auth,
                           json={"action": "legitimate", "note": "Party catering"})
    assert reviewed.json()["status"] == "legitimate"
    # A full rescan must not resurrect a reviewed alert.
    client.post("/api/v1/anomalies/scan", headers=auth)
    assert client.get("/api/v1/anomalies?status=open", headers=auth).json()["items"] == []

    # Transactions are never modified or deleted by detection.
    assert client.get(f"/api/v1/expenses/{expense_id}", headers=auth).json()["amount_minor"] == 600000


def test_correcting_transaction_refreshes_category_spike(client, auth, today):
    from app.domain.dates import add_months

    this_month = today.replace(day=1)
    for i in (1, 2, 3):
        add_expense(client, auth, 100000, add_months(this_month, -i) + dt.timedelta(days=4), "shopping", "Monthly shop", merchant=f"S{i}")
    big = client.post("/api/v1/expenses", headers=auth, json={
        "amount_minor": 400000, "date": this_month.isoformat(), "category": "shopping", "description": "Big buy"}).json()["expense"]
    spikes = [a for a in client.get("/api/v1/anomalies?status=open", headers=auth).json()["items"] if a["rule"] == "category_spike"]
    assert len(spikes) == 1
    client.put(f"/api/v1/expenses/{big['id']}", headers=auth, json={
        "amount_minor": 90000, "date": this_month.isoformat(), "category": "shopping", "description": "Big buy (fixed)"})
    spikes = [a for a in client.get("/api/v1/anomalies?status=open", headers=auth).json()["items"] if a["rule"] == "category_spike"]
    assert spikes == []


def test_correcting_transaction_resolves_open_alert(client, auth, today):
    start = today - dt.timedelta(days=40)
    for i, amount in enumerate([30000, 32000, 28000, 35000, 31000, 29000]):
        add_expense(client, auth, amount, start + dt.timedelta(days=i * 5), "food", f"Meal {i}", merchant=f"R{i}")
    exp = client.post("/api/v1/expenses", headers=auth, json={
        "amount_minor": 600000, "date": today.isoformat(), "category": "food", "description": "Typo"}).json()["expense"]
    assert client.get("/api/v1/anomalies?status=open", headers=auth).json()["items"]
    client.put(f"/api/v1/expenses/{exp['id']}", headers=auth, json={
        "amount_minor": 30000, "date": today.isoformat(), "category": "food", "description": "Typo fixed"})
    assert client.get("/api/v1/anomalies?status=open", headers=auth).json()["items"] == []
