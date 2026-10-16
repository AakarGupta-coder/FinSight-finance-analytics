"""Bearer token verification for both authentication modes.

* local   - HS256 JWTs issued by this backend (development / self-hosted).
* cognito - RS256 access tokens issued by an Amazon Cognito user pool,
            verified against the pool's JWKS (signature, issuer, expiry,
            token_use and client_id), then checked for revocation with
            Cognito GetUser so that sign-out (GlobalSignOut / RevokeToken)
            takes effect within a few seconds instead of at token expiry.
"""

from __future__ import annotations

import datetime as dt
import logging
import time
from dataclasses import dataclass

import jwt

from app.config import Settings
from app.errors import Unauthorized

LOCAL_ISSUER = "finance-intelligence-local"
logger = logging.getLogger("app.auth")


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str
    name: str


def issue_local_token(settings: Settings, user_id: str, email: str, name: str) -> tuple[str, int]:
    now = dt.datetime.now(dt.UTC)
    ttl = settings.jwt_ttl_minutes * 60
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "iss": LOCAL_ISSUER,
        "iat": now,
        "exp": now + dt.timedelta(seconds=ttl),
        "token_use": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256"), ttl


def _verify_local(settings: Settings, token: str) -> AuthUser:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=LOCAL_ISSUER,
            options={"require": ["sub", "exp", "iat", "iss"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise Unauthorized("Your session has expired. Please sign in again.", code="token_expired") from exc
    except jwt.PyJWTError as exc:
        raise Unauthorized("Invalid authentication token.") from exc
    return AuthUser(id=claims["sub"], email=claims.get("email", ""), name=claims.get("name", ""))


_jwks_clients: dict[str, jwt.PyJWKClient] = {}


def _jwks_client(issuer: str) -> jwt.PyJWKClient:
    # Cached per warm Lambda container / process.
    if issuer not in _jwks_clients:
        _jwks_clients[issuer] = jwt.PyJWKClient(f"{issuer}/.well-known/jwks.json", cache_keys=True, lifespan=3600)
    return _jwks_clients[issuer]


def _verify_cognito(settings: Settings, token: str) -> AuthUser:
    issuer = settings.cognito_issuer
    try:
        signing_key = _jwks_client(issuer).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            options={"require": ["sub", "exp", "iss", "token_use"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise Unauthorized("Your session has expired. Please sign in again.", code="token_expired") from exc
    except jwt.PyJWTError as exc:
        raise Unauthorized("Invalid authentication token.") from exc
    if claims.get("token_use") != "access" or claims.get("client_id") != settings.cognito_app_client_id:
        raise Unauthorized("Invalid authentication token.")
    if settings.cognito_revocation_check:
        _ensure_not_revoked(settings, token, claims)
    # Access tokens carry no email or name. With email as the sign-in alias the
    # `username` claim is an opaque UUID, so it must not become a display name;
    # the frontend shows the name/email from the ID token instead.
    return AuthUser(id=claims["sub"], email=claims.get("email", ""), name="")


_revocation_checked: dict[str, float] = {}
_cognito_clients: dict[str, object] = {}


def _cognito_client(region: str):
    if region not in _cognito_clients:
        import boto3

        _cognito_clients[region] = boto3.client("cognito-idp", region_name=region)
    return _cognito_clients[region]


def _ensure_not_revoked(settings: Settings, token: str, claims: dict) -> None:
    """Reject access tokens revoked by sign-out.

    API Gateway JWT authorizers (and the JWKS check above) only validate signature and
    expiry, so a token stays usable after GlobalSignOut until it expires. Cognito's
    GetUser, authorised by the token itself (no IAM permission needed), fails with
    NotAuthorizedException for revoked tokens. A positive result is cached per token for
    a few seconds per warm container to keep latency and Cognito calls low. On throttling
    or a Cognito outage the request is allowed (the token is already cryptographically
    valid) and a warning is logged, so a dependency failure does not lock users out.
    """
    key = str(claims.get("jti") or claims.get("origin_jti") or token[-43:])
    now = time.monotonic()
    if now - _revocation_checked.get(key, float("-inf")) < settings.token_check_cache_seconds:
        return
    region = settings.cognito_user_pool_id.split("_", 1)[0] or settings.aws_region
    try:
        _cognito_client(region).get_user(AccessToken=token)
    except Exception as exc:  # noqa: BLE001 - botocore ClientError and transport errors
        code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
        if code == "NotAuthorizedException":
            _revocation_checked.pop(key, None)
            raise Unauthorized("Your session has ended. Please sign in again.", code="token_revoked") from exc
        logger.warning("token revocation check skipped (%s)", code or type(exc).__name__)
        return
    if len(_revocation_checked) > 5000:
        _revocation_checked.clear()
    _revocation_checked[key] = now


def verify_token(settings: Settings, token: str) -> AuthUser:
    if settings.auth_mode == "cognito":
        return _verify_cognito(settings, token)
    return _verify_local(settings, token)
