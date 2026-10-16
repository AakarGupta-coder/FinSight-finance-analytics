"""Lambda entry point for the 'expenses' route group."""

from app.handlers import build_handler

handler = build_handler("expenses")
