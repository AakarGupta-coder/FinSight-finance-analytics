import datetime as dt

from app.domain.models import Budget
from app.services.analytics import month_summary
from app.services.insights import generate_insights
from tests.conftest import make_expense, prefs

TODAY = dt.date(2026, 10, 20)


def _by_id(result, prefix):
    return [i for i in result["insights"] if i["id"].startswith(prefix)]


def test_insufficient_history_produces_data_gap_not_claims():
    expenses = [make_expense(500, dt.date(2026, 10, 5))]
    result = generate_insights(expenses, [], [], prefs(), "2026-10", TODAY)
    assert _by_id(result, "history-needed")
    assert not _by_id(result, "mom-total")
    assert not _by_id(result, "cat-change")
    assert not _by_id(result, "avg-monthly")


def test_empty_month():
    result = generate_insights([], [], [], prefs(), "2026-10", TODAY)
    assert _by_id(result, "no-data")
    assert all(i["kind"] == "data_gap" for i in result["insights"])


def test_month_over_month_uses_same_day_range():
    expenses = [
        make_expense(1000, dt.date(2026, 9, 10), "food"),
        make_expense(5000, dt.date(2026, 9, 28), "food"),  # after day 20: excluded from comparison
        make_expense(1280, dt.date(2026, 10, 12), "food"),
    ]
    summary = month_summary(expenses, "2026-10", TODAY)
    assert summary["previous_comparable_total_minor"] == 100000
    assert summary["previous_month_total_minor"] == 600000
    assert summary["change_pct"] == 28.0
    result = generate_insights(expenses, [], [], prefs(), "2026-10", TODAY)
    mom = _by_id(result, "mom-total")[0]
    assert mom["kind"] == "fact"
    assert mom["evidence"]["values"]["change_pct"] == 28.0
    assert mom["evidence"]["values"]["comparison_period"]["end"] == "2026-09-20"


def test_category_increase_insight_with_evidence():
    expenses = [
        make_expense(1000, dt.date(2026, 9, 3), "food"),
        make_expense(1000, dt.date(2026, 9, 4), "transportation"),
        make_expense(1500, dt.date(2026, 10, 3), "food"),
        make_expense(1000, dt.date(2026, 10, 4), "transportation"),
    ]
    result = generate_insights(expenses, [], [], prefs(), "2026-10", TODAY)
    change = _by_id(result, "cat-change-food")[0]
    assert "50% higher" in change["message"]
    assert change["evidence"]["transactions"][0]["amount_minor"] == 150000
    assert not _by_id(result, "cat-change-transportation")  # unchanged
    share = _by_id(result, "top-share")[0]
    assert share["evidence"]["values"]["share_pct"] == 60.0
    rec = _by_id(result, "rec-reduce-food")
    assert rec and rec[0]["kind"] == "recommendation"


def test_budget_projection_is_labelled_projection():
    expenses = [make_expense(800, dt.date(2026, 10, d), "food") for d in range(1, 21)]  # 16,000 in 20 days
    budget = Budget(user_id="u1", amount_minor=2000000, effective_from="2026-01")  # 20,000
    result = generate_insights(expenses, [budget], [], prefs(), "2026-10", TODAY)
    proj = _by_id(result, "budget-projection")[0]
    assert proj["kind"] == "projection"
    assert proj["evidence"]["values"]["projected_minor"] == 2480000  # 16000/20*31
    assert "not a certainty" in proj["message"]
    assert _by_id(result, "budget-allowance")[0]["kind"] == "recommendation"


def test_exceeded_budget_is_a_fact():
    expenses = [make_expense(30000, dt.date(2026, 10, 2), "housing")]
    budget = Budget(user_id="u1", amount_minor=2000000, effective_from="2026-01")
    result = generate_insights(expenses, [budget], [], prefs(), "2026-10", TODAY)
    exceeded = _by_id(result, "budget-exceeded")[0]
    assert exceeded["kind"] == "fact" and exceeded["severity"] == "critical"


def test_past_month_uses_full_month_comparison():
    expenses = [make_expense(100, dt.date(2026, 8, 30)), make_expense(200, dt.date(2026, 9, 30))]
    result = generate_insights(expenses, [], [], prefs(), "2026-09", TODAY)
    mom = _by_id(result, "mom-total")[0]
    assert mom["evidence"]["values"]["change_pct"] == 100.0
    assert mom["evidence"]["values"]["comparison_period"]["end"] == "2026-08-31"


def test_new_recurring_subscription_detected():
    expenses = [
        make_expense(649, dt.date(2026, 6, 5), "subscriptions", "Netflix", "Netflix"),
        make_expense(649, dt.date(2026, 7, 5), "subscriptions", "Netflix", "Netflix"),
        make_expense(649, dt.date(2026, 8, 5), "subscriptions", "Netflix", "Netflix"),
        make_expense(649, dt.date(2026, 9, 5), "subscriptions", "Netflix", "Netflix"),
        make_expense(649, dt.date(2026, 10, 5), "subscriptions", "Netflix", "Netflix"),
        make_expense(119, dt.date(2026, 9, 12), "subscriptions", "Spotify", "Spotify"),
        make_expense(119, dt.date(2026, 10, 12), "subscriptions", "Spotify", "Spotify"),
    ]
    result = generate_insights(expenses, [], [], prefs(), "2026-10", TODAY)
    assert any(r["name"] == "Spotify" and r["cadence"] == "monthly" for r in result["recurring"])
    new = _by_id(result, "recurring-new-spotify")
    assert new and "increased" in new[0]["message"]
    assert not _by_id(result, "recurring-new-netflix")
