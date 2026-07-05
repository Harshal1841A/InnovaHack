"""Normalization functions: amount, currency, date, vendor name.

Each function is pure and independent so validators can be tested and
reused in isolation.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from dateutil import parser as date_parser

from .config import CURRENCY_ALIASES, LEGAL_SUFFIXES
from .utils import clean_whitespace


def normalize_amount(raw: Optional[str]) -> Optional[Decimal]:
    """Strip currency symbols/commas and convert to Decimal.

    Returns None if the value is missing or not a parseable number.
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    # Strip currency symbols/words and thousands separators.
    text = re.sub(r"[₹$€£]", "", text)
    text = re.sub(r"(?i)(\brs\.?\b|\b(?:inr|usd|us\$|eur|gbp)\b)", "", text)
    text = text.replace(",", "").replace(" ", "").strip()
    text = re.sub(r"^[.\s]+", "", text)
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def normalize_currency(raw: Optional[str]) -> Optional[str]:
    """Map a raw currency symbol/word to its ISO 4217 code."""
    if raw is None:
        return None
    text = str(raw).strip().lower()
    if not text:
        return None
    if text in CURRENCY_ALIASES:
        return CURRENCY_ALIASES[text]
    upper = text.upper()
    if upper in {"INR", "USD", "EUR", "GBP"}:
        return upper
    return None


def normalize_date(raw: Optional[str]) -> Optional[str]:
    """Parse an OCR date string into ISO-8601 (YYYY-MM-DD).

    Returns None if the value is missing or unparseable.
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        parsed = date_parser.parse(text, dayfirst=False, fuzzy=True)
    except (ValueError, OverflowError):
        return None
    return parsed.date().isoformat()


def normalize_vendor(raw: Optional[str]) -> Optional[str]:
    """Lowercase, strip punctuation/whitespace, remove legal suffixes."""
    if raw is None:
        return None
    text = str(raw).lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = clean_whitespace(text)
    if not text:
        return None

    # Remove legal suffixes as trailing words (longest first so "pvt ltd"
    # is removed before "pvt" or "ltd" alone would leave a stray word).
    for suffix in sorted(LEGAL_SUFFIXES, key=len, reverse=True):
        pattern = r"\s*\b" + re.escape(suffix) + r"\b\s*$"
        new_text = re.sub(pattern, "", text)
        text = clean_whitespace(new_text)

    return text if text else None
