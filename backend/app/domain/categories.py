"""Built-in expense categories and payment methods."""

from __future__ import annotations

DEFAULT_CATEGORIES: list[dict[str, str]] = [
    {"id": "food", "name": "Food & Dining"},
    {"id": "groceries", "name": "Groceries"},
    {"id": "transportation", "name": "Transportation"},
    {"id": "education", "name": "Education"},
    {"id": "healthcare", "name": "Healthcare"},
    {"id": "housing", "name": "Housing"},
    {"id": "utilities", "name": "Utilities"},
    {"id": "shopping", "name": "Shopping"},
    {"id": "entertainment", "name": "Entertainment"},
    {"id": "travel", "name": "Travel"},
    {"id": "subscriptions", "name": "Subscriptions"},
    {"id": "other", "name": "Other"},
]

DEFAULT_CATEGORY_IDS = {c["id"] for c in DEFAULT_CATEGORIES}

# Categories generally considered discretionary; used only to phrase
# recommendations, never to make claims about the user's priorities.
DISCRETIONARY_CATEGORIES = {"food", "shopping", "entertainment", "subscriptions", "travel"}

PAYMENT_METHODS: list[dict[str, str]] = [
    {"id": "upi", "name": "UPI"},
    {"id": "debit_card", "name": "Debit card"},
    {"id": "credit_card", "name": "Credit card"},
    {"id": "cash", "name": "Cash"},
    {"id": "net_banking", "name": "Net banking"},
    {"id": "wallet", "name": "Wallet"},
    {"id": "other", "name": "Other"},
]

PAYMENT_METHOD_IDS = {p["id"] for p in PAYMENT_METHODS}

OVERALL_BUDGET_KEY = "__overall__"
