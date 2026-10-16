from decimal import Decimal

import pytest

from app.domain.dates import month_bounds, shift_month
from app.domain.money import divide, format_money, pct_change, percent, scale, to_minor


def test_to_minor_exact():
    assert to_minor("1,234.50") == 123450
    assert to_minor("0.1") == 10
    assert to_minor(Decimal("19.99")) == 1999
    assert to_minor("500", "JPY") == 500


def test_to_minor_rejects_excess_precision_and_garbage():
    with pytest.raises(ValueError):
        to_minor("1.234")
    with pytest.raises(ValueError):
        to_minor("abc")


def test_no_float_drift():
    # 0.1 + 0.2 style errors cannot occur with integer minor units.
    assert to_minor("0.10") + to_minor("0.20") == to_minor("0.30")


def test_format_money_indian_grouping():
    assert format_money(12345678) == "₹1,23,456.78"
    assert format_money(50000) == "₹500"
    assert format_money(-150) == "-₹1.50"
    assert format_money(123456, "USD") == "$1,234.56"


def test_percent_handles_zero_denominator():
    assert percent(50, 0) is None
    assert pct_change(100, 0) is None
    assert percent(1, 3) == 33.3
    assert pct_change(128, 100) == 28.0


def test_scale_and_divide_round_half_up():
    assert scale(1000, Decimal("0.25")) == 250
    assert divide(10, 4) == 3  # 2.5 -> 3
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)


def test_month_helpers():
    assert shift_month("2026-01", -1) == "2025-12"
    assert shift_month("2026-12", 1) == "2027-01"
    start, end = month_bounds("2024-02")
    assert (start.day, end.day) == (1, 29)
