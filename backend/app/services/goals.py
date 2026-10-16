"""Savings goals: CRUD, contributions and progress metrics."""

from __future__ import annotations

import datetime as dt
import math

from app.domain.dates import add_months, months_until, today_in, utc_now
from app.domain.models import Goal, GoalContribution, Preferences
from app.domain.money import MAX_AMOUNT_MINOR, divide, percent
from app.errors import NotFound, ValidationFailed
from app.repositories.base import Repository


def _validate(name: str, target_minor: int, saved_minor: int, target_date: dt.date | None, today: dt.date,
              *, is_new: bool) -> str:
    name = " ".join((name or "").split())
    errors = []
    if not (1 <= len(name) <= 80):
        errors.append({"field": "name", "message": "Goal name must be 1-80 characters."})
    if not isinstance(target_minor, int) or target_minor <= 0:
        errors.append({"field": "target_minor", "message": "Target amount must be greater than zero."})
    elif target_minor > MAX_AMOUNT_MINOR:
        errors.append({"field": "target_minor", "message": "Target amount is unrealistically large."})
    if not isinstance(saved_minor, int) or saved_minor < 0:
        errors.append({"field": "saved_minor", "message": "Saved amount cannot be negative."})
    if is_new and target_date is not None and target_date <= today:
        errors.append({"field": "target_date", "message": "Target date must be in the future."})
    if errors:
        raise ValidationFailed(errors[0]["message"], details=errors)
    return name


def is_starting_balance(contribution: GoalContribution) -> bool:
    return contribution.kind == "starting_balance" or (
        # Records created before `kind` existed were tagged only by their note.
        contribution.kind == "contribution" and contribution.note == "Starting balance"
    )


def goal_metrics(goal: Goal, today: dt.date) -> dict:
    remaining = max(goal.target_minor - goal.saved_minor, 0)
    progress = percent(min(goal.saved_minor, goal.target_minor), goal.target_minor) or 0.0
    completed = goal.saved_minor >= goal.target_minor
    required_monthly = None
    months_left = None
    overdue = False
    if goal.target_date and not completed:
        if goal.target_date <= today:
            overdue = True
        else:
            months_left = round(months_until(today, goal.target_date), 1)
            # At least one month so that very near dates don't divide by tiny numbers.
            required_monthly = divide(remaining, max(1, math.ceil(months_until(today, goal.target_date))))

    # Actual contribution pace over the last 90 days (contributions only, never expenses).
    # The starting balance entered when the goal was created is not part of the pace.
    regular = [c for c in goal.contributions if not is_starting_balance(c)]
    window_start = today - dt.timedelta(days=90)
    recent = sum(c.amount_minor for c in regular if window_start < c.date <= today)
    recent_monthly = divide(max(recent, 0), 3) if recent > 0 else 0
    projected_completion = None
    if not completed and recent_monthly > 0:
        projected_completion = add_months(today, math.ceil(remaining / recent_monthly)).isoformat()

    if goal.archived:
        status = "archived"
    elif completed:
        status = "completed"
    elif overdue:
        status = "overdue"
    elif required_monthly is not None and recent_monthly < required_monthly:
        status = "behind" if regular else "not_started"
    else:
        status = "on_track" if regular or goal.saved_minor else "not_started"

    return {
        "remaining_minor": remaining,
        "progress_pct": progress,
        "status": status,
        "completed": completed,
        "months_left": months_left,
        "required_monthly_minor": required_monthly,
        "recent_monthly_contribution_minor": recent_monthly,
        "projected_completion_date": projected_completion,
    }


def serialize_goal(goal: Goal, today: dt.date) -> dict:
    data = goal.model_dump(mode="json")
    data["contributions"] = sorted(data["contributions"], key=lambda c: (c["date"], c["created_at"]), reverse=True)
    data.update(goal_metrics(goal, today))
    return data


def create_goal(repo: Repository, prefs: Preferences, name: str, target_minor: int, saved_minor: int,
                target_date: dt.date | None, *, is_demo: bool = False) -> Goal:
    today = today_in(prefs.timezone)
    name = _validate(name, target_minor, saved_minor, target_date, today, is_new=True)
    goal = Goal(user_id=prefs.user_id, name=name, target_minor=target_minor, saved_minor=saved_minor,
                target_date=target_date, is_demo=is_demo)
    if saved_minor > 0:
        goal.contributions.append(GoalContribution(amount_minor=saved_minor, date=today, note="Starting balance",
                                                   kind="starting_balance"))
    repo.put_goal(goal)
    return goal


def get_goal(repo: Repository, user_id: str, goal_id: str) -> Goal:
    goal = repo.get_goal(user_id, goal_id)
    if not goal:
        raise NotFound("Goal not found.")
    return goal


def update_goal(repo: Repository, prefs: Preferences, goal_id: str, *, name: str | None = None,
                target_minor: int | None = None, target_date: dt.date | None = None,
                clear_target_date: bool = False, archived: bool | None = None) -> Goal:
    goal = get_goal(repo, prefs.user_id, goal_id)
    today = today_in(prefs.timezone)
    new_date = None if clear_target_date else (target_date if target_date is not None else goal.target_date)
    if target_date is not None and target_date != goal.target_date and target_date <= today:
        raise ValidationFailed("Target date must be in the future.")
    goal.name = _validate(name if name is not None else goal.name,
                          target_minor if target_minor is not None else goal.target_minor,
                          goal.saved_minor, None, today, is_new=False)
    if target_minor is not None:
        goal.target_minor = target_minor
    goal.target_date = new_date
    if archived is not None:
        goal.archived = archived
    goal.updated_at = utc_now()
    repo.put_goal(goal)
    return goal


def add_contribution(repo: Repository, prefs: Preferences, goal_id: str, amount_minor: int,
                     day: dt.date | None, note: str | None) -> Goal:
    goal = get_goal(repo, prefs.user_id, goal_id)
    today = today_in(prefs.timezone)
    day = day or today
    if not isinstance(amount_minor, int) or amount_minor == 0:
        raise ValidationFailed("Contribution amount must be non-zero.")
    if abs(amount_minor) > MAX_AMOUNT_MINOR:
        raise ValidationFailed("Contribution amount is unrealistically large.")
    if day > today:
        raise ValidationFailed("Contribution date cannot be in the future.")
    if goal.saved_minor + amount_minor < 0:
        raise ValidationFailed("Withdrawal exceeds the amount saved for this goal.")
    goal.contributions.append(GoalContribution(amount_minor=amount_minor, date=day,
                                               note=(note or "").strip()[:200] or None))
    goal.saved_minor += amount_minor
    goal.updated_at = utc_now()
    repo.put_goal(goal)
    return goal


def delete_contribution(repo: Repository, prefs: Preferences, goal_id: str, contribution_id: str) -> Goal:
    goal = get_goal(repo, prefs.user_id, goal_id)
    match = next((c for c in goal.contributions if c.id == contribution_id), None)
    if not match:
        raise NotFound("Contribution not found.")
    if goal.saved_minor - match.amount_minor < 0:
        raise ValidationFailed("Removing this entry would make the saved amount negative.")
    goal.contributions = [c for c in goal.contributions if c.id != contribution_id]
    goal.saved_minor -= match.amount_minor
    goal.updated_at = utc_now()
    repo.put_goal(goal)
    return goal


def delete_goal(repo: Repository, user_id: str, goal_id: str) -> None:
    if not repo.delete_goal(user_id, goal_id):
        raise NotFound("Goal not found.")
