from validation import rules


def test_no_missing_fields():
    extraction = {
        "invoice_amount": {"value": "100", "status": "found"},
        "invoice_date": {"value": "2026-01-01", "status": "found"},
    }
    assert rules.validate_required_fields(extraction) == []


def test_detects_missing_fields():
    extraction = {
        "invoice_amount": {"value": None, "status": "not_found"},
        "invoice_date": {"value": "2026-01-01", "status": "found"},
        "invoice_vendor": {"value": None, "status": "not_found"},
    }
    missing = rules.validate_required_fields(extraction)
    assert set(missing) == {"invoice_amount", "invoice_vendor"}


def test_low_confidence_is_not_missing():
    extraction = {
        "invoice_amount": {"value": "100", "status": "low_confidence"},
    }
    assert rules.validate_required_fields(extraction) == []
