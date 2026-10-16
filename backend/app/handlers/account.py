"""Lambda entry point for the 'account' route group."""

from app.handlers import build_handler

handler = build_handler("account")
