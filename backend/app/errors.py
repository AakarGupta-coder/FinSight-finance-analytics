"""Application exceptions and consistent JSON error responses."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, details: Any = None, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.details = details
        if code:
            self.code = code


class ValidationFailed(AppError):
    status_code = 422
    code = "validation_error"


class NotFound(AppError):
    status_code = 404
    code = "not_found"


class Conflict(AppError):
    status_code = 409
    code = "conflict"


class Unauthorized(AppError):
    status_code = 401
    code = "unauthorized"


class Forbidden(AppError):
    status_code = 403
    code = "forbidden"


class TooManyRequests(AppError):
    status_code = 429
    code = "too_many_requests"


class ServiceUnavailable(AppError):
    status_code = 503
    code = "service_unavailable"


def _body(code: str, message: str, details: Any = None) -> dict:
    payload: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return payload


def _clean_validation_errors(errors: list[dict]) -> list[dict]:
    cleaned = []
    for err in errors:
        loc = [str(part) for part in err.get("loc", []) if part not in ("body", "query", "path")]
        cleaned.append({"field": ".".join(loc) or None, "message": err.get("msg", "Invalid value")})
    return cleaned


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(_body(exc.code, exc.message, exc.details), status_code=exc.status_code, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError):
        details = _clean_validation_errors(exc.errors())
        first = details[0] if details else {"message": "Invalid request"}
        message = f"{first['field']}: {first['message']}" if first.get("field") else first["message"]
        return JSONResponse(_body("validation_error", message, details), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(_: Request, exc: StarletteHTTPException):
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return JSONResponse(_body(code, str(exc.detail)), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        # Log the exception type and path only; never request bodies.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(_body("internal_error", "An unexpected error occurred."), status_code=500)
