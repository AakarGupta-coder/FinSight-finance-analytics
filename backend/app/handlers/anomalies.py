"""Lambda entry point for the 'anomalies' route group."""

from app.handlers import build_handler

handler = build_handler("anomalies")
