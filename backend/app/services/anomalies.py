"""Financial anomaly detection.

Flags transactions that *deserve review*. It never claims fraud, never
modifies or deletes transactions, and keeps detection (pure functions over a
list of expenses) separate from persistence and the UI.

Signals
-------
* category_outlier  - amount far above the user's typical amount in the same
                      category, measured with the median and the median
                      absolute deviation (robust to skew and small samples).
* overall_outlier   - for categories with little history: amount far above
                      the user's typical transaction overall.
* duplicate         - same amount and merchant/description within 1 day.
* repeated_similar  - 3+ transactions at the same merchant on the same day.
* category_spike    - a category's monthly spending far above its recent
                      monthly average.
"""

from __future__ import annotations

import datetime as dt
import re
import statistics
from collections import defaultdict
from dataclasses import dataclass, field

from app.domain.dates import month_bounds, month_key, month_label, shift_month, today_in, utc_now
from app.domain.models import AnomalyAlert, Expense, Preferences
from app.domain.money import format_money
from app.errors import NotFound, ValidationFailed
from app.repositories.base import Repository
from app.services.preferences import category_names

MIN_CATEGORY_SAMPLES = 5
MIN_OVERALL_SAMPLES = 10
LOOKBACK_DAYS = 365
SCAN_DAYS = 180


@dataclass(frozen=True)
class Sensitivity:
    robust_z: float
    ratio: float
    overall_ratio: float
    spike_ratio: float


SENSITIVITY = {
    "conservative": Sensitivity(robust_z=5.0, ratio=3.0, overall_ratio=6.0, spike_ratio=2.25),
    "balanced": Sensitivity(robust_z=3.5, ratio=2.5, overall_ratio=5.0, spike_ratio=1.75),
    "sensitive": Sensitivity(robust_z=3.0, ratio=2.0, overall_ratio=4.0, spike_ratio=1.5),
}


@dataclass
class Finding:
    rule: str
    expense_id: str
    dedup_key: str
    severity: str
    reason: str
    comparison: dict = field(default_factory=dict)


def _norm(text: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _identity(e: Expense) -> str:
    return _norm(e.merchant) or _norm(e.description)


def robust_z(value: float, sample: list[int]) -> tuple[float | None, float, float]:
    """Modified z-score (Iglewicz & Hoaglin): 0.6745 * (x - median) / MAD."""
    median = statistics.median(sample)
    mad = statistics.median([abs(x - median) for x in sample])
    if mad == 0:
        return None, median, mad
    return 0.6745 * (value - median) / mad, median, mad


def _percentile(sample: list[int], pct: float) -> float:
    ordered = sorted(sample)
    if len(ordered) == 1:
        return ordered[0]
    k = (len(ordered) - 1) * pct
    lo, hi = int(k), min(int(k) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def detect_amount_outlier(target: Expense, history: list[Expense], cfg: Sensitivity, currency: str,
                          names: dict[str, str]) -> Finding | None:
    window_start = target.date - dt.timedelta(days=LOOKBACK_DAYS)
    others = [e for e in history if e.id != target.id and window_start <= e.date <= target.date + dt.timedelta(days=LOOKBACK_DAYS)]
    same_cat = [e.amount_minor for e in others if e.category == target.category]
    cat_name = names.get(target.category, target.category)
    money = lambda v: format_money(int(round(v)), currency)  # noqa: E731

    if len(same_cat) >= MIN_CATEGORY_SAMPLES:
        z, median, mad = robust_z(target.amount_minor, same_cat)
        ratio = target.amount_minor / median if median else None
        if ratio is None or ratio < cfg.ratio:
            return None
        if z is not None and z < cfg.robust_z:
            return None
        # Repeated large transactions in the same category within 30 days escalate severity.
        recent_large = [e for e in others if e.category == target.category
                        and abs((e.date - target.date).days) <= 30 and e.amount_minor >= cfg.ratio * median]
        severity = "high" if ratio >= cfg.ratio * 2 or recent_large else "medium"
        reason = (f"{money(target.amount_minor)} is {ratio:.1f}x your typical {cat_name} transaction "
                  f"({money(median)}, median of {len(same_cat)}).")
        if recent_large:
            reason += f" This is one of {len(recent_large) + 1} unusually large {cat_name} transactions within 30 days."
        return Finding("category_outlier", target.id, f"category_outlier:{target.id}", severity, reason, {
            "category": target.category, "amount_minor": target.amount_minor, "median_minor": median,
            "mad_minor": mad, "robust_z": round(z, 2) if z is not None else None, "ratio": round(ratio, 2),
            "sample_size": len(same_cat), "p90_minor": round(_percentile(same_cat, 0.9)),
            "method": "median & median absolute deviation" if z is not None else "ratio to median (MAD = 0)",
            "related_expense_ids": [e.id for e in recent_large],
        })

    # Too little category history: compare against all spending, conservatively.
    all_amounts = [e.amount_minor for e in others]
    if len(all_amounts) < MIN_OVERALL_SAMPLES:
        return None
    # Similar amounts already seen in this category -> probably normal for the user (e.g. rent).
    if any(abs(a - target.amount_minor) <= 0.5 * target.amount_minor for a in same_cat):
        return None
    median = statistics.median(all_amounts)
    p95 = _percentile(all_amounts, 0.95)
    if target.amount_minor >= max(cfg.overall_ratio * median, 1.5 * p95):
        ratio = target.amount_minor / median if median else 0
        return Finding("overall_outlier", target.id, f"overall_outlier:{target.id}", "low",
                       f"{money(target.amount_minor)} is {ratio:.1f}x your typical transaction ({money(median)}) and "
                       f"above 1.5x your 95th percentile ({money(p95)}). There is limited {cat_name} history "
                       "to compare against.", {
                           "amount_minor": target.amount_minor, "median_minor": median, "p95_minor": round(p95),
                           "ratio": round(ratio, 2), "sample_size": len(all_amounts),
                           "category_sample_size": len(same_cat), "method": "ratio to overall median and 95th percentile",
                       })
    return None


def detect_duplicate(target: Expense, history: list[Expense], currency: str) -> Finding | None:
    ident = _identity(target)
    if not ident:
        return None
    matches = [
        e for e in history
        if e.id != target.id and e.amount_minor == target.amount_minor and _identity(e) == ident
        and abs((e.date - target.date).days) <= 1
    ]
    # Flag only the later entry of a pair so one duplicate creates one alert.
    earlier = [e for e in matches if (e.date, e.created_at, e.id) < (target.date, target.created_at, target.id)]
    if not earlier:
        return None
    original = earlier[0]
    return Finding("duplicate", target.id, f"duplicate:{target.id}", "medium",
                   f"Possible duplicate: same amount ({format_money(target.amount_minor, currency)}) and "
                   f"merchant/description as a transaction on {original.date.isoformat()}.",
                   {"amount_minor": target.amount_minor, "matching_expense_ids": [e.id for e in earlier],
                    "window_days": 1})


def detect_repeated_similar(target: Expense, history: list[Expense]) -> Finding | None:
    ident = _norm(target.merchant)
    if not ident:
        return None
    same_day = [e for e in history if e.date == target.date and _norm(e.merchant) == ident]
    if target.id not in {e.id for e in same_day}:
        same_day.append(target)
    if len(same_day) < 3:
        return None
    ordered = sorted(same_day, key=lambda e: (e.created_at, e.id))
    if ordered[-1].id != target.id:
        return None  # alert once, on the latest of the group
    return Finding("repeated_similar", target.id, f"repeated_similar:{target.merchant and ident}:{target.date}",
                   "low", f"{len(same_day)} transactions at {target.merchant} on {target.date.isoformat()}.",
                   {"count": len(same_day), "expense_ids": [e.id for e in ordered],
                    "total_minor": sum(e.amount_minor for e in same_day)})


def detect_category_spikes(expenses: list[Expense], month: str, cfg: Sensitivity, currency: str,
                           names: dict[str, str]) -> list[Finding]:
    start, end = month_bounds(month)
    current = [e for e in expenses if start <= e.date <= end]
    by_cat: dict[str, list[Expense]] = defaultdict(list)
    for e in current:
        by_cat[e.category].append(e)
    findings = []
    for cat, items in by_cat.items():
        prior_totals = []
        for i in (1, 2, 3):
            p_start, p_end = month_bounds(shift_month(month, -i))
            prior_totals.append(sum(e.amount_minor for e in expenses if e.category == cat and p_start <= e.date <= p_end))
        months_with_spend = [t for t in prior_totals if t > 0]
        if len(months_with_spend) < 2:
            continue
        avg = sum(months_with_spend) / len(months_with_spend)
        cur_total = sum(e.amount_minor for e in items)
        if cur_total < cfg.spike_ratio * avg:
            continue
        largest = max(items, key=lambda e: e.amount_minor)
        ratio = cur_total / avg
        findings.append(Finding(
            "category_spike", largest.id, f"category_spike:{cat}:{month}", "high" if ratio >= 3 else "medium",
            f"{names.get(cat, cat)} spending in {month_label(month)} is {format_money(cur_total, currency)}, {ratio:.1f}x the "
            f"recent monthly average of {format_money(int(avg), currency)}. This is the largest transaction in that category.",
            {"category": cat, "month": month, "month_total_minor": cur_total, "average_minor": int(avg),
             "ratio": round(ratio, 2), "months_compared": len(months_with_spend),
             "expense_ids": [e.id for e in sorted(items, key=lambda e: -e.amount_minor)[:10]]},
        ))
    return findings


def detect_for_expense(target: Expense, history: list[Expense], sensitivity: str, currency: str,
                       names: dict[str, str]) -> list[Finding]:
    cfg = SENSITIVITY.get(sensitivity, SENSITIVITY["balanced"])
    findings = []
    for result in (
        detect_amount_outlier(target, history, cfg, currency, names),
        detect_duplicate(target, history, currency),
        detect_repeated_similar(target, history),
    ):
        if result:
            findings.append(result)
    return findings


# ---- persistence / orchestration ----

def _store(repo: Repository, user_id: str, findings: list[Finding], is_demo: bool = False) -> int:
    created = 0
    for f in findings:
        alert = AnomalyAlert(user_id=user_id, expense_id=f.expense_id, rule=f.rule, dedup_key=f.dedup_key,
                             severity=f.severity, reason=f.reason, comparison=f.comparison, is_demo=is_demo)
        if repo.create_alert_if_absent(alert):
            created += 1
    return created


def scan_expense(repo: Repository, prefs: Preferences, expense: Expense) -> int:
    """Run detection for one new/updated transaction. Returns alerts created."""
    month = month_key(expense.date)
    # Clear open alerts that this change may resolve: the transaction's own
    # alerts, and open category-spike alerts for its month (totals changed).
    for alert in repo.list_alerts(prefs.user_id):
        if alert.status != "open":
            continue
        if alert.rule == "category_spike":
            if alert.comparison.get("month") == month:
                repo.delete_alert(prefs.user_id, alert.id)
        elif alert.expense_id == expense.id:
            repo.delete_alert(prefs.user_id, alert.id)
    start = expense.date - dt.timedelta(days=LOOKBACK_DAYS)
    history = repo.list_expenses(prefs.user_id, start, expense.date + dt.timedelta(days=LOOKBACK_DAYS))
    names = category_names(prefs)
    findings = detect_for_expense(expense, history, prefs.anomaly_sensitivity, prefs.currency, names)
    cfg = SENSITIVITY.get(prefs.anomaly_sensitivity, SENSITIVITY["balanced"])
    findings += detect_category_spikes(history, month, cfg, prefs.currency, names)
    return _store(repo, prefs.user_id, findings, expense.is_demo)


def refresh_category_spikes(repo: Repository, prefs: Preferences, day: dt.date) -> int:
    """Re-evaluate category-spike alerts for a month after a transaction is removed."""
    month = month_key(day)
    for alert in repo.list_alerts(prefs.user_id):
        if alert.status == "open" and alert.rule == "category_spike" and alert.comparison.get("month") == month:
            repo.delete_alert(prefs.user_id, alert.id)
    start = month_bounds(shift_month(month, -3))[0]
    expenses = repo.list_expenses(prefs.user_id, start, month_bounds(month)[1])
    cfg = SENSITIVITY.get(prefs.anomaly_sensitivity, SENSITIVITY["balanced"])
    return _store(repo, prefs.user_id, detect_category_spikes(expenses, month, cfg, prefs.currency, category_names(prefs)))


def scan_all(repo: Repository, prefs: Preferences) -> dict:
    today = today_in(prefs.timezone)
    start = today - dt.timedelta(days=SCAN_DAYS + LOOKBACK_DAYS)
    expenses = repo.list_expenses(prefs.user_id, start, today)
    names = category_names(prefs)
    scan_from = today - dt.timedelta(days=SCAN_DAYS)
    findings: list[Finding] = []
    for e in expenses:
        if e.date >= scan_from:
            findings += detect_for_expense(e, expenses, prefs.anomaly_sensitivity, prefs.currency, names)
    cfg = SENSITIVITY.get(prefs.anomaly_sensitivity, SENSITIVITY["balanced"])
    for i in range(0, 3):
        findings += detect_category_spikes(expenses, shift_month(month_key(today), -i), cfg, prefs.currency, names)
    created = _store(repo, prefs.user_id, findings)
    return {"scanned": sum(1 for e in expenses if e.date >= scan_from), "findings": len(findings), "created": created}


REVIEW_ACTIONS = {"reviewed", "legitimate", "dismissed", "open"}


def review_alert(repo: Repository, user_id: str, alert_id: str, action: str, note: str | None) -> AnomalyAlert:
    if action not in REVIEW_ACTIONS:
        raise ValidationFailed("Action must be reviewed, legitimate, dismissed or open.")
    alert = repo.get_alert(user_id, alert_id)
    if not alert:
        raise NotFound("Alert not found.")
    alert.status = action  # type: ignore[assignment]
    alert.status_updated_at = utc_now()
    alert.note = (note or "").strip()[:300] or alert.note
    repo.put_alert(alert)
    return alert


def list_alerts_with_expenses(repo: Repository, prefs: Preferences, status: str | None = None) -> list[dict]:
    alerts = repo.list_alerts(prefs.user_id)
    if status and status != "all":
        alerts = [a for a in alerts if a.status == status]
    names = category_names(prefs)
    expenses = {e.id: e for e in repo.list_expenses(prefs.user_id)} if alerts else {}
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    rows = []
    for a in sorted(alerts, key=lambda a: (a.status != "open", severity_rank[a.severity], -a.detected_at.timestamp())):
        e = expenses.get(a.expense_id)
        row = a.model_dump(mode="json")
        row["expense"] = (
            {"id": e.id, "description": e.description, "merchant": e.merchant, "amount_minor": e.amount_minor,
             "date": e.date.isoformat(), "category": e.category, "category_name": names.get(e.category, e.category),
             "payment_method": e.payment_method}
            if e else None
        )
        rows.append(row)
    return rows
