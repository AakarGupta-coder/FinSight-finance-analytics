"""Application configuration loaded from environment variables.

All configuration is read from the environment (optionally seeded from a local
``backend/.env`` file during development). Nothing secret is hardcoded here.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

try:  # python-dotenv is a development convenience only
    from dotenv import load_dotenv

    load_dotenv(BACKEND_DIR / ".env", override=False)
except ImportError:  # pragma: no cover - not installed in Lambda
    pass


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw) if raw and raw.strip() else default


@dataclass(frozen=True)
class Settings:
    environment: str = "development"  # development | test | production
    data_backend: str = "sqlite"  # sqlite | dynamodb
    sqlite_path: Path = BACKEND_DIR / "data" / "finance.db"
    dynamodb_table: str = "finance-app"
    aws_region: str = "ap-south-1"
    auth_mode: str = "local"  # local | cognito
    jwt_secret: str = ""
    jwt_ttl_minutes: int = 120
    cognito_user_pool_id: str = ""
    cognito_app_client_id: str = ""
    # Ask Cognito (GetUser) whether an access token was revoked by sign-out; result cached briefly.
    cognito_revocation_check: bool = True
    token_check_cache_seconds: int = 15
    receipt_storage: str = "local"  # local | s3
    receipt_dir: Path = BACKEND_DIR / "data" / "receipts"
    receipt_bucket: str = ""
    max_receipt_bytes: int = 5 * 1024 * 1024
    tesseract_cmd: str = ""
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:5173"])
    allow_demo_data: bool = True
    log_level: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cognito_issuer(self) -> str:
        region = self.cognito_user_pool_id.split("_", 1)[0] if self.cognito_user_pool_id else self.aws_region
        return f"https://cognito-idp.{region}.amazonaws.com/{self.cognito_user_pool_id}"


def _local_jwt_secret(data_dir: Path) -> str:
    """Return a persistent random signing secret for local development.

    The secret is generated once and stored in a git-ignored file so that
    sessions survive backend restarts. Production must set JWT_SECRET (or use
    Cognito, which needs no shared secret).
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    secret_file = data_dir / ".jwt_secret"
    if secret_file.exists():
        value = secret_file.read_text(encoding="utf-8").strip()
        if len(value) >= 32:
            return value
    value = secrets.token_urlsafe(48)
    secret_file.write_text(value, encoding="utf-8")
    return value


def load_settings() -> Settings:
    environment = _env("APP_ENV", "development")
    sqlite_path = Path(_env("SQLITE_PATH") or BACKEND_DIR / "data" / "finance.db")
    receipt_dir = Path(_env("RECEIPT_DIR") or BACKEND_DIR / "data" / "receipts")
    auth_mode = _env("AUTH_MODE", "local")

    jwt_secret = _env("JWT_SECRET")
    if auth_mode == "local" and not jwt_secret:
        if environment == "production":
            raise RuntimeError("JWT_SECRET must be set when AUTH_MODE=local in production")
        jwt_secret = _local_jwt_secret(sqlite_path.parent)

    settings = Settings(
        environment=environment,
        data_backend=_env("DATA_BACKEND", "sqlite"),
        sqlite_path=sqlite_path,
        dynamodb_table=_env("DYNAMODB_TABLE", "finance-app"),
        aws_region=_env("AWS_REGION", _env("AWS_DEFAULT_REGION", "ap-south-1")),
        auth_mode=auth_mode,
        jwt_secret=jwt_secret,
        jwt_ttl_minutes=_env_int("JWT_TTL_MINUTES", 120),
        cognito_user_pool_id=_env("COGNITO_USER_POOL_ID"),
        cognito_app_client_id=_env("COGNITO_APP_CLIENT_ID"),
        cognito_revocation_check=_env_bool("COGNITO_REVOCATION_CHECK", True),
        token_check_cache_seconds=_env_int("TOKEN_CHECK_CACHE_SECONDS", 15),
        receipt_storage=_env("RECEIPT_STORAGE", "local"),
        receipt_dir=receipt_dir,
        receipt_bucket=_env("RECEIPT_BUCKET"),
        max_receipt_bytes=_env_int("MAX_RECEIPT_BYTES", 5 * 1024 * 1024),
        tesseract_cmd=_env("TESSERACT_CMD"),
        cors_origins=_env_list("CORS_ORIGINS", ["http://localhost:5173"]),
        allow_demo_data=_env_bool("ALLOW_DEMO_DATA", environment != "production"),
        log_level=_env("LOG_LEVEL", "INFO"),
    )
    validate_settings(settings)
    return settings


def validate_settings(settings: Settings) -> None:
    if settings.data_backend not in {"sqlite", "dynamodb"}:
        raise RuntimeError("DATA_BACKEND must be 'sqlite' or 'dynamodb'")
    if settings.auth_mode not in {"local", "cognito"}:
        raise RuntimeError("AUTH_MODE must be 'local' or 'cognito'")
    if settings.auth_mode == "cognito" and not (settings.cognito_user_pool_id and settings.cognito_app_client_id):
        raise RuntimeError("COGNITO_USER_POOL_ID and COGNITO_APP_CLIENT_ID are required when AUTH_MODE=cognito")
    if settings.receipt_storage not in {"local", "s3"}:
        raise RuntimeError("RECEIPT_STORAGE must be 'local' or 's3'")
    if settings.receipt_storage == "s3" and not settings.receipt_bucket:
        raise RuntimeError("RECEIPT_BUCKET is required when RECEIPT_STORAGE=s3")
    if settings.is_production and "*" in settings.cors_origins:
        raise RuntimeError("Wildcard CORS origins are not allowed in production")
