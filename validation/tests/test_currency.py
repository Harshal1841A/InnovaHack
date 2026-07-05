from validation import normalizer
from validation import rules


def test_normalize_currency_symbols_and_aliases():
    assert normalizer.normalize_currency("₹") == "INR"
    assert normalizer.normalize_currency("Rs") == "INR"
    assert normalizer.normalize_currency("$") == "USD"
    assert normalizer.normalize_currency("US$") == "USD"
    assert normalizer.normalize_currency("€") == "EUR"
    assert normalizer.normalize_currency("£") == "GBP"
    assert normalizer.normalize_currency("usd") == "USD"


def test_normalize_currency_unknown_returns_none():
    assert normalizer.normalize_currency("XYZ") is None
    assert normalizer.normalize_currency(None) is None


def test_currency_match():
    result = rules.validate_currency("$", "USD")
    assert result["currency_match"] is True


def test_currency_mismatch():
    result = rules.validate_currency("USD", "EUR")
    assert result["currency_match"] is False


def test_currency_missing_returns_none():
    result = rules.validate_currency(None, "USD")
    assert result["currency_match"] is None
