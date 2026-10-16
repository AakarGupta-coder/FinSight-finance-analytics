"""Lambda entry point for the 'analytics' route group."""

from app.handlers import build_handler

handler = build_handler("analytics")
