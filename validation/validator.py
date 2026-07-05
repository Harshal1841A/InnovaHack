"""Validation Engine entry point.

Composes the independent rule validators into a single deterministic
pipeline: Extraction JSON in, ValidationResult out.
"""
from __future__ import annotations

from . import rules
from . import normalizer
from .result import ValidationResult


def validate(extraction: dict) -> ValidationResult:
    """Run the full validation pipeline against a raw Extraction JSON dict.

    `extraction` is expected to map field names to {"value", "status"}
    objects, as produced by the OCR/Parser module. Missing keys are treated
    as not_found.
    """
    def field(name: str) -> dict:
        return extraction.get(name, {"value": None, "status": "not_found"})

    missing_fields = rules.validate_required_fields(extraction)

    invoice_currency_raw = field("invoice_currency").get("value")
    contract_currency_raw = field("contract_currency").get("value")
    currency_result = rules.validate_currency(invoice_currency_raw, contract_currency_raw)

    # Amount tolerance depends on currency; prefer the normalized invoice
    # currency, falling back to contract currency if invoice is missing.
    resolved_currency = (
        normalizer.normalize_currency(invoice_currency_raw)
        or normalizer.normalize_currency(contract_currency_raw)
    )
    amount_result = rules.validate_amount(
        field("invoice_amount").get("value"),
        field("contract_amount").get("value"),
        resolved_currency,
    )

    date_result = rules.validate_date(
        field("invoice_date").get("value"),
        field("contract_date").get("value"),
    )

    vendor_result = rules.validate_vendor(
        field("invoice_vendor").get("value"),
        field("contract_vendor").get("value"),
    )

    purpose_result = rules.validate_purpose_code(
        field("invoice_description").get("value"),
        field("declared_purpose_code").get("value"),
    )

    flags = []
    notes = []

    if amount_result["amount_match"] is False:
        flags.append("AMOUNT_MISMATCH")
        notes.append(amount_result["amount_note"])
    if currency_result["currency_match"] is False:
        flags.append("CURRENCY_MISMATCH")
        notes.append(currency_result["currency_note"])
    if date_result["date_match"] is False:
        flags.append("DATE_OUT_OF_TOLERANCE")
        notes.append(date_result["date_note"])
    if vendor_result["vendor_match"] is False:
        flags.append("VENDOR_MISMATCH")
        notes.append(vendor_result["vendor_note"])
    if purpose_result["purpose_code_plausible"] is False:
        flags.append("PURPOSE_CODE_IMPLAUSIBLE")
        notes.append(purpose_result["purpose_code_note"])
    if missing_fields:
        flags.append("MISSING_REQUIRED_FIELDS")
        notes.append(f"Missing required fields: {', '.join(missing_fields)}.")

    return ValidationResult(
        amount_match=amount_result["amount_match"],
        amount_difference=amount_result["amount_difference"],
        amount_note=amount_result["amount_note"],
        currency_match=currency_result["currency_match"],
        currency_note=currency_result["currency_note"],
        date_match=date_result["date_match"],
        date_day_difference=date_result["date_day_difference"],
        date_note=date_result["date_note"],
        vendor_match=vendor_result["vendor_match"],
        vendor_similarity=vendor_result["vendor_similarity"],
        vendor_note=vendor_result["vendor_note"],
        purpose_code_plausible=purpose_result["purpose_code_plausible"],
        purpose_code_note=purpose_result["purpose_code_note"],
        purpose_code_declared=purpose_result["purpose_code_declared"],
        purpose_code_suggested=purpose_result["purpose_code_suggested"],
        purpose_code_matched_keywords=purpose_result["purpose_code_matched_keywords"],
        missing_fields=missing_fields,
        flags=flags,
        validation_notes=notes,
    )


def validate_json(extraction: dict) -> dict:
    """Convenience wrapper returning a plain JSON-serializable dict."""
    return validate(extraction).to_dict()


def _flatten_extraction_schema(extraction) -> dict:
    """Convert the repo's `schemas.ExtractionSchema` (fields: Dict[str, FieldData])
    into the flat {"field_name": {"value", "status"}} dict this pipeline expects.

    ASSUMPTION: `extraction.fields` is expected to contain the keys
    invoice_amount, contract_amount, invoice_currency, contract_currency,
    invoice_date, contract_date, invoice_vendor, contract_vendor,
    declared_purpose_code, invoice_description. Any of these missing from
    `fields` is treated as not_found (consistent with FieldData.status).
    """
    flat = {}
    for name, field_data in extraction.fields.items():
        flat[name] = {"value": field_data.value, "status": field_data.status}
    return flat


def validate_document(extraction, case_id: str):
    """Public entry point for the `/validate-document` endpoint.

    Accepts the repo's `schemas.ExtractionSchema` (or an equivalent flat
    dict, for convenience/testing) and returns a `schemas.ValidationResponse`.
    Imports `schemas` lazily (not at module level) so this package has no
    hard dependency on pydantic/the repo's schema module for its own unit
    tests, which exercise `validate()`/`validate_json()` directly.
    """
    import schemas  # repo-root schemas.py

    extraction_dict = (
        _flatten_extraction_schema(extraction)
        if hasattr(extraction, "fields")
        else extraction
    )
    result = validate(extraction_dict)

    return schemas.ValidationResponse(
        case_id=case_id,
        amount_match=result.amount_match,
        amount_difference=result.amount_difference,
        amount_note=result.amount_note,
        currency_match=result.currency_match,
        currency_note=result.currency_note,
        date_consistent=result.date_match,
        date_day_difference=result.date_day_difference,
        date_note=result.date_note,
        vendor_match=result.vendor_match,
        vendor_similarity=result.vendor_similarity,
        vendor_note=result.vendor_note,
        purpose_code_plausible=result.purpose_code_plausible,
        purpose_code_note=result.purpose_code_note,
        purpose_code_declared=result.purpose_code_declared,
        purpose_code_suggested=result.purpose_code_suggested,
        purpose_code_matched_keywords=result.purpose_code_matched_keywords,
        missing_fields=result.missing_fields,
        flags=result.flags,
        validation_notes=result.validation_notes,
    )
