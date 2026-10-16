import datetime as dt
import io

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.errors import ValidationFailed
from app.services.receipts.ocr import tesseract_available
from app.services.receipts.parser import Line, amounts_in, parse_amount, parse_receipt
from app.services.receipts.storage import LocalReceiptStorage
from app.services.receipts.validation import validate_image

TODAY = dt.date(2026, 10, 15)

SAMPLE = """GREEN LEAF CAFE
12 MG Road, Bengaluru
GSTIN: 29ABCDE1234F1Z5
Tax Invoice
Date: 14/10/2026 Time: 13:45
Masala Dosa 2 x 120.00 240.00
Filter Coffee 1 x 60.00 60.00
Paneer Roll 150.00
Sub Total 450.00
CGST 2.5% 11.25
SGST 2.5% 11.25
Grand Total Rs. 472.50
Paid by UPI
Thank you, visit again"""


def lines(text: str, conf: float = 92.0):
    return [Line(t, conf) for t in text.splitlines()]


def test_successful_parse_extracts_all_fields():
    r = parse_receipt(lines(SAMPLE), TODAY)
    assert r["merchant"]["value"] == "GREEN LEAF CAFE"
    assert r["date"]["value"] == "2026-10-14"
    assert r["total"]["value"] == "472.50"
    assert r["total"]["verified_by"] == "subtotal + tax"
    assert r["subtotal"] == "450.00"
    assert r["tax"]["value"] == "22.50"
    assert r["currency"]["value"] == "INR"
    assert [i["description"] for i in r["line_items"]] == ["Masala Dosa", "Filter Coffee", "Paneer Roll"]
    assert r["line_items"][0]["quantity"] == 2
    assert r["suggested_category"]["value"] == "food"
    assert 0 < r["total"]["confidence"] <= 1


def test_missing_fields_are_left_empty_not_invented():
    r = parse_receipt(lines("SOME SHOP\nThank you\nVisit again"), TODAY)
    assert r["total"]["value"] is None
    assert r["date"]["value"] is None
    assert any("Total amount could not be identified" in w for w in r["warnings"])


def test_empty_ocr_output():
    r = parse_receipt([], TODAY)
    assert r["total"]["value"] is None and r["merchant"]["value"] is None
    assert r["warnings"]


@pytest.mark.parametrize("token,expected", [
    ("1,234.50", "1234.50"), ("1.234,50", "1234.50"), ("450/-", "450"), ("1,20,000.00", "120000.00"),
    ("12,50", "12.50"), ("99", "99"),
])
def test_amount_formats(token, expected):
    assert str(parse_amount(token)) == expected


@pytest.mark.parametrize("token", ["1.2.3", "12,3456", "abc", "1.234"])
def test_malformed_amounts_rejected(token):
    assert parse_amount(token) is None


def test_amounts_ignore_dates_phone_numbers_and_percentages():
    assert amounts_in("Date 14/10/2026 Tel 9876543210 GST 18%") == []
    assert [str(a) for a in amounts_in("T0TAL 1O5.00")] == ["105.00"]  # OCR O->0 fix inside numbers


def test_subtotal_and_tax_totals_are_not_mistaken_for_grand_total():
    r = parse_receipt(lines("SHOP\nSubtotal 900.00\nTotal Tax 100.00\nTotal 1000.00"), TODAY)
    assert r["total"]["value"] == "1000.00"


def test_ambiguous_date_warns_and_future_date_ignored():
    r = parse_receipt(lines("SHOP\nDate 05/06/2026\nTotal 10.00"), TODAY)
    assert r["date"]["value"] == "2026-06-05"
    assert any("day/month/year" in w for w in r["warnings"])
    future = parse_receipt(lines("SHOP\nDate 05/12/2027\nTotal 10.00"), TODAY)
    assert future["date"]["value"] is None


# ---------- validation ----------

def _png(width=400, height=300) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(buf, "PNG")
    return buf.getvalue()


def test_invalid_file_types_rejected():
    with pytest.raises(ValidationFailed) as exc:
        validate_image(b"%PDF-1.4 fake pdf", "application/pdf", 10**6)
    assert exc.value.code == "unsupported_file_type"
    with pytest.raises(ValidationFailed):
        validate_image(b"<script>alert(1)</script>", "image/png", 10**6)


def test_spoofed_content_type_rejected():
    with pytest.raises(ValidationFailed) as exc:
        validate_image(_png(), "image/jpeg", 10**6)
    assert exc.value.code == "type_mismatch"


def test_oversized_upload_rejected():
    with pytest.raises(ValidationFailed) as exc:
        validate_image(_png(), "image/png", 100)
    assert exc.value.code == "file_too_large"


def test_unreadable_image_rejected():
    corrupt = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
    with pytest.raises(ValidationFailed) as exc:
        validate_image(corrupt, "image/png", 10**6)
    assert exc.value.code == "unreadable_image"


def test_storage_rejects_path_traversal(tmp_path):
    storage = LocalReceiptStorage(tmp_path / "r")
    for key in ("../../etc/passwd", "user/../../x.jpg", "user/abc.jpg", "/abs/" + "a" * 32 + ".jpg",
                "u\\..\\" + "a" * 32 + ".png"):
        with pytest.raises(ValidationFailed):
            storage.save(key, b"x", "image/png")


# ---------- end to end with real OCR ----------

def _font(size: int):
    for name in ("arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def render_receipt(text: str) -> bytes:
    font = _font(30)
    rows = text.splitlines()
    img = Image.new("RGB", (900, 60 + 48 * len(rows)), "white")
    draw = ImageDraw.Draw(img)
    for i, row in enumerate(rows):
        draw.text((40, 30 + i * 48), row, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


needs_tesseract = pytest.mark.skipif(not tesseract_available(None), reason="Tesseract OCR not installed")


@needs_tesseract
def test_upload_process_review_confirm(client, auth, today):
    text = (f"FRESH MART SUPERMARKET\nDate: {today.strftime('%d/%m/%Y')}\nRice 5kg 450.00\nMilk 2 x 30.00 60.00\n"
            "Sub Total 510.00\nGST 5% 25.50\nGrand Total 535.50\nThank you")
    image = render_receipt(text)
    up = client.post("/api/v1/receipts", headers=auth, files={"file": ("receipt.png", image, "image/png")})
    assert up.status_code == 201, up.text
    rid = up.json()["id"]
    assert "storage_key" not in up.json()

    processed = client.post(f"/api/v1/receipts/{rid}/process", headers=auth)
    assert processed.status_code == 200, processed.text
    ex = processed.json()["extracted"]
    assert ex["total"]["value"] == "535.50"
    assert ex["total_minor"] == 53550
    assert ex["date"]["value"] == today.isoformat()
    assert "FRESH MART" in (ex["merchant"]["value"] or "").upper()
    assert ex["raw_text"]

    img = client.get(f"/api/v1/receipts/{rid}/image", headers=auth)
    assert img.status_code == 200 and img.headers["content-type"] == "image/png"

    confirm = client.post(f"/api/v1/receipts/{rid}/confirm", headers=auth, json={
        "amount_minor": ex["total_minor"], "date": ex["date"]["value"], "category": "groceries",
        "description": "Groceries", "merchant": ex["merchant"]["value"]})
    assert confirm.status_code == 201, confirm.text
    expense = confirm.json()["expense"]
    assert expense["receipt_id"] == rid
    assert client.get(f"/api/v1/receipts/{rid}", headers=auth).json()["status"] == "confirmed"
    again = client.post(f"/api/v1/receipts/{rid}/confirm", headers=auth, json={
        "amount_minor": 1, "date": today.isoformat(), "category": "groceries", "description": "dup"})
    assert again.status_code == 422


@needs_tesseract
def test_blank_image_processes_without_inventing_values(client, auth):
    up = client.post("/api/v1/receipts", headers=auth, files={"file": ("blank.png", _png(), "image/png")})
    ex = client.post(f"/api/v1/receipts/{up.json()['id']}/process", headers=auth).json()["extracted"]
    assert ex["total"]["value"] is None and ex["total_minor"] is None
    assert ex["warnings"]


def test_upload_api_rejects_bad_files(client, auth):
    bad = client.post("/api/v1/receipts", headers=auth, files={"file": ("x.png", b"not an image", "image/png")})
    assert bad.status_code == 422
    big = client.post("/api/v1/receipts", headers=auth,
                      files={"file": ("big.png", b"\x89PNG\r\n\x1a\n" + b"0" * (2 * 1024 * 1024), "image/png")})
    assert big.status_code == 422 and big.json()["error"]["code"] == "file_too_large"
    evil_name = client.post("/api/v1/receipts", headers=auth,
                            files={"file": ("../../../evil.png", _png(), "image/png")})
    assert evil_name.status_code == 201  # filename is ignored; key is server-generated
    assert ".." not in client.get(f"/api/v1/receipts/{evil_name.json()['id']}", headers=auth).text
