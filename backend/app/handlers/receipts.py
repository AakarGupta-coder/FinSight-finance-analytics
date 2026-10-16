"""Lambda entry point for the 'receipts' route group."""

from app.handlers import build_handler

handler = build_handler("receipts")
