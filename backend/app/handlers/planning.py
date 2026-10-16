"""Lambda entry point for the 'planning' route group."""

from app.handlers import build_handler

handler = build_handler("planning")
