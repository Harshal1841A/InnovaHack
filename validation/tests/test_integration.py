import json
import os

from validation import validator

MOCK_DIR = os.path.join(os.path.dirname(__file__), "mock_data")


def _load(name):
    with open(os.path.join(MOCK_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


def test_clean_match_has_no_flags():
    result = validator.validate(_load("clean_match.json"))
    assert result.amount_match is True
    assert result.currency_match is True
    assert result.date_match is True
    assert result.vendor_match is True
    assert result.purpose_code_plausible is True
    assert result.flags == []
    assert result.missing_fields == []


def test_amount_mismatch_flagged():
    result = validator.validate(_load("amount_mismatch.json"))
    assert result.amount_match is False
    assert "AMOUNT_MISMATCH" in result.flags


def test_currency_mismatch_flagged():
    result = validator.validate(_load("currency_mismatch.json"))
    assert result.currency_match is False
    assert "CURRENCY_MISMATCH" in result.flags


def test_missing_field_flagged():
    result = validator.validate(_load("missing_field.json"))
    assert "invoice_amount" in result.missing_fields
    assert "MISSING_REQUIRED_FIELDS" in result.flags
    # amount validation should degrade gracefully, not error
    assert result.amount_match is None


def test_vendor_variation_flagged():
    result = validator.validate(_load("vendor_variation.json"))
    assert result.vendor_match is False
    assert "VENDOR_MISMATCH" in result.flags


def test_purpose_code_mismatch_flagged():
    result = validator.validate(_load("purpose_code_mismatch.json"))
    assert result.purpose_code_plausible is False
    assert "PURPOSE_CODE_IMPLAUSIBLE" in result.flags
    assert result.purpose_code_suggested == "P1007"


def test_multiple_simultaneous_failures():
    extraction = {
        "invoice_amount": {"value": "$100", "status": "found"},
        "contract_amount": {"value": "$500", "status": "found"},
        "invoice_currency": {"value": "USD", "status": "found"},
        "contract_currency": {"value": "EUR", "status": "found"},
        "invoice_date": {"value": "2026-01-01", "status": "found"},
        "contract_date": {"value": "2026-06-01", "status": "found"},
        "invoice_vendor": {"value": "ABC Solutions", "status": "found"},
        "contract_vendor": {"value": "XYZ Corp", "status": "found"},
        "declared_purpose_code": {"value": "P0802", "status": "found"},
        "invoice_description": {"value": "Annual maintenance support", "status": "found"},
    }
    result = validator.validate(extraction)
    assert set(result.flags) >= {
        "AMOUNT_MISMATCH", "CURRENCY_MISMATCH", "DATE_OUT_OF_TOLERANCE",
        "VENDOR_MISMATCH", "PURPOSE_CODE_IMPLAUSIBLE",
    }


def test_result_is_json_serializable():
    result = validator.validate_json(_load("clean_match.json"))
    json.dumps(result)  # should not raise
