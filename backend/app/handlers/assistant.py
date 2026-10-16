"""Lambda entry point for the 'assistant' route group."""

from app.handlers import build_handler

handler = build_handler("assistant")
