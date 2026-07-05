from validation import rules


def test_purpose_code_plausible_when_matching():
    result = rules.validate_purpose_code(
        "Software development and implementation services for client portal",
        "P0802",
    )
    assert result["purpose_code_plausible"] is True


def test_purpose_code_mismatch_maintenance_vs_consultancy():
    """Verified confusable pair: P0802 (implementation/consultancy) vs
    P0804 (repair and maintenance of computer and software)."""
    result = rules.validate_purpose_code(
        "Ongoing annual maintenance and support for existing software system",
        "P0802",
    )
    assert result["purpose_code_plausible"] is False
    assert result["purpose_code_suggested"] == "P0804"


def test_purpose_code_mismatch_marketing_vs_it_consultancy():
    """Verified confusable pair: P0802 (software/IT) vs P1007 (advertising,
    market research)."""
    result = rules.validate_purpose_code(
        "Digital marketing and advertising campaign management",
        "P0802",
    )
    assert result["purpose_code_plausible"] is False
    assert result["purpose_code_suggested"] == "P1007"


def test_purpose_code_missing_description():
    result = rules.validate_purpose_code(None, "P0802")
    assert result["purpose_code_plausible"] is None


def test_purpose_code_missing_declared_code_suggests_one():
    result = rules.validate_purpose_code("Software consultancy services", None)
    assert result["purpose_code_plausible"] is False
    assert result["purpose_code_suggested"] == "P0802"
