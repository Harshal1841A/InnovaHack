"""Independent, reusable validation rules.

Each function takes normalized inputs and returns a plain result tuple/dict
of the fields relevant to that rule. Validator.py composes these into the
final ValidationResult.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from dateutil import parser as date_parser
from rapidfuzz import fuzz

from . import normalizer
from .config import (
    AMOUNT_TOLERANCE,
    DEFAULT_AMOUNT_TOLERANCE,
    DATE_TOLERANCE_DAYS,
    VENDOR_MATCH_THRESHOLD,
)
from .purpose_codes import load_purpose_codes, score_description


def validate_amount(invoice_amount: Optional[str], contract_amount: Optional[str],
                     currency: Optional[str]) -> dict:
    inv = normalizer.normalize_amount(invoice_amount)
    con = normalizer.normalize_amount(contract_amount)

    if inv is None or con is None:
        return {
            "amount_match": None,
            "amount_difference": None,
            "amount_note": "Amount validation skipped: invoice or contract amount missing/unparseable.",
        }

    tolerance = AMOUNT_TOLERANCE.get(currency, DEFAULT_AMOUNT_TOLERANCE)
    diff = abs(inv - con)
    match = diff <= tolerance
    note = (
        f"Invoice amount {inv} vs contract amount {con}: difference {diff} "
        f"is {'within' if match else 'outside'} tolerance {tolerance}."
    )
    return {"amount_match": match, "amount_difference": str(diff), "amount_note": note}


def validate_currency(invoice_currency: Optional[str], contract_currency: Optional[str]) -> dict:
    inv = normalizer.normalize_currency(invoice_currency)
    con = normalizer.normalize_currency(contract_currency)

    if inv is None or con is None:
        return {
            "currency_match": None,
            "currency_note": "Currency validation skipped: invoice or contract currency missing/unrecognized.",
        }

    match = inv == con
    note = f"Invoice currency {inv} vs contract currency {con}: {'match' if match else 'mismatch'}."
    return {"currency_match": match, "currency_note": note}


def validate_date(invoice_date: Optional[str], contract_date: Optional[str]) -> dict:
    inv_iso = normalizer.normalize_date(invoice_date)
    con_iso = normalizer.normalize_date(contract_date)

    if inv_iso is None or con_iso is None:
        return {
            "date_match": None,
            "date_day_difference": None,
            "date_note": "Date validation skipped: invoice or contract date missing/unparseable.",
        }

    inv_dt = date_parser.parse(inv_iso)
    con_dt = date_parser.parse(con_iso)
    day_diff = abs((inv_dt - con_dt).days)
    match = day_diff <= DATE_TOLERANCE_DAYS
    note = (
        f"Invoice date {inv_iso} vs contract date {con_iso}: {day_diff} day(s) apart, "
        f"{'within' if match else 'outside'} {DATE_TOLERANCE_DAYS}-day tolerance."
    )
    return {"date_match": match, "date_day_difference": day_diff, "date_note": note}


def validate_vendor(invoice_vendor: Optional[str], contract_vendor: Optional[str]) -> dict:
    inv = normalizer.normalize_vendor(invoice_vendor)
    con = normalizer.normalize_vendor(contract_vendor)

    if inv is None or con is None:
        return {
            "vendor_match": None,
            "vendor_similarity": None,
            "vendor_note": "Vendor validation skipped: invoice or contract vendor name missing.",
        }

    similarity = fuzz.token_sort_ratio(inv, con)
    match = similarity >= VENDOR_MATCH_THRESHOLD
    note = (
        f"Vendor '{invoice_vendor}' vs '{contract_vendor}' (normalized: '{inv}' / '{con}'): "
        f"similarity {similarity:.1f}, threshold {VENDOR_MATCH_THRESHOLD} -> "
        f"{'match' if match else 'no match'}."
    )
    return {"vendor_match": match, "vendor_similarity": similarity, "vendor_note": note}


def validate_required_fields(extraction: dict) -> list:
    """extraction: mapping of field_name -> {"value": ..., "status": ...}.
    Returns list of field names with status == 'not_found'."""
    missing = []
    for field_name, field_data in extraction.items():
        if isinstance(field_data, dict) and field_data.get("status") == "not_found":
            missing.append(field_name)
    return missing


def validate_purpose_code(description: Optional[str], declared_code: Optional[str]) -> dict:
    codes = load_purpose_codes()

    if not description:
        return {
            "purpose_code_plausible": None,
            "purpose_code_note": "Purpose code validation skipped: invoice description missing.",
            "purpose_code_declared": declared_code,
            "purpose_code_suggested": None,
            "purpose_code_matched_keywords": [],
        }

    match = score_description(description, codes)

    if match.best_code is None:
        return {
            "purpose_code_plausible": None,
            "purpose_code_note": "No known purpose-code keywords matched the invoice description.",
            "purpose_code_declared": declared_code,
            "purpose_code_suggested": None,
            "purpose_code_matched_keywords": [],
        }

    if declared_code is None:
        return {
            "purpose_code_plausible": False,
            "purpose_code_note": f"Declared purpose code missing; keywords suggest {match.best_code} ({codes[match.best_code]['description']}).",
            "purpose_code_declared": None,
            "purpose_code_suggested": match.best_code,
            "purpose_code_matched_keywords": match.matched_keywords,
        }

    declared_upper = declared_code.strip().upper()
    plausible = declared_upper == match.best_code

    if plausible:
        note = f"Declared code {declared_upper} matches keyword evidence ({', '.join(match.matched_keywords)})."
    else:
        note = (
            f"Declared code {declared_upper} ({codes.get(declared_upper, {}).get('description', 'unknown code')}) "
            f"does not match the best-fit code {match.best_code} "
            f"({codes[match.best_code]['description']}), suggested by keywords: "
            f"{', '.join(match.matched_keywords)}."
        )

    return {
        "purpose_code_plausible": plausible,
        "purpose_code_note": note,
        "purpose_code_declared": declared_upper,
        "purpose_code_suggested": match.best_code,
        "purpose_code_matched_keywords": match.matched_keywords,
    }
