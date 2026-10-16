"""Lambda entry point for the 'budgets' route group."""

from app.handlers import build_handler

handler = build_handler("budgets")
