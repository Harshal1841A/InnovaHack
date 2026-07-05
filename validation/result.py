"""Internal result dataclass for the validation pipeline.

Named `result.py` (not `schemas.py`) deliberately: the repo's top-level
`schemas.py` is the single source of truth for API-facing pydantic models
(`ValidationRequest`/`ValidationResponse`). This dataclass is an internal
implementation detail of the pipeline and is converted to
`schemas.ValidationResponse` by `adapter.py` before crossing the API
boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ValidationResult:
    amount_match: Optional[bool]
    amount_difference: Optional[str]
    amount_note: str

    currency_match: Optional[bool]
    currency_note: str

    date_match: Optional[bool]
    date_day_difference: Optional[int]
    date_note: str

    vendor_match: Optional[bool]
    vendor_similarity: Optional[float]
    vendor_note: str

    purpose_code_plausible: Optional[bool]
    purpose_code_note: str
    purpose_code_declared: Optional[str]
    purpose_code_suggested: Optional[str]
    purpose_code_matched_keywords: list = field(default_factory=list)

    missing_fields: list = field(default_factory=list)
    flags: list = field(default_factory=list)
    validation_notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
