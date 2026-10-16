"""Interpret OCR text from a receipt.

Extraction is heuristic and every field carries a confidence score (0-1).
When a field cannot be found reliably it is returned as ``None`` so the user
enters it manually - values are never invented.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.domain.dates import MONTH_NAMES

MONTH_ABBR = {name[:3]: i + 1 for i, name in enumerate(MONTH_NAMES)}
MONTH_ABBR["sept"] = 9

AMOUNT_TOKEN = re.compile(r"(?<![\w.])-?\d[\d,.\s]*\d(?:\s*/-)?|(?<![\w.])\d(?![\w])")

TOTAL_KEYWORDS: list[tuple[re.Pattern, float]] = [
    (re.compile(r"\bgrand\s*total\b"), 0.95),
    (re.compile(r"\b(net\s*(amount|payable|total)|amount\s*(payable|due)|balance\s*due|total\s*amount|total\s*payable|bill\s*amount|total\s*due)\b"), 0.9),
    (re.compile(r"\btotal\b"), 0.8),
    (re.compile(r"\b(amount|amt)\b"), 0.5),
]
NOT_TOTAL = re.compile(
    r"\b(sub\s*-?\s*total|total\s*(tax|gst|vat|qty|quantity|items?|savings?|discount|disc)|"
    r"(tax|gst|vat)\s*total|no\.?\s*of\s*items|items?\s*total|change|tender|cash\s*paid|you\s*saved|round(ed)?\s*off)\b"
)
SUBTOTAL = re.compile(r"\bsub\s*-?\s*total\b")
TAX_LINE = re.compile(r"\b(c\s*gst|s\s*gst|i\s*gst|u\s*gst|gst|vat|tax|cess|service\s*tax)\b")
TAX_EXCLUDE = re.compile(r"\b(gstin|gst\s*no|gst\s*reg|tax\s*invoice|incl(usive)?|vat\s*no|tin)\b")
NON_ITEM = re.compile(
    r"\b(total|sub\s*total|tax|gst|vat|cgst|sgst|igst|cess|change|cash|card|upi|paid|tender|balance|discount|"
    r"round|amount|invoice|bill\s*no|date|time|phone|tel|gstin|thank|visit|table|cashier|qty|rate|price|hsn|"
    r"savings?|mrp)\b"
)
HEADER_SKIP = re.compile(
    r"\b(tax\s*invoice|invoice|receipt|bill|gstin|gst\s*no|phone|ph\.?|tel|mobile|email|www\.|\.com|fssai|"
    r"date|time|order|token|table|cashier|counter|welcome)\b"
)

CURRENCY_PATTERNS = [
    (re.compile(r"₹|\brs\.?(?=\s|\d|$)|\binr\b"), "INR"),
    (re.compile(r"€|\beur\b"), "EUR"),
    (re.compile(r"£|\bgbp\b"), "GBP"),
    (re.compile(r"\busd\b|\$"), "USD"),
]

CATEGORY_HINTS = [
    (re.compile(r"\b(restaurant|cafe|caf[eé]|coffee|kitchen|dhaba|bistro|pizza|burger|food|eatery|bakery|swiggy|zomato|dine|dining)\b"), "food"),
    (re.compile(r"\b(mart|supermarket|grocery|groceries|kirana|fresh|provision|dmart|bigbasket|vegetables?)\b"), "groceries"),
    (re.compile(r"\b(pharmacy|chemist|medical|medicos?|hospital|clinic|apollo|diagnostic|lab)\b"), "healthcare"),
    (re.compile(r"\b(petrol|fuel|diesel|filling\s*station|uber|ola|metro|parking|toll)\b"), "transportation"),
    (re.compile(r"\b(electricity|water\s*bill|broadband|internet|gas\s*agency|recharge)\b"), "utilities"),
    (re.compile(r"\b(cinema|movie|pvr|inox|theatre|bowling|games?)\b"), "entertainment"),
    (re.compile(r"\b(book\s*store|stationery|school|college|tuition|course)\b"), "education"),
    (re.compile(r"\b(hotel|resort|airlines?|airways|railway|irctc|travels?)\b"), "travel"),
    (re.compile(r"\b(fashion|apparel|clothing|electronics|store|retail|shop|footwear|mall)\b"), "shopping"),
]


@dataclass
class Line:
    text: str
    confidence: float = 90.0  # OCR confidence 0-100

    @property
    def lower(self) -> str:
        return self.text.lower()


def _fix_ocr_digits(text: str) -> str:
    # Common OCR confusions inside numbers: O->0, l/I->1, S->5 when between digits.
    text = re.sub(r"(?<=\d)[oO](?=[\d.,])|(?<=[\d.,])[oO](?=\d)", "0", text)
    text = re.sub(r"(?<=\d)[lI](?=[\d.,])|(?<=[\d.,])[lI](?=\d)", "1", text)
    return text


def parse_amount(token: str) -> Decimal | None:
    """Parse a money token such as '1,234.50', '1.234,50', '450/-' or '1,20,000.00'."""
    token = token.strip().replace(" ", "")
    token = re.sub(r"/-$", "", token)
    if not token or not re.fullmatch(r"-?[\d.,]+", token):
        return None
    negative = token.startswith("-")
    token = token.lstrip("-")
    has_comma, has_dot = "," in token, "." in token
    if has_comma and has_dot:
        decimal_sep = "," if token.rfind(",") > token.rfind(".") else "."
        thousands = "." if decimal_sep == "," else ","
        token = token.replace(thousands, "").replace(decimal_sep, ".")
    elif has_comma:
        parts = token.split(",")
        if len(parts) == 2 and len(parts[1]) == 2:
            token = parts[0] + "." + parts[1]  # European decimal comma
        elif all(len(p) in (2, 3) for p in parts[1:]) and parts[-1] and len(parts[-1]) == 3:
            token = token.replace(",", "")  # thousands (incl. Indian 1,20,000)
        else:
            return None
    elif has_dot:
        parts = token.split(".")
        if len(parts) > 2:
            if all(len(p) == 3 for p in parts[1:]):
                token = token.replace(".", "")
            else:
                return None
        elif len(parts[1]) not in (1, 2):
            return None
    try:
        value = Decimal(token)
    except InvalidOperation:
        return None
    return -value if negative else value


def amounts_in(text: str) -> list[Decimal]:
    fixed = _fix_ocr_digits(text)
    # Ignore things that look like dates, times, phone numbers and percentages.
    fixed = re.sub(r"\b\d{1,4}[/-]\d{1,2}[/-]\d{1,4}\b", " ", fixed)
    fixed = re.sub(r"\b\d{1,2}:\d{2}(:\d{2})?\b", " ", fixed)
    fixed = re.sub(r"\d+(\.\d+)?\s*%", " ", fixed)
    results = []
    for match in AMOUNT_TOKEN.finditer(fixed):
        token = match.group(0)
        digits = re.sub(r"\D", "", token)
        if len(digits) > 12:  # card numbers, ids
            continue
        if re.fullmatch(r"\d{7,}", token.strip()):  # phone numbers / bill numbers without separators
            continue
        value = parse_amount(token)
        if value is not None and value >= 0:
            results.append(value)
    return results


def _money_amounts(text: str) -> list[Decimal]:
    """Amounts that look like money: prefer values with a decimal part or currency marker."""
    return amounts_in(text)


def _field(value, confidence: float, source: str | None = None, **extra) -> dict:
    return {"value": value, "confidence": round(max(0.0, min(confidence, 1.0)), 2), "source": source, **extra}


def detect_currency(lines: list[Line]) -> dict:
    text = "\n".join(line.lower for line in lines)
    for pattern, code in CURRENCY_PATTERNS:
        if pattern.search(text):
            return _field(code, 0.9 if code != "USD" else 0.7)
    if re.search(r"\b(gst|cgst|sgst|gstin)\b", text):
        return _field("INR", 0.6, "GST references")
    return _field(None, 0.0)


def find_total(lines: list[Line]) -> tuple[dict, list[dict], int | None]:
    candidates = []
    for idx, line in enumerate(lines):
        lower = line.lower
        if NOT_TOTAL.search(lower):
            continue
        for pattern, weight in TOTAL_KEYWORDS:
            if pattern.search(lower):
                values = _money_amounts(line.text)
                source_idx = idx
                if not values and idx + 1 < len(lines):
                    values = _money_amounts(lines[idx + 1].text)
                    source_idx = idx + 1
                if values:
                    candidates.append({"amount": values[-1], "weight": weight, "line": source_idx,
                                       "text": lines[source_idx].text, "ocr": lines[source_idx].confidence})
                break
    if not candidates:
        return _field(None, 0.0), [], None
    best_weight = max(c["weight"] for c in candidates)
    top = [c for c in candidates if c["weight"] == best_weight]
    chosen = max(top, key=lambda c: (c["amount"], c["line"]))
    confidence = best_weight * (chosen["ocr"] / 100)
    return (_field(str(chosen["amount"]), confidence, chosen["text"]),
            [{"value": str(c["amount"]), "source": c["text"]} for c in candidates], chosen["line"])


def find_subtotal(lines: list[Line]) -> Decimal | None:
    for line in lines:
        if SUBTOTAL.search(line.lower):
            values = _money_amounts(line.text)
            if values:
                return values[-1]
    return None


def find_tax(lines: list[Line]) -> dict:
    components = []
    total_tax = None
    for line in lines:
        lower = line.lower
        if TAX_EXCLUDE.search(lower) or not TAX_LINE.search(lower):
            continue
        values = _money_amounts(line.text)
        if not values:
            continue
        amount = values[-1]
        if re.search(r"\btotal\s*(tax|gst|vat)|(tax|gst|vat)\s*total\b", lower):
            total_tax = (amount, line)
        else:
            components.append((amount, line))
    if total_tax:
        amount, line = total_tax
        return _field(str(amount), 0.85 * line.confidence / 100, line.text, components=[])
    if components:
        amount = sum(a for a, _ in components)
        conf = min(l.confidence for _, l in components) / 100 * 0.75
        return _field(str(amount), conf, "; ".join(l.text for _, l in components),
                      components=[{"label": l.text, "value": str(a)} for a, l in components])
    return _field(None, 0.0, components=[])


DATE_PATTERNS = [
    ("ymd", re.compile(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b")),
    ("dmy", re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4}|\d{2})\b")),
    ("d_mon_y", re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?[\s\-/.,]*([a-z]{3,9})[\s\-/.,']*(\d{4}|\d{2})\b")),
    ("mon_d_y", re.compile(r"\b([a-z]{3,9})[\s\-/.]*(\d{1,2})(?:st|nd|rd|th)?[\s,\-/.]*(\d{4})\b")),
]


def _year(value: str) -> int:
    year = int(value)
    return 2000 + year if year < 100 else year


def _month_from_name(name: str) -> int | None:
    name = name.lower()
    return MONTH_ABBR.get(name[:4]) or MONTH_ABBR.get(name[:3])


def find_date(lines: list[Line], today: dt.date) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    found = []
    for idx, line in enumerate(lines):
        lower = line.lower
        has_label = "date" in lower or "dt" in lower.split()
        for kind, pattern in DATE_PATTERNS:
            for m in pattern.finditer(lower):
                try:
                    ambiguous = False
                    if kind == "ymd":
                        day = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                    elif kind == "dmy":
                        a, b, y = int(m.group(1)), int(m.group(2)), _year(m.group(3))
                        if b > 12 and a <= 12:  # clearly month-first (US style)
                            day = dt.date(y, a, b)
                        else:
                            day = dt.date(y, b, a)  # day-first (default for INR receipts)
                            ambiguous = a <= 12 and b <= 12 and a != b
                    elif kind == "d_mon_y":
                        month = _month_from_name(m.group(2))
                        if not month:
                            continue
                        day = dt.date(_year(m.group(3)), month, int(m.group(1)))
                    else:
                        month = _month_from_name(m.group(1))
                        if not month:
                            continue
                        day = dt.date(_year(m.group(3)), month, int(m.group(2)))
                except ValueError:
                    continue
                if not (dt.date(2000, 1, 1) <= day <= today + dt.timedelta(days=1)):
                    continue
                found.append((day, has_label, ambiguous, idx, line))
    if not found:
        return _field(None, 0.0), warnings
    found.sort(key=lambda f: (not f[1], f[3]))
    day, labelled, ambiguous, _, line = found[0]
    conf = (0.9 if labelled else 0.75) * (line.confidence / 100)
    if ambiguous:
        conf *= 0.7
        warnings.append(f"Date '{day.isoformat()}' was read as day/month/year; check it is correct.")
    return _field(day.isoformat(), conf, line.text), warnings


def find_merchant(lines: list[Line]) -> dict:
    for line in lines[:6]:
        text = re.sub(r"^[^A-Za-z0-9]+|[^A-Za-z0-9).&']+$", "", line.text).strip()
        letters = sum(c.isalpha() for c in text)
        if letters < 3 or letters / max(len(text), 1) < 0.5:
            continue
        if HEADER_SKIP.search(text.lower()) and letters < 15:
            continue
        if amounts_in(text) and letters < 6:
            continue
        return _field(text[:80], 0.7 * line.confidence / 100, line.text)
    return _field(None, 0.0)


def find_line_items(lines: list[Line], total_line: int | None) -> list[dict]:
    items = []
    end = total_line if total_line is not None else len(lines)
    for line in lines[1:end]:
        lower = line.lower
        if NON_ITEM.search(lower):
            continue
        values = _money_amounts(line.text)
        if not values:
            continue
        name_match = re.match(r"^\s*([A-Za-z][A-Za-z0-9&'()./\- ]{1,60}?)\s+(?=[\d₹$€£]|rs)", line.text, re.IGNORECASE)
        if not name_match:
            continue
        name = name_match.group(1).strip(" .-")
        if sum(c.isalpha() for c in name) < 2:
            continue
        qty = None
        qty_match = re.search(r"\b(\d{1,3})\s*[xX@*]\s*\d", line.text)
        if qty_match:
            qty = int(qty_match.group(1))
        elif len(values) >= 3 and values[0] == values[0].to_integral_value() and values[0] <= 100:
            qty = int(values[0])
        items.append({"description": name[:60], "quantity": qty, "amount": str(values[-1]),
                      "confidence": round(0.6 * line.confidence / 100, 2)})
        if len(items) >= 50:
            break
    return items


def suggest_category(merchant: str | None, lines: list[Line]) -> dict:
    text = " ".join([merchant or ""] + [line.lower for line in lines[:8]]).lower()
    for pattern, category in CATEGORY_HINTS:
        if pattern.search(text):
            return _field(category, 0.5, "keyword match")
    return _field(None, 0.0)


def parse_receipt(lines: list[Line], today: dt.date) -> dict:
    lines = [Line(l.text.strip(), l.confidence) for l in lines if l.text and l.text.strip()]
    warnings: list[str] = []
    if not lines:
        return {
            "merchant": _field(None, 0), "date": _field(None, 0), "total": _field(None, 0),
            "subtotal": None, "tax": _field(None, 0, components=[]), "currency": _field(None, 0),
            "line_items": [], "total_candidates": [], "suggested_category": _field(None, 0),
            "warnings": ["No text could be read from the image."],
        }
    total, candidates, total_line = find_total(lines)
    subtotal = find_subtotal(lines)
    tax = find_tax(lines)
    date, date_warnings = find_date(lines, today)
    warnings += date_warnings
    merchant = find_merchant(lines)
    currency = detect_currency(lines)
    items = find_line_items(lines, total_line)

    if total["value"] is None:
        warnings.append("Total amount could not be identified. Please enter it manually.")
    else:
        total_value = Decimal(total["value"])
        if subtotal is not None and tax["value"] is not None:
            if abs(subtotal + Decimal(tax["value"]) - total_value) <= Decimal("1"):
                total["confidence"] = round(min(1.0, total["confidence"] + 0.1), 2)
                total["verified_by"] = "subtotal + tax"
        items_sum = sum(Decimal(i["amount"]) for i in items) if items else None
        if items_sum is not None and items_sum and abs(items_sum - total_value) <= Decimal("1"):
            total["confidence"] = round(min(1.0, total["confidence"] + 0.05), 2)
            total["verified_by"] = total.get("verified_by") or "sum of line items"
    if date["value"] is None:
        warnings.append("Date could not be identified. Please enter it manually.")
    if merchant["value"] is None:
        warnings.append("Merchant name could not be identified.")

    return {
        "merchant": merchant,
        "date": date,
        "total": total,
        "subtotal": str(subtotal) if subtotal is not None else None,
        "tax": tax,
        "currency": currency,
        "line_items": items,
        "total_candidates": candidates,
        "suggested_category": suggest_category(merchant["value"], lines),
        "warnings": warnings,
    }
