"""Exact money handling.

Amounts are stored and calculated as integers in the currency's minor unit
(for INR: paise). Floating point is never used for stored values; percentages
and ratios derived from amounts are computed with Decimal and rounded only for
presentation.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

# ISO 4217 code -> (symbol, minor-unit exponent)
SUPPORTED_CURRENCIES: dict[str, tuple[str, int]] = {
    "INR": ("₹", 2),
    "USD": ("$", 2),
    "EUR": ("€", 2),
    "GBP": ("£", 2),
    "JPY": ("¥", 0),
    "AUD": ("A$", 2),
    "CAD": ("C$", 2),
    "SGD": ("S$", 2),
    "AED": ("AED ", 2),
}

MAX_AMOUNT_MINOR = 10**13  # generous upper bound to catch typos / overflow


def minor_exponent(currency: str) -> int:
    return SUPPORTED_CURRENCIES.get(currency, ("", 2))[1]


def to_minor(value: str | int | Decimal, currency: str = "INR") -> int:
    """Convert a major-unit amount (e.g. "1,234.50") to integer minor units.

    Raises ValueError for malformed values or excess precision.
    """
    if isinstance(value, int):
        value = Decimal(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").replace("_", "").strip()
        try:
            value = Decimal(cleaned)
        except InvalidOperation as exc:
            raise ValueError(f"Invalid amount: {value!r}") from exc
    if not value.is_finite():
        raise ValueError("Amount must be finite")
    exponent = minor_exponent(currency)
    scaled = value * (Decimal(10) ** exponent)
    if scaled != scaled.to_integral_value():
        raise ValueError(f"Amount has more than {exponent} decimal places")
    return int(scaled)


def from_minor(amount_minor: int, currency: str = "INR") -> Decimal:
    exponent = minor_exponent(currency)
    return Decimal(amount_minor) / (Decimal(10) ** exponent)


def format_money(amount_minor: int, currency: str = "INR") -> str:
    """Human readable amount, e.g. ₹1,234.50 (Indian digit grouping for INR)."""
    symbol, exponent = SUPPORTED_CURRENCIES.get(currency, (currency + " ", 2))
    negative = amount_minor < 0
    major = from_minor(abs(amount_minor), currency)
    if exponent:
        text = f"{major:.{exponent}f}"
        whole, frac = text.split(".")
    else:
        whole, frac = f"{major:.0f}", ""
    if currency == "INR" and len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    else:
        whole = f"{int(whole):,}"
    if frac and set(frac) == {"0"}:
        frac = ""
    body = f"{symbol}{whole}" + (f".{frac}" if frac else "")
    return f"-{body}" if negative else body


def percent(part: int | Decimal, whole: int | Decimal, places: int = 1) -> float | None:
    """part / whole * 100, or None when the denominator is zero."""
    if not whole:
        return None
    result = (Decimal(part) / Decimal(whole) * 100).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return float(result)


def pct_change(current: int, previous: int, places: int = 1) -> float | None:
    """Percentage change from previous to current; None when previous is zero."""
    if not previous:
        return None
    result = (Decimal(current - previous) / Decimal(previous) * 100).quantize(
        Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP
    )
    return float(result)


def scale(amount_minor: int, factor: Decimal | float | int) -> int:
    """Multiply an amount by a factor and round half-up to whole minor units."""
    return int((Decimal(amount_minor) * Decimal(str(factor))).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def divide(amount_minor: int, divisor: int | Decimal) -> int:
    """Divide an amount, rounding half-up to whole minor units."""
    if not divisor:
        raise ZeroDivisionError("divisor must be non-zero")
    return int((Decimal(amount_minor) / Decimal(divisor)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def round_major(amount_minor: int, currency: str = "INR") -> int:
    """Round to a whole major unit (e.g. whole rupees) for approximate figures like projections."""
    unit = 10 ** minor_exponent(currency)
    return int((Decimal(amount_minor) / unit).quantize(Decimal(1), rounding=ROUND_HALF_UP)) * unit
