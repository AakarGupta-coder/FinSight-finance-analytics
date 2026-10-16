"""The Lambda entry points serve the same FastAPI app through Mangum."""

import json


def _event(method: str, path: str, headers: dict | None = None, body: dict | None = None) -> dict:
    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": path,
        "rawQueryString": "",
        "headers": {"host": "api.example.com", **(headers or {})},
        "requestContext": {
            "accountId": "123456789012", "apiId": "api", "domainName": "api.example.com", "domainPrefix": "api",
            "http": {"method": method, "path": path, "protocol": "HTTP/1.1", "sourceIp": "203.0.113.1",
                     "userAgent": "pytest"},
            "requestId": "req", "routeKey": "$default", "stage": "$default", "time": "15/Oct/2026:10:00:00 +0000",
            "timeEpoch": 1791021600000,
        },
        "body": json.dumps(body) if body else None,
        "isBase64Encoded": False,
    }


def test_expenses_handler(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "lambda.db"))
    monkeypatch.setenv("RECEIPT_DIR", str(tmp_path / "receipts"))
    monkeypatch.setenv("JWT_SECRET", "lambda-test-secret-lambda-test-secret-123")
    from app.handlers import build_handler

    handler = build_handler("expenses")
    health = handler(_event("GET", "/api/v1/health"), None)
    assert health["statusCode"] == 200 and json.loads(health["body"])["status"] == "ok"

    unauth = handler(_event("GET", "/api/v1/expenses"), None)
    assert unauth["statusCode"] == 401

    # Routes of other groups are not served by this function.
    other = handler(_event("GET", "/api/v1/goals"), None)
    assert other["statusCode"] == 404
