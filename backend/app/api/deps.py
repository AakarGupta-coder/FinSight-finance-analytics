"""FastAPI dependencies: settings, repository, storage and the current user."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Request

from app.auth.tokens import AuthUser, verify_token
from app.config import Settings
from app.domain.models import Preferences
from app.errors import Unauthorized
from app.repositories.base import Repository
from app.services.preferences import get_or_create_preferences


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_repo(request: Request) -> Repository:
    return request.app.state.repo


def get_current_user(request: Request, settings: Settings = Depends(get_settings)) -> AuthUser:
    """Identify the caller from a validated bearer token.

    The user id used for every data access comes from here - never from a
    request body, query parameter or path parameter.
    """
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise Unauthorized("Authentication required.")
    return verify_token(settings, token.strip())


@dataclass
class UserContext:
    user: AuthUser
    prefs: Preferences
    repo: Repository
    settings: Settings

    @property
    def user_id(self) -> str:
        return self.user.id


def get_context(
    user: AuthUser = Depends(get_current_user),
    repo: Repository = Depends(get_repo),
    settings: Settings = Depends(get_settings),
) -> UserContext:
    prefs = get_or_create_preferences(repo, user.id, default_name=user.name or None)
    return UserContext(user=user, prefs=prefs, repo=repo, settings=settings)
