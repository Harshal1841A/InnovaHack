from validation import normalizer
from validation import rules


def test_normalize_date_various_formats():
    assert normalizer.normalize_date("2026-03-01") == "2026-03-01"
    assert normalizer.normalize_date("01 March 2026") == "2026-03-01"
    assert normalizer.normalize_date("March 1, 2026") == "2026-03-01"


def test_normalize_date_invalid_returns_none():
    assert normalizer.normalize_date("not a date") is None
    assert normalizer.normalize_date(None) is None


def test_date_within_tolerance():
    result = rules.validate_date("2026-03-01", "2026-03-20")
    assert result["date_match"] is True
    assert result["date_day_difference"] == 19


def test_date_outside_tolerance():
    result = rules.validate_date("2026-01-01", "2026-04-01")
    assert result["date_match"] is False


def test_date_exactly_at_boundary():
    result = rules.validate_date("2026-01-01", "2026-02-15")  # 45 days
    assert result["date_match"] is True


def test_date_missing_returns_none():
    result = rules.validate_date(None, "2026-01-01")
    assert result["date_match"] is None
