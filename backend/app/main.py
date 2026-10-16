"""FastAPI application factory.

``create_app`` builds the full API for local development, or a subset of
route groups for an individual AWS Lambda function (see app/handlers).
"""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, load_settings
from app.errors import register_error_handlers
from app.logging_config import configure_logging
from app.repositories.base import Repository
from app.repositories.factory import build_repository
from app.services.receipts.storage import ReceiptStorage, build_storage

API_PREFIX = "/api/v1"
ALL_GROUPS = ("auth", "expenses", "budgets", "analytics", "anomalies", "receipts", "planning", "assistant", "account")

logger = logging.getLogger("app.http")


def _group_routers(group: str) -> list[APIRouter]:
    if group == "auth":
        from app.api.routes.auth import router

        return [router]
    if group == "expenses":
        from app.api.routes.expenses import router

        return [router]
    if group == "budgets":
        from app.api.routes.budgets import router

        return [router]
    if group == "analytics":
        from app.api.routes.analytics import router

        return [router]
    if group == "anomalies":
        from app.api.routes.anomalies import router

        return [router]
    if group == "receipts":
        from app.api.routes.receipts import router

        return [router]
    if group == "planning":
        from app.api.routes.planning import goals_router, simulations_router

        return [goals_router, simulations_router]
    if group == "assistant":
        from app.api.routes.account import assistant_router

        return [assistant_router]
    if group == "account":
        from app.api.routes.account import account_router

        return [account_router]
    raise ValueError(f"Unknown route group {group}")


def create_app(settings: Settings | None = None, groups: tuple[str, ...] | list[str] | None = None,
               repo: Repository | None = None, storage: ReceiptStorage | None = None) -> FastAPI:
    settings = settings or load_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title="Finance Intelligence API",
        version="1.0.0",
        description="Personal finance tracking, analytics and intelligence API.",
        docs_url=None if settings.is_production else "/api/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/api/openapi.json",
    )
    app.state.settings = settings
    app.state.repo = repo or build_repository(settings)
    app.state.storage = storage or build_storage(settings)

    register_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=600,
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        started = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers.setdefault("Cache-Control", "no-store")
        # Method, path, status and timing only - no bodies, tokens or query strings.
        logger.info("%s %s %s %.0fms rid=%s", request.method, request.url.path, response.status_code, elapsed, request_id)
        return response

    api = APIRouter(prefix=API_PREFIX)

    @api.get("/health", tags=["meta"])
    def health():
        try:
            db_ok = app.state.repo.health_check()
        except Exception:  # noqa: BLE001
            db_ok = False
        return {"status": "ok" if db_ok else "degraded", "database": "ok" if db_ok else "unavailable",
                "environment": settings.environment, "data_backend": settings.data_backend}

    @api.get("/config", tags=["meta"])
    def public_config():
        """Non-secret settings the frontend needs before sign-in."""
        return {
            "auth_mode": settings.auth_mode,
            "cognito": {"user_pool_id": settings.cognito_user_pool_id, "client_id": settings.cognito_app_client_id,
                        "region": settings.cognito_user_pool_id.split("_")[0] if settings.cognito_user_pool_id else None}
            if settings.auth_mode == "cognito" else None,
            "demo_data_enabled": settings.allow_demo_data,
            "receipt_upload_mode": "presigned" if app.state.storage.supports_presigned_upload else "direct",
        }

    selected = groups or ALL_GROUPS
    for group in selected:
        if group == "auth" and settings.auth_mode != "local":
            continue
        for router in _group_routers(group):
            api.include_router(router)
    app.include_router(api)
    return app
