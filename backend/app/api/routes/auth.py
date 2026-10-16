"""Local email/password authentication (AUTH_MODE=local).

In AWS (AUTH_MODE=cognito) these routes are not mounted: the frontend signs in
directly with Amazon Cognito and the API only validates Cognito tokens.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, Request

from app.api.deps import UserContext, get_context, get_repo, get_settings
from app.api.schemas import ChangePasswordIn, LoginIn, Message, RegisterIn, TokenOut
from app.auth.passwords import hash_password, password_problems, verify_password
from app.auth.tokens import issue_local_token
from app.config import Settings
from app.domain.models import User, new_id
from app.errors import TooManyRequests, Unauthorized, ValidationFailed
from app.repositories.base import Repository
from app.services.preferences import get_or_create_preferences

router = APIRouter(prefix="/auth", tags=["auth"])

# Simple in-process limiter for failed logins (per email+client). Enough for
# local use; in AWS, Cognito provides its own protections.
_FAILED: dict[str, deque] = defaultdict(deque)
_LOCK = threading.Lock()
MAX_FAILURES, WINDOW_SECONDS = 5, 300


def _limiter_key(request: Request, email: str) -> str:
    client = request.client.host if request.client else "unknown"
    return f"{client}:{email.lower()}"


def _check_rate(key: str) -> None:
    now = time.monotonic()
    with _LOCK:
        attempts = _FAILED[key]
        while attempts and now - attempts[0] > WINDOW_SECONDS:
            attempts.popleft()
        if len(attempts) >= MAX_FAILURES:
            raise TooManyRequests("Too many failed sign-in attempts. Try again in a few minutes.")


def _record_failure(key: str) -> None:
    with _LOCK:
        _FAILED[key].append(time.monotonic())


def _token_response(settings: Settings, user: User) -> TokenOut:
    token, ttl = issue_local_token(settings, user.id, user.email, user.name)
    return TokenOut(access_token=token, expires_in=ttl, user={"id": user.id, "email": user.email, "name": user.name})


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, repo: Repository = Depends(get_repo), settings: Settings = Depends(get_settings)):
    problems = password_problems(body.password)
    if problems:
        raise ValidationFailed("Password must contain " + ", ".join(problems) + ".",
                               details=[{"field": "password", "message": "Password must contain " + ", ".join(problems)}])
    user = User(id=new_id(), email=body.email, name=body.name.strip(), password_hash=hash_password(body.password))
    repo.create_user(user)
    get_or_create_preferences(repo, user.id, default_name=user.name)
    return _token_response(settings, user)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, repo: Repository = Depends(get_repo),
          settings: Settings = Depends(get_settings)):
    key = _limiter_key(request, body.email)
    _check_rate(key)
    user = repo.get_user_by_email(body.email)
    # Verify against a dummy hash when the user doesn't exist to keep timing similar.
    valid = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not valid:
        _record_failure(key)
        raise Unauthorized("Incorrect email or password.", code="invalid_credentials")
    with _LOCK:
        _FAILED.pop(key, None)
    return _token_response(settings, user)


@router.post("/change-password", response_model=Message)
def change_password(body: ChangePasswordIn, ctx: UserContext = Depends(get_context)):
    user = ctx.repo.get_user(ctx.user_id)
    if not user or not verify_password(body.current_password, user.password_hash):
        raise ValidationFailed("Current password is incorrect.",
                               details=[{"field": "current_password", "message": "Incorrect password"}])
    problems = password_problems(body.new_password)
    if problems:
        raise ValidationFailed("Password must contain " + ", ".join(problems) + ".",
                               details=[{"field": "new_password", "message": "Password must contain " + ", ".join(problems)}])
    user.password_hash = hash_password(body.new_password)
    ctx.repo.update_user(user)
    return Message(message="Password updated.")


_DUMMY_HASH = hash_password("dummy-password-for-timing-1")
