from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile

from app.api.deps import UserContext, get_context
from app.api.routes.expenses import _after_change
from app.api.schemas import PresignIn, ReceiptConfirmIn
from app.domain.models import Receipt
from app.errors import ValidationFailed
from app.services.expenses import ExpenseData
from app.services.receipts import service as svc
from app.services.receipts.ocr import tesseract_available
from app.services.receipts.storage import ReceiptStorage, S3ReceiptStorage

router = APIRouter(prefix="/receipts", tags=["receipts"])
logger = logging.getLogger("app.receipts")


def get_storage(request: Request) -> ReceiptStorage:
    return request.app.state.storage


def _serialize(receipt: Receipt, ctx: UserContext) -> dict:
    data = receipt.model_dump(mode="json", exclude={"user_id", "storage_key"})
    extracted = data.get("extracted")
    if extracted:
        total = extracted.get("total", {}).get("value")
        tax = extracted.get("tax", {}).get("value")
        extracted["total_minor"] = svc.extracted_amount_minor(total, ctx.prefs.currency)
        extracted["tax_minor"] = svc.extracted_amount_minor(tax, ctx.prefs.currency)
        detected = extracted.get("currency", {}).get("value")
        extracted["currency_mismatch"] = bool(detected and detected != ctx.prefs.currency)
    data["image_url"] = f"/api/v1/receipts/{receipt.id}/image"
    return data


@router.get("/status")
def ocr_status(request: Request, ctx: UserContext = Depends(get_context)):
    storage = get_storage(request)
    return {
        "ocr_available": tesseract_available(ctx.settings.tesseract_cmd),
        "upload_mode": "presigned" if storage.supports_presigned_upload else "direct",
        "max_bytes": ctx.settings.max_receipt_bytes,
        "accepted_types": ["image/jpeg", "image/png", "image/webp"],
    }


@router.get("")
def list_receipts(ctx: UserContext = Depends(get_context)):
    receipts = sorted(ctx.repo.list_receipts(ctx.user_id), key=lambda r: r.uploaded_at, reverse=True)
    return {"items": [_serialize(r, ctx) for r in receipts if r.status != "pending_upload"]}


@router.post("", status_code=201)
async def upload(request: Request, file: UploadFile = File(...), ctx: UserContext = Depends(get_context)):
    """Backend-mediated upload (local development and small files)."""
    storage = get_storage(request)
    limit = ctx.settings.max_receipt_bytes
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise ValidationFailed(f"File is too large. Maximum size is {limit // (1024 * 1024)} MB.", code="file_too_large")
    receipt = svc.upload_receipt(ctx.repo, storage, ctx.settings, ctx.user_id, data, file.content_type)
    return _serialize(receipt, ctx)


@router.post("/upload-url", status_code=201)
def presigned_upload(body: PresignIn, request: Request, ctx: UserContext = Depends(get_context)):
    """Short-lived presigned S3 POST so the browser uploads directly to the private bucket."""
    return svc.create_presigned_upload(ctx.repo, get_storage(request), ctx.settings, ctx.user_id,
                                       body.content_type, body.size_bytes)


@router.post("/{receipt_id}/process")
def process(receipt_id: str, request: Request, ctx: UserContext = Depends(get_context)):
    receipt = svc.process_receipt(ctx.repo, get_storage(request), ctx.settings, ctx.prefs, receipt_id)
    return _serialize(receipt, ctx)


@router.get("/{receipt_id}")
def get(receipt_id: str, ctx: UserContext = Depends(get_context)):
    return _serialize(svc.get_receipt(ctx.repo, ctx.user_id, receipt_id), ctx)


@router.get("/{receipt_id}/image")
def image(receipt_id: str, request: Request, ctx: UserContext = Depends(get_context)):
    receipt = svc.get_receipt(ctx.repo, ctx.user_id, receipt_id)
    storage = get_storage(request)
    if isinstance(storage, S3ReceiptStorage):
        return {"url": storage.presigned_get(receipt.storage_key), "expires_in": 120}
    data = storage.load(receipt.storage_key)
    return Response(content=data, media_type=receipt.content_type,
                    headers={"Cache-Control": "private, no-store", "Content-Disposition": "inline"})


@router.post("/{receipt_id}/confirm", status_code=201)
def confirm(receipt_id: str, body: ReceiptConfirmIn, ctx: UserContext = Depends(get_context)):
    fields = body.model_dump(exclude={"receipt_id"})
    expense, receipt = svc.confirm_receipt(ctx.repo, ctx.prefs, receipt_id, ExpenseData(**fields))
    created, alerts = _after_change(ctx, expense)
    return {"expense": expense.model_dump(mode="json", exclude={"user_id"}), "receipt": _serialize(receipt, ctx),
            "new_anomalies": created, "budget_alerts": alerts}


@router.delete("/{receipt_id}", status_code=204)
def delete(receipt_id: str, request: Request, ctx: UserContext = Depends(get_context)):
    svc.delete_receipt(ctx.repo, get_storage(request), ctx.user_id, receipt_id)
    return Response(status_code=204)
