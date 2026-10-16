"""User preferences and category configuration."""

from __future__ import annotations

import re

from app.domain.categories import DEFAULT_CATEGORIES, DEFAULT_CATEGORY_IDS
from app.domain.dates import is_valid_timezone, utc_now
from app.domain.models import CustomCategory, Preferences
from app.domain.money import SUPPORTED_CURRENCIES
from app.errors import Conflict, NotFound, ValidationFailed
from app.repositories.base import Repository


def get_or_create_preferences(repo: Repository, user_id: str, default_name: str | None = None) -> Preferences:
    prefs = repo.get_preferences(user_id)
    if prefs is None:
        prefs = Preferences(user_id=user_id, display_name=default_name)
        repo.put_preferences(prefs)
    return prefs


def all_categories(prefs: Preferences) -> list[dict]:
    return [dict(c, custom=False) for c in DEFAULT_CATEGORIES] + [
        {"id": c.id, "name": c.name, "custom": True} for c in prefs.custom_categories
    ]


def category_ids(prefs: Preferences) -> set[str]:
    return DEFAULT_CATEGORY_IDS | {c.id for c in prefs.custom_categories}


def category_names(prefs: Preferences) -> dict[str, str]:
    return {c["id"]: c["name"] for c in all_categories(prefs)}


def update_preferences(repo: Repository, prefs: Preferences, changes: dict) -> Preferences:
    data = prefs.model_dump()
    if "currency" in changes and changes["currency"] is not None:
        if changes["currency"] not in SUPPORTED_CURRENCIES:
            raise ValidationFailed("Unsupported currency.")
    if "timezone" in changes and changes["timezone"] is not None:
        if not is_valid_timezone(changes["timezone"]):
            raise ValidationFailed("Unknown timezone.")
    if "budget_thresholds" in changes and changes["budget_thresholds"] is not None:
        thresholds = sorted(set(int(t) for t in changes["budget_thresholds"]))
        if not thresholds or len(thresholds) > 5 or any(t < 1 or t > 200 for t in thresholds):
            raise ValidationFailed("Provide 1-5 alert thresholds between 1 and 200 percent.")
        changes["budget_thresholds"] = thresholds
    for key, value in changes.items():
        if value is not None and key in data:
            data[key] = value
    data["updated_at"] = utc_now()
    updated = Preferences.model_validate(data)
    repo.put_preferences(updated)
    return updated


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug[:40]


def add_custom_category(repo: Repository, prefs: Preferences, name: str) -> Preferences:
    name = name.strip()
    if not (1 <= len(name) <= 40):
        raise ValidationFailed("Category name must be 1-40 characters.")
    slug = _slugify(name)
    if not slug:
        raise ValidationFailed("Category name must contain letters or numbers.")
    existing_names = {c["name"].lower() for c in all_categories(prefs)}
    if slug in category_ids(prefs) or name.lower() in existing_names:
        raise Conflict("A category with this name already exists.")
    if len(prefs.custom_categories) >= 30:
        raise ValidationFailed("You can create up to 30 custom categories.")
    prefs.custom_categories.append(CustomCategory(id=slug, name=name))
    prefs.updated_at = utc_now()
    repo.put_preferences(prefs)
    return prefs


def remove_custom_category(repo: Repository, prefs: Preferences, category_id: str) -> int:
    """Remove a custom category; its expenses move to 'other'. Returns moved count."""
    if category_id in DEFAULT_CATEGORY_IDS:
        raise ValidationFailed("Built-in categories cannot be removed.")
    if category_id not in {c.id for c in prefs.custom_categories}:
        raise NotFound("Category not found.")
    moved = 0
    for expense in repo.list_expenses(prefs.user_id):
        if expense.category == category_id:
            expense.category = "other"
            expense.updated_at = utc_now()
            repo.put_expense(expense)
            moved += 1
    for budget in repo.list_budgets(prefs.user_id):
        if budget.category == category_id:
            repo.delete_budget(prefs.user_id, budget.id)
    prefs.custom_categories = [c for c in prefs.custom_categories if c.id != category_id]
    prefs.updated_at = utc_now()
    repo.put_preferences(prefs)
    return moved
