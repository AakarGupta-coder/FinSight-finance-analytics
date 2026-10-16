"""Finance assistant: answers supported questions from the user's own records.

All numbers come from trusted backend calculations over data retrieved via
the repository for the authenticated user only. User text is never executed
or turned into database queries; it only selects one of the fixed intents.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from decimal import Decimal

from app.domain.categories import OVERALL_BUDGET_KEY
from app.domain.dates import format_date, month_key, today_in
from app.domain.models import Expense, Preferences
from app.domain.money import divide, format_money, pct_change, percent, round_major, scale, to_minor
from app.repositories.base import Repository
from app.services.anomalies import list_alerts_with_expenses
from app.services.budgets import month_overview
from app.services.goals import goal_metrics
from app.services.preferences import category_names
from app.services.assistant.nlu import Period, ParsedQuery, parse_query
from app.services.simulator import compute_baseline

EXAMPLES = [
    "How much did I spend this month?",
    "How much did I spend on food last month?",
    "Which category increased the most?",
    "What is my remaining monthly budget?",
    "Am I approaching my monthly budget limit?",
    "Which transactions were unusually large?",
    "How much could I save by reducing shopping by 20%?",
    "How much do I need to save each month to reach my goal?",
    "Show expenses between 2026-09-01 and 2026-09-15",
    "What were my largest expenses last month?",
]

DISCLAIMER = "This is an automated summary of your records, not financial advice."


def _reply(answer: str, intent: str, *, period: Period | None = None, data: dict | None = None,
           suggestions: list[str] | None = None, clarification: bool = False) -> dict:
    return {"answer": answer, "intent": intent, "period": period.as_dict() if period else None, "data": data,
            "suggestions": suggestions or [], "needs_clarification": clarification}


def _txn_rows(expenses: list[Expense], names: dict[str, str]) -> list[dict]:
    return [{"id": e.id, "date": e.date.isoformat(), "description": e.description, "merchant": e.merchant,
             "category": e.category, "category_name": names.get(e.category, e.category),
             "amount_minor": e.amount_minor} for e in expenses]


def _previous_period(period: Period, today: dt.date) -> Period:
    """The comparable earlier period: the previous month for month-aligned periods, else equal length."""
    start, end = period.start, period.end
    if start.day == 1:
        prev_month_end = start - dt.timedelta(days=1)
        prev_start = prev_month_end.replace(day=1)
        span_days = (end - start).days
        prev_end = min(prev_start + dt.timedelta(days=span_days), prev_month_end)
        return Period(prev_start, prev_end, f"{format_date(prev_start)} to {format_date(prev_end)}")
    length = (end - start).days + 1
    prev_end = start - dt.timedelta(days=1)
    prev_start = prev_end - dt.timedelta(days=length - 1)
    return Period(prev_start, prev_end, f"{format_date(prev_start)} to {format_date(prev_end)}")


class FinanceAssistant:
    def __init__(self, repo: Repository, prefs: Preferences):
        self.repo = repo
        self.prefs = prefs
        self.user_id = prefs.user_id  # from the authenticated context only
        self.today = today_in(prefs.timezone)
        self.names = category_names(prefs)

    def money(self, amount: int) -> str:
        return format_money(amount, self.prefs.currency)

    def _expenses(self, period: Period) -> list[Expense]:
        return self.repo.list_expenses(self.user_id, period.start, period.end)

    def _default_period(self, parsed: ParsedQuery) -> Period:
        if parsed.period:
            return parsed.period
        start = self.today.replace(day=1)
        return Period(start, self.today, "this month (so far)", explicit=False)

    def _filter(self, expenses: list[Expense], parsed: ParsedQuery) -> list[Expense]:
        if parsed.categories:
            expenses = [e for e in expenses if e.category in parsed.categories]
        if parsed.merchant:
            key = parsed.merchant.lower()
            expenses = [e for e in expenses if (e.merchant or "").lower() == key]
        return expenses

    def _scope(self, parsed: ParsedQuery) -> str:
        text = ""
        if parsed.categories:
            text += " on " + " and ".join(self.names.get(c, c) for c in parsed.categories)
        if parsed.merchant:
            text += f" at {parsed.merchant}"
        return text

    # ------------------------------------------------------------------
    def answer(self, question: str) -> dict:
        question = (question or "").strip()
        if not question:
            return _reply("Please type a question about your spending, budgets or goals.", "empty",
                          suggestions=EXAMPLES[:4])
        merchants = sorted({e.merchant for e in self.repo.list_expenses(self.user_id,
                                                                          self.today - dt.timedelta(days=400),
                                                                          self.today) if e.merchant})
        goals = [g for g in self.repo.list_goals(self.user_id) if not g.archived]
        parsed = parse_query(question, self.today, self.names, merchants, [g.name for g in goals])

        if parsed.vague_time and parsed.intent not in ("help", "unsupported", "goal_requirement"):
            return _reply("Which period do you mean? For example: 'this month', 'last month', "
                          "'the last 30 days' or 'between 2026-09-01 and 2026-09-30'.",
                          parsed.intent, clarification=True,
                          suggestions=[f"{question.rstrip('?')} this month", f"{question.rstrip('?')} last month"])

        handler = getattr(self, f"_handle_{parsed.intent}", self._handle_unsupported)
        return handler(parsed)

    # ------------------------------------------------------------------
    def _handle_help(self, parsed: ParsedQuery) -> dict:
        return _reply("I can answer questions about your recorded expenses, budgets, unusual transactions, "
                      "savings simulations and savings goals. Try one of these:", "help", suggestions=EXAMPLES)

    def _handle_unsupported(self, parsed: ParsedQuery) -> dict:
        return _reply("I can't answer that yet. I only work with the expenses, budgets and savings goals recorded "
                      "in this app (I don't have income, investment or bank data), and I'm not a financial "
                      "advisor. Here are questions I can answer:", "unsupported", suggestions=EXAMPLES[:6])

    def _handle_total_spent(self, parsed: ParsedQuery) -> dict:
        period = self._default_period(parsed)
        items = self._filter(self._expenses(period), parsed)
        scope = self._scope(parsed)
        if not items:
            return _reply(f"No expenses{scope} were recorded for {period.label}.", "total_spent", period=period,
                          data={"kind": "metrics", "total_minor": 0, "count": 0},
                          suggestions=["How much did I spend last month?", "Show my largest expenses this month"])
        total = sum(e.amount_minor for e in items)
        answer = f"You spent {self.money(total)}{scope} for {period.label}, across {len(items)} transaction(s)."
        if not parsed.categories and not parsed.merchant:
            by_cat: dict[str, int] = defaultdict(int)
            for e in items:
                by_cat[e.category] += e.amount_minor
            top, amt = max(by_cat.items(), key=lambda kv: kv[1])
            answer += f" The largest share was {self.names.get(top, top)} ({self.money(amt)}, {percent(amt, total):.0f}%)."
        return _reply(answer, "total_spent", period=period,
                      data={"kind": "metrics", "total_minor": total, "count": len(items)},
                      suggestions=["Which category increased the most?", "What is my remaining monthly budget?"])

    def _handle_transaction_count(self, parsed: ParsedQuery) -> dict:
        period = self._default_period(parsed)
        items = self._filter(self._expenses(period), parsed)
        return _reply(f"You recorded {len(items)} transaction(s){self._scope(parsed)} for {period.label}"
                      + (f", totalling {self.money(sum(e.amount_minor for e in items))}." if items else "."),
                      "transaction_count", period=period, data={"kind": "metrics", "count": len(items)})

    def _handle_average_spending(self, parsed: ParsedQuery) -> dict:
        period = self._default_period(parsed)
        items = self._filter(self._expenses(period), parsed)
        if not items:
            return _reply(f"No expenses{self._scope(parsed)} were recorded for {period.label}, so there is no "
                          "average to calculate.", "average_spending", period=period)
        total = sum(e.amount_minor for e in items)
        days = (period.end - period.start).days + 1
        per_day = divide(total, days)
        per_txn = divide(total, len(items))
        return _reply(f"For {period.label}{self._scope(parsed)}, you spent {self.money(total)} over {days} day(s): "
                      f"an average of {self.money(per_day)} per day and {self.money(per_txn)} per transaction.",
                      "average_spending", period=period,
                      data={"kind": "metrics", "total_minor": total, "average_daily_minor": per_day,
                            "average_transaction_minor": per_txn, "days": days, "count": len(items)})

    def _handle_top_category(self, parsed: ParsedQuery) -> dict:
        period = self._default_period(parsed)
        items = self._expenses(period)
        if not items:
            return _reply(f"No expenses were recorded for {period.label}.", "top_category", period=period)
        by_cat: dict[str, int] = defaultdict(int)
        for e in items:
            by_cat[e.category] += e.amount_minor
        total = sum(by_cat.values())
        rows = sorted(by_cat.items(), key=lambda kv: -kv[1])
        top, amt = rows[0]
        breakdown = [{"category": c, "category_name": self.names.get(c, c), "amount_minor": a,
                      "share_pct": percent(a, total)} for c, a in rows]
        return _reply(f"For {period.label}, your top category was {self.names.get(top, top)} with {self.money(amt)} "
                      f"({percent(amt, total):.0f}% of {self.money(total)}).", "top_category", period=period,
                      data={"kind": "breakdown", "rows": breakdown})

    def _handle_category_change(self, parsed: ParsedQuery) -> dict:
        period = self._default_period(parsed)
        previous = _previous_period(period, self.today)
        cur: dict[str, int] = defaultdict(int)
        prev: dict[str, int] = defaultdict(int)
        for e in self._expenses(period):
            cur[e.category] += e.amount_minor
        for e in self.repo.list_expenses(self.user_id, previous.start, previous.end):
            prev[e.category] += e.amount_minor
        if not cur and not prev:
            return _reply(f"There are no expenses for {period.label} or {previous.label} to compare.",
                          "category_change", period=period)
        if not prev:
            return _reply(f"There are no expenses recorded for the comparison period ({previous.label}), so I "
                          "can't tell which category changed.", "category_change", period=period)
        rows = []
        for cat in set(cur) | set(prev):
            rows.append({"category": cat, "category_name": self.names.get(cat, cat), "current_minor": cur.get(cat, 0),
                         "previous_minor": prev.get(cat, 0), "change_minor": cur.get(cat, 0) - prev.get(cat, 0),
                         "change_pct": pct_change(cur.get(cat, 0), prev.get(cat, 0))})
        wants_decrease = any(w in parsed.text for w in ("decrease", "dropped", "fell", "went down", "reduced"))
        rows.sort(key=lambda r: r["change_minor"], reverse=not wants_decrease)
        best = rows[0]
        if (best["change_minor"] <= 0 and not wants_decrease) or (best["change_minor"] >= 0 and wants_decrease):
            word = "increased" if not wants_decrease else "decreased"
            return _reply(f"No category {word} between {previous.label} and {period.label}.", "category_change",
                          period=period, data={"kind": "comparison", "rows": rows, "previous_period": previous.as_dict()})
        pct = f" ({abs(best['change_pct']):.0f}%)" if best["change_pct"] is not None else " (no spending before)"
        verb = "decreased" if wants_decrease else "increased"
        return _reply(f"{best['category_name']} {verb} the most: {self.money(best['previous_minor'])} during "
                      f"{previous.label} to {self.money(best['current_minor'])} during {period.label}, a change of "
                      f"{self.money(abs(best['change_minor']))}{pct}.", "category_change", period=period,
                      data={"kind": "comparison", "rows": rows[:6], "previous_period": previous.as_dict()})

    def _budget_overview(self) -> dict:
        return month_overview(self.repo, self.prefs, month_key(self.today), record_events=False)

    def _handle_budget_remaining(self, parsed: ParsedQuery) -> dict:
        overview = self._budget_overview()
        period = Period(self.today.replace(day=1), self.today, "this month (so far)")
        if parsed.categories:
            rows = [c for c in overview["categories"] if c["category"] in parsed.categories]
            if not rows:
                return _reply(f"You haven't set a budget for {self.names.get(parsed.categories[0])}. "
                              "You can add one on the Budgets page.", "budget_remaining", period=period)
            row = rows[0]
        else:
            row = overview["overall"]
            if not row:
                return _reply("You haven't set an overall monthly budget yet. Add one on the Budgets page to track "
                              f"what's left. So far this month you've spent {self.money(overview['total_spent_minor'])}.",
                              "budget_remaining", period=period)
        remaining = row["remaining_minor"]
        name = row["category_name"]
        if remaining >= 0:
            msg = (f"You have {self.money(remaining)} left in your {name.lower() if name == 'Overall' else name} "
                   f"budget of {self.money(row['amount_minor'])} this month ({row['utilization_pct'] or 0:.0f}% used).")
            if row.get("daily_allowance_minor") is not None:
                days_left = row["days_in_month"] - row["days_elapsed"] + 1
                msg += f" That's about {self.money(row['daily_allowance_minor'])} per day for the remaining {days_left} day(s)."
        else:
            msg = (f"You are {self.money(-remaining)} over your {name.lower() if name == 'Overall' else name} budget of "
                   f"{self.money(row['amount_minor'])} this month.")
        return _reply(msg, "budget_remaining", period=period, data={"kind": "budget", "row": row})

    def _handle_budget_status(self, parsed: ParsedQuery) -> dict:
        overview = self._budget_overview()
        period = Period(self.today.replace(day=1), self.today, "this month (so far)")
        rows = ([overview["overall"]] if overview["overall"] else []) + overview["categories"]
        if parsed.categories:
            rows = [r for r in rows if r["category"] in parsed.categories]
        if not rows:
            return _reply("You don't have a matching budget set for this month, so I can't check your limit. "
                          "Add budgets on the Budgets page.", "budget_status", period=period)
        lines = []
        for r in rows[:5]:
            util = r["utilization_pct"]
            util_text = f"{util:.0f}% used" if util is not None else "zero budget"
            if r["status"] == "exceeded":
                state = f"exceeded by {self.money(-r['remaining_minor'])}"
            elif r["status"] == "at_limit":
                state = "at the limit"
            elif r["projected_overrun"]:
                state = f"on pace to exceed it (projected {self.money(r['projected_spend_minor'])})"
            elif r["status"] == "warning":
                state = "approaching the limit"
            else:
                state = "within budget"
            lines.append(f"{r['category_name']}: {self.money(r['spent_minor'])} of {self.money(r['amount_minor'])} "
                         f"({util_text}) - {state}.")
        flagged = [r for r in rows if r["status"] in ("exceeded", "at_limit", "warning") or r["projected_overrun"]]
        head = ("Yes - some budgets need attention." if flagged else "You're within your budgets so far.")
        return _reply(head + " " + " ".join(lines) + " Projections assume your current daily pace continues.",
                      "budget_status", period=period, data={"kind": "budgets", "rows": rows[:5]})

    def _handle_unusual_transactions(self, parsed: ParsedQuery) -> dict:
        alerts = [a for a in list_alerts_with_expenses(self.repo, self.prefs, None)
                  if a["status"] in ("open", "reviewed") and a["expense"]]
        if parsed.period:
            alerts = [a for a in alerts if parsed.period.start.isoformat() <= a["expense"]["date"] <= parsed.period.end.isoformat()]
        if parsed.categories:
            alerts = [a for a in alerts if a["expense"]["category"] in parsed.categories]
        if not alerts:
            return _reply("No unusual transactions are currently flagged" + (f" for {parsed.period.label}" if parsed.period else "")
                          + ". Detection compares each transaction with your typical spending in its category.",
                          "unusual_transactions", period=parsed.period,
                          suggestions=["What were my largest expenses this month?"])
        rows = [{**a["expense"], "reason": a["reason"], "severity": a["severity"], "alert_id": a["id"]} for a in alerts[:8]]
        return _reply(f"{len(alerts)} transaction(s) are flagged for review. These are unusual compared with your "
                      "history - not necessarily wrong. Top items:", "unusual_transactions", period=parsed.period,
                      data={"kind": "transactions", "rows": rows})

    def _handle_largest_transactions(self, parsed: ParsedQuery) -> dict:
        period = self._default_period(parsed)
        items = sorted(self._filter(self._expenses(period), parsed), key=lambda e: -e.amount_minor)
        limit = min(parsed.limit or 5, 20)
        if not items:
            return _reply(f"No expenses{self._scope(parsed)} were recorded for {period.label}.", "largest_transactions",
                          period=period)
        top = items[:limit]
        return _reply(f"Your {len(top)} largest expense(s){self._scope(parsed)} for {period.label}:",
                      "largest_transactions", period=period, data={"kind": "transactions", "rows": _txn_rows(top, self.names)})

    def _handle_list_transactions(self, parsed: ParsedQuery) -> dict:
        period = self._default_period(parsed)
        items = sorted(self._filter(self._expenses(period), parsed), key=lambda e: (e.date, e.created_at), reverse=True)
        if not items:
            return _reply(f"No expenses{self._scope(parsed)} were recorded for {period.label}.", "list_transactions",
                          period=period)
        total = sum(e.amount_minor for e in items)
        shown = items[:20]
        more = f" Showing the latest {len(shown)}." if len(items) > len(shown) else ""
        note = "" if parsed.period else " (No period was given, so I used this month.)"
        return _reply(f"{len(items)} expense(s){self._scope(parsed)} for {period.label}, totalling {self.money(total)}.{more}{note}",
                      "list_transactions", period=period, data={"kind": "transactions", "rows": _txn_rows(shown, self.names)})

    def _handle_simulate_saving(self, parsed: ParsedQuery) -> dict:
        if not parsed.categories:
            return _reply("Which category would you reduce? For example: 'How much could I save by reducing "
                          "shopping by 20%?'", "simulate_saving", clarification=True,
                          suggestions=["How much could I save by reducing food by 20%?",
                                       "How much could I save by reducing shopping by ₹1,000?"])
        start = self.today.replace(day=1)
        history = self.repo.list_expenses(self.user_id, dt.date(start.year - 1, start.month, 1), self.today)
        baseline, info = compute_baseline(history, "avg_3_months", self.today)
        if info["months"] == 0:
            baseline, info = compute_baseline(history, "current_month_projection", self.today)
        rows, total_saving = [], 0
        for cat in parsed.categories:
            current = baseline.get(cat, 0)
            if parsed.amount is not None:
                reduction = min(to_minor(parsed.amount, self.prefs.currency), current)
                desc = f"by {self.money(to_minor(parsed.amount, self.prefs.currency))}"
            else:
                pct = parsed.percent if parsed.percent is not None else Decimal(10)
                if pct > 100:
                    return _reply("A reduction can't be more than 100%.", "simulate_saving", clarification=True)
                reduction = scale(current, pct / 100)
                desc = f"by {pct.normalize():f}%"
            total_saving += reduction
            rows.append({"category": cat, "category_name": self.names.get(cat, cat), "current_minor": current,
                         "monthly_savings_minor": reduction, "new_minor": current - reduction})
        if all(r["current_minor"] == 0 for r in rows):
            return _reply(f"You have no recent spending in {', '.join(r['category_name'] for r in rows)}, so reducing "
                          "it wouldn't save anything based on your records.", "simulate_saving")
        default_note = "" if (parsed.percent is not None or parsed.amount is not None) else " (I assumed a 10% reduction.)"
        names = " and ".join(r["category_name"] for r in rows)
        current_total = sum(r["current_minor"] for r in rows)
        return _reply(f"Reducing {names} {desc} from about {self.money(current_total)} per month "
                      f"({info['label'].lower()}) would save roughly {self.money(total_saving)} per month, or "
                      f"{self.money(total_saving * 12)} per year if the change lasts 12 months.{default_note}",
                      "simulate_saving",
                      data={"kind": "simulation", "rows": rows, "monthly_savings_minor": total_saving,
                            "annual_savings_minor": total_saving * 12, "baseline": info},
                      suggestions=["Open the What-If simulator to compare scenarios"])

    def _handle_goal_requirement(self, parsed: ParsedQuery) -> dict:
        goals = [g for g in self.repo.list_goals(self.user_id) if not g.archived]
        if not goals:
            return _reply("You don't have any savings goals yet. Create one on the Goals page and I can tell you "
                          "how much to save each month.", "goal_requirement")
        goal = None
        if parsed.goal_hint:
            goal = next((g for g in goals if g.name == parsed.goal_hint), None)
        if goal is None:
            open_goals = [g for g in goals if g.saved_minor < g.target_minor]
            if len(open_goals) == 1:
                goal = open_goals[0]
            elif not open_goals:
                return _reply("All of your savings goals are already complete.", "goal_requirement")
            else:
                return _reply("Which goal do you mean? You have: " + ", ".join(f"'{g.name}'" for g in open_goals) + ".",
                              "goal_requirement", clarification=True,
                              suggestions=[f"How much do I need to save each month for {g.name}?" for g in open_goals[:3]])
        m = goal_metrics(goal, self.today)
        if m["completed"]:
            return _reply(f"'{goal.name}' is complete: you've saved {self.money(goal.saved_minor)} of "
                          f"{self.money(goal.target_minor)}.", "goal_requirement")
        if m["required_monthly_minor"] is None:
            if goal.target_date and goal.target_date <= self.today:
                return _reply(f"The target date for '{goal.name}' ({format_date(goal.target_date)}) has passed with "
                              f"{self.money(m['remaining_minor'])} still to save. Set a new target date to get a monthly figure.",
                              "goal_requirement")
            return _reply(f"'{goal.name}' has no target date, so there's no monthly requirement. You still need "
                          f"{self.money(m['remaining_minor'])}. Add a target date on the Goals page.", "goal_requirement")
        msg = (f"To reach '{goal.name}' ({self.money(goal.target_minor)}) by {format_date(goal.target_date)}, you need to "
               f"save about {self.money(m['required_monthly_minor'])} per month for the next {m['months_left']:.1f} month(s). "
               f"You've saved {self.money(goal.saved_minor)} so far ({m['progress_pct']:.0f}%).")
        if m["recent_monthly_contribution_minor"]:
            msg += f" Your recent contributions average about {self.money(round_major(m['recent_monthly_contribution_minor'], self.prefs.currency))} per month."
        return _reply(msg, "goal_requirement", data={"kind": "goal", "goal_id": goal.id, **m})


def answer_question(repo: Repository, prefs: Preferences, question: str) -> dict:
    result = FinanceAssistant(repo, prefs).answer(question)
    result["disclaimer"] = DISCLAIMER
    return result
