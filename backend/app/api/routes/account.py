"""Assistant, preferences, categories, demo data and account data management."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request

from app.api.deps import UserContext, get_context
from app.api.schemas import AssistantQueryIn, CategoryIn, DeleteAccountIn, PreferencesIn
from app.auth.passwords import verify_password
from app.domain.categories import PAYMENT_METHODS
from app.domain.money import SUPPORTED_CURRENCIES
from app.errors import Forbidden, ValidationFailed
from app.services import preferences as pref_svc
from app.services.assistant.engine import answer_question
from app.services.demo_data import clear_demo_data, load_demo_data

assistant_router = APIRouter(prefix="/assistant", tags=["assistant"])
account_router = APIRouter(tags=["account"])
logger = logging.getLogger("app.account")


@assistant_router.post("/query")
def query(body: AssistantQueryIn, ctx: UserContext = Depends(get_context)):
    # The question text is not logged: it may contain personal financial details.
    return answer_question(ctx.repo, ctx.prefs, body.question)


def _prefs_out(ctx: UserContext, prefs=None) -> dict:
    prefs = prefs or ctx.prefs
    data = prefs.model_dump(mode="json", exclude={"user_id"})
    data["categories"] = pref_svc.all_categories(prefs)
    return data


@account_router.get("/me")
def me(ctx: UserContext = Depends(get_context)):
    return {
        "user": {"id": ctx.user.id, "email": ctx.user.email, "name": ctx.prefs.display_name or ctx.user.name},
        "preferences": _prefs_out(ctx),
        "auth_mode": ctx.settings.auth_mode,
        "demo_data_enabled": ctx.settings.allow_demo_data,
    }


@account_router.get("/reference")
def reference(ctx: UserContext = Depends(get_context)):
    return {
        "categories": pref_svc.all_categories(ctx.prefs),
        "payment_methods": PAYMENT_METHODS,
        "currencies": [{"code": c, "symbol": s, "exponent": e} for c, (s, e) in SUPPORTED_CURRENCIES.items()],
    }


@account_router.put("/preferences")
def update_preferences(body: PreferencesIn, ctx: UserContext = Depends(get_context)):
    prefs = pref_svc.update_preferences(ctx.repo, ctx.prefs, body.model_dump(exclude_unset=True))
    return _prefs_out(ctx, prefs)


@account_router.post("/categories", status_code=201)
def add_category(body: CategoryIn, ctx: UserContext = Depends(get_context)):
    prefs = pref_svc.add_custom_category(ctx.repo, ctx.prefs, body.name)
    return _prefs_out(ctx, prefs)


@account_router.delete("/categories/{category_id}")
def remove_category(category_id: str, ctx: UserContext = Depends(get_context)):
    moved = pref_svc.remove_custom_category(ctx.repo, ctx.prefs, category_id)
    return {"moved_to_other": moved, "preferences": _prefs_out(ctx)}


def _require_demo(ctx: UserContext) -> None:
    if not ctx.settings.allow_demo_data:
        raise Forbidden("Demo data is disabled in this environment.")


@account_router.post("/demo-data")
def demo_load(ctx: UserContext = Depends(get_context)):
    _require_demo(ctx)
    return {"created": load_demo_data(ctx.repo, ctx.prefs)}


@account_router.delete("/demo-data")
def demo_clear(ctx: UserContext = Depends(get_context)):
    _require_demo(ctx)
    return {"removed": clear_demo_data(ctx.repo, ctx.prefs)}


@account_router.post("/account/delete-data")
def delete_all_data(body: DeleteAccountIn, request: Request, ctx: UserContext = Depends(get_context)):
    """Permanently delete all of the user's financial records (and the local account, in local auth mode)."""
    include_user = ctx.settings.auth_mode == "local"
    if include_user:
        user = ctx.repo.get_user(ctx.user_id)
        if not user or not body.password or not verify_password(body.password, user.password_hash):
            raise ValidationFailed("Password is incorrect.", details=[{"field": "password", "message": "Incorrect password"}])
    storage = request.app.state.storage
    for receipt in ctx.repo.list_receipts(ctx.user_id):
        try:
            storage.delete(receipt.storage_key)
        except Exception:  # noqa: BLE001
            logger.warning("could not delete a receipt file during account deletion")
    ctx.repo.delete_all_user_data(ctx.user_id, include_user=include_user)
    return {"deleted": True, "account_deleted": include_user}
