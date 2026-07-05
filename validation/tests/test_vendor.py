from validation import normalizer
from validation import rules


def test_normalize_vendor_strips_legal_suffixes():
    assert normalizer.normalize_vendor("ABC Solutions Pvt Ltd") == "abc solutions"
    assert normalizer.normalize_vendor("ABC Solutions Private Limited") == "abc solutions"
    assert normalizer.normalize_vendor("ABC Solutions") == "abc solutions"


def test_normalize_vendor_punctuation_and_whitespace():
    assert normalizer.normalize_vendor("ABC   Solutions, Inc.") == "abc solutions"


def test_vendor_match_with_legal_suffix_variation():
    result = rules.validate_vendor("ABC Solutions Pvt Ltd", "ABC Solutions Private Limited")
    assert result["vendor_match"] is True
    assert result["vendor_similarity"] >= 85


def test_vendor_match_bare_name_vs_suffixed():
    result = rules.validate_vendor("ABC Solutions", "ABC Solutions Pvt Ltd")
    assert result["vendor_match"] is True


def test_vendor_mismatch_different_company():
    result = rules.validate_vendor("ABC Solutions", "ABC Consulting")
    assert result["vendor_match"] is False


def test_vendor_missing_returns_none():
    result = rules.validate_vendor(None, "ABC Solutions")
    assert result["vendor_match"] is None
