"""Receipt workflow: upload -> process (OCR + parse) -> review -> confirm as expense."""

from __future__ import annotations

import logging
from decimal import Decimal

from app.config import Settings
from app.domain.dates import today_in, utc_now
from app.domain.models import Preferences, Receipt, new_id
from app.domain.money import to_minor
from app.errors import AppError, NotFound, ValidationFailed
from app.repositories.base import Repository
from app.services.expenses import ExpenseData, create_expense
from app.services.receipts.ocr import run_ocr
from app.services.receipts.parser import Line, parse_receipt
from app.services.receipts.storage import ReceiptStorage, S3ReceiptStorage, build_key
from app.services.receipts.validation import ALLOWED_TYPES, validate_image

logger = logging.getLogger("app.receipts")


def get_receipt(repo: Repository, user_id: str, receipt_id: str) -> Receipt:
    receipt = repo.get_receipt(user_id, receipt_id)
    if not receipt:
        raise NotFound("Receipt not found.")
    return receipt


def upload_receipt(repo: Repository, storage: ReceiptStorage, settings: Settings, user_id: str,
                   data: bytes, declared_type: str | None) -> Receipt:
    content_type, ext = validate_image(data, declared_type, settings.max_receipt_bytes)
    receipt_id = new_id()
    key = build_key(user_id, receipt_id, ext)
    storage.save(key, data, content_type)
    receipt = Receipt(id=receipt_id, user_id=user_id, storage_key=key, content_type=content_type,
                      size_bytes=len(data), status="uploaded")
    repo.put_receipt(receipt)
    return receipt


def create_presigned_upload(repo: Repository, storage: ReceiptStorage, settings: Settings, user_id: str,
                            content_type: str, size_bytes: int) -> dict:
    if not isinstance(storage, S3ReceiptStorage):
        raise ValidationFailed("Direct uploads are only available with S3 storage.")
    if content_type not in ALLOWED_TYPES:
        raise ValidationFailed("Unsupported file. Upload a JPEG, PNG or WebP image.", code="unsupported_file_type")
    if size_bytes <= 0 or size_bytes > settings.max_receipt_bytes:
        raise ValidationFailed("File is too large.", code="file_too_large")
    receipt_id = new_id()
    key = build_key(user_id, receipt_id, ALLOWED_TYPES[content_type])
    receipt = Receipt(id=receipt_id, user_id=user_id, storage_key=key, content_type=content_type,
                      size_bytes=size_bytes, status="pending_upload")
    repo.put_receipt(receipt)
    post = storage.presigned_upload(key, content_type, settings.max_receipt_bytes)
    return {"receipt_id": receipt_id, "upload": post, "expires_in": 300}


def process_receipt(repo: Repository, storage: ReceiptStorage, settings: Settings, prefs: Preferences,
                    receipt_id: str) -> Receipt:
    receipt = get_receipt(repo, prefs.user_id, receipt_id)
    if receipt.status == "confirmed":
        raise ValidationFailed("This receipt has already been saved as an expense.")
    try:
        data = storage.load(receipt.storage_key)
    except NotFound as exc:
        raise ValidationFailed("The receipt upload has not completed.") from exc
    # Re-validate the stored bytes: presigned uploads bypass the API server.
    content_type, _ = validate_image(data, receipt.content_type, settings.max_receipt_bytes)
    try:
        ocr = run_ocr(data, settings.tesseract_cmd)
        parsed = parse_receipt([Line(l.text, l.confidence) for l in ocr.lines], today_in(prefs.timezone))
    except AppError as exc:
        receipt.status = "failed"
        receipt.error = exc.message
        receipt.processed_at = utc_now()
        repo.put_receipt(receipt)
        raise
    if not ocr.lines:
        parsed["warnings"].insert(0, "No text was detected. The image may be blurry, dark or not a receipt.")
    receipt.extracted = {**parsed, "raw_text": ocr.text, "ocr_confidence": ocr.mean_confidence,
                         "line_count": len(ocr.lines), "engine": "tesseract"}
    receipt.status = "processed"
    receipt.error = None
    receipt.size_bytes = len(data)
    receipt.content_type = content_type
    receipt.processed_at = utc_now()
    repo.put_receipt(receipt)
    # Log metadata only - never receipt text or amounts.
    logger.info("receipt processed id=%s lines=%d conf=%.1f", receipt.id, len(ocr.lines), ocr.mean_confidence)
    return receipt


def confirm_receipt(repo: Repository, prefs: Preferences, receipt_id: str, data: ExpenseData):
    receipt = get_receipt(repo, prefs.user_id, receipt_id)
    if receipt.status == "confirmed" and receipt.expense_id and repo.get_expense(prefs.user_id, receipt.expense_id):
        raise ValidationFailed("This receipt has already been saved as an expense.")
    data.receipt_id = receipt.id
    expense = create_expense(repo, prefs, data)
    receipt.status = "confirmed"
    receipt.expense_id = expense.id
    repo.put_receipt(receipt)
    return expense, receipt


def delete_receipt(repo: Repository, storage: ReceiptStorage, user_id: str, receipt_id: str) -> None:
    receipt = get_receipt(repo, user_id, receipt_id)
    storage.delete(receipt.storage_key)
    if receipt.expense_id:
        expense = repo.get_expense(user_id, receipt.expense_id)
        if expense and expense.receipt_id == receipt.id:
            expense.receipt_id = None
            expense.updated_at = utc_now()
            repo.put_expense(expense)
    repo.delete_receipt(user_id, receipt_id)


def extracted_amount_minor(value: str | None, currency: str) -> int | None:
    if value is None:
        return None
    try:
        return to_minor(Decimal(value), currency)
    except ValueError:
        return None
