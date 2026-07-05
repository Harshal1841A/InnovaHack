# Validation Engine — Backend Integration Patch

This is a patch against `Harshal1841A/InnovaHack` (`Backend-integration`
branch), not a full repo copy. It adds a real deterministic validation
engine behind a new endpoint, without touching any existing schema class,
endpoint, or file content those classes already back.

## What's in this patch vs. what to do with it

| File here | Action |
|---|---|
| `validation/` | Copy this whole folder into the repo root as-is: `InnovaHack/validation/` |
| `schemas_append_snippet.py` | **Append** its contents (the `ValidationRequest` / `ValidationResponse` classes) to the **end** of the repo's existing `schemas.py`. Do not create a second `schemas.py`. |
| `main_py_patch_snippet.py` | Add the import line near `main.py`'s other local imports, and add the new endpoint anywhere after the existing `POST /validate` — do not modify or remove that existing (mocked) endpoint. |
| `requirements.txt` | Reference copy with the 3 new lines appended (`python-dateutil`, `rapidfuzz`, `pytest`) to the repo's existing 7. Just append those 3 lines to the real file — don't overwrite it. |

## Why nothing existing was touched

- `schemas.ValidationSchema` (bool fields, `date_consistent`, no
  `vendor_similarity`) is already consumed by `SummarizeRequest` and
  `FollowupDraftRequest`. Changing its shape would break those. The new
  `ValidationResponse` is a separate, richer class for this new endpoint.
- `main.py`'s existing `POST /validate` is explicitly commented as mocking
  Harshit's output. Whether to point it at the real engine or retire it is
  a call for whoever owns that endpoint — this patch adds `POST
  /validate-document` alongside it instead of silently replacing behavior
  something else might depend on.

## Folder structure (after applying)

```
InnovaHack/
├── main.py                  (+2 lines: import + new endpoint)
├── schemas.py                (+2 classes appended: ValidationRequest, ValidationResponse)
├── requirements.txt          (+3 lines appended)
└── validation/
    ├── __init__.py           # exposes validate_document
    ├── validator.py          # pipeline + validate_document() adapter
    ├── rules.py               # one independent validator per pipeline step
    ├── normalizer.py          # amount/currency/date/vendor normalization
    ├── purpose_codes.py        # keyword-based RBI purpose-code matcher
    ├── result.py                # internal ValidationResult dataclass (pipeline-only, not API-facing)
    ├── config.py                 # tolerances/thresholds
    ├── utils.py
    ├── data/
    │   └── purpose_codes.json    # verified RBI codes (source noted in file)
    └── tests/
        ├── mock_data/             # 6 mock extraction files
        ├── test_amount.py
        ├── test_currency.py
        ├── test_dates.py
        ├── test_vendor.py
        ├── test_required_fields.py
        ├── test_purpose_code.py
        └── test_integration.py
```

## Endpoint

```
POST /validate-document
```

**Request** (`schemas.ValidationRequest`):
```json
{
  "case_id": "case_123",
  "extraction": {
    "document_id": "doc_1",
    "document_type": "invoice",
    "fields": {
      "invoice_amount":        {"value": "$9,800.00", "confidence": 0.91, "status": "extracted"},
      "contract_amount":       {"value": "USD 12500",  "confidence": 0.95, "status": "extracted"},
      "invoice_currency":      {"value": "$",           "confidence": 0.91, "status": "extracted"},
      "contract_currency":     {"value": "USD",         "confidence": 0.95, "status": "extracted"},
      "invoice_date":          {"value": "2026-03-01",  "confidence": 0.9,  "status": "extracted"},
      "contract_date":         {"value": "2026-03-05",  "confidence": 0.9,  "status": "extracted"},
      "invoice_vendor":        {"value": "ABC Solutions Pvt Ltd",      "confidence": 0.9, "status": "extracted"},
      "contract_vendor":       {"value": "ABC Solutions Pvt Ltd",      "confidence": 0.9, "status": "extracted"},
      "declared_purpose_code": {"value": "P0802",        "confidence": 0.8, "status": "extracted"},
      "invoice_description":   {"value": "Software consultancy services rendered", "confidence": 0.85, "status": "extracted"}
    }
  }
}
```

**Response** (`schemas.ValidationResponse`):
```json
{
  "case_id": "case_123",
  "amount_match": false,
  "amount_difference": "2700.00",
  "amount_note": "Invoice amount 9800.00 vs contract amount 12500: difference 2700.00 is outside tolerance 0.01.",
  "currency_match": true,
  "currency_note": "Invoice currency USD vs contract currency USD: match.",
  "date_consistent": true,
  "date_day_difference": 4,
  "date_note": "Invoice date 2026-03-01 vs contract date 2026-03-05: 4 day(s) apart, within 45-day tolerance.",
  "vendor_match": true,
  "vendor_similarity": 100.0,
  "vendor_note": "Vendor 'ABC Solutions Pvt Ltd' vs 'ABC Solutions Pvt Ltd' ...: similarity 100.0, threshold 85 -> match.",
  "purpose_code_plausible": true,
  "purpose_code_note": "Declared code P0802 matches keyword evidence (software, consultancy).",
  "purpose_code_declared": "P0802",
  "purpose_code_suggested": "P0802",
  "purpose_code_matched_keywords": ["software", "consultancy"],
  "missing_fields": [],
  "flags": ["AMOUNT_MISMATCH"],
  "validation_notes": ["Invoice amount 9800.00 vs contract amount 12500: difference 2700.00 is outside tolerance 0.01."]
}
```

Verified end-to-end against a real `schemas.ExtractionSchema` instance
(pydantic object, not just a dict) before this patch was written.

## ASSUMPTION carried over from the original brief

`extraction.fields` is expected to contain these exact keys: `invoice_amount`,
`contract_amount`, `invoice_currency`, `contract_currency`, `invoice_date`,
`contract_date`, `invoice_vendor`, `contract_vendor`, `declared_purpose_code`,
`invoice_description`. This wasn't specified by the OCR module's actual
output — once real OCR output is available, confirm these key names match
(or adjust `validator._flatten_extraction_schema` if they don't; the
pipeline logic itself won't need to change).

## Running

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

```bash
curl -X POST http://localhost:8000/validate-document \
  -H "Content-Type: application/json" \
  -d @sample_request.json
```

## Testing

```bash
cd InnovaHack
python3 -m pytest validation/tests/ -v
python3 -m pytest validation/tests/ --cov=validation --cov-report=term-missing
```

39 tests, 97% coverage on the `validation/` package. These tests exercise
the internal `validate()`/`validate_json()` pipeline directly (plain dicts)
and don't require pydantic/FastAPI — `validate_document()` (the pydantic-
facing adapter) is smoke-tested separately since it needs the real
`schemas.py` to import, which lives at the repo root, not in this patch.
