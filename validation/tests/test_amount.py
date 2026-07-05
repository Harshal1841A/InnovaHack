from decimal import Decimal

from validation import normalizer
from validation import rules


def test_normalize_amount_strips_symbols_and_commas():
    assert normalizer.normalize_amount("$12,500.00") == Decimal("12500.00")
    assert normalizer.normalize_amount("Rs. 1,000") == Decimal("1000")
    assert normalizer.normalize_amount("INR 45.50") == Decimal("45.50")


def test_normalize_amount_invalid_returns_none():
    assert normalizer.normalize_amount("not a number") is None
    assert normalizer.normalize_amount(None) is None
    assert normalizer.normalize_amount("") is None


def test_amount_match_within_tolerance():
    result = rules.validate_amount("USD 12500.00", "USD 12500.005", "USD")
    assert result["amount_match"] is True


def test_amount_mismatch_outside_tolerance():
    result = rules.validate_amount("$9800", "$12500", "USD")
    assert result["amount_match"] is False
    assert result["amount_difference"] == "2700"


def test_amount_inr_uses_wider_tolerance():
    result = rules.validate_amount("INR 1000", "INR 1000.9", "INR")
    assert result["amount_match"] is True


def test_amount_missing_value_returns_none_match():
    result = rules.validate_amount(None, "USD 100", "USD")
    assert result["amount_match"] is None
