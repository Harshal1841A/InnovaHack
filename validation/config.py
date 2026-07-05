"""Central configuration for validation tolerances and thresholds."""
from decimal import Decimal

# Amount tolerance by currency (absolute, in that currency's units)
AMOUNT_TOLERANCE = {
    "INR": Decimal("1"),
    "USD": Decimal("0.01"),
    "EUR": Decimal("0.01"),
    "GBP": Decimal("0.01"),
}
DEFAULT_AMOUNT_TOLERANCE = Decimal("0.01")

# Date tolerance in days between invoice date and contract date
DATE_TOLERANCE_DAYS = 45

# Vendor name fuzzy-match threshold (rapidfuzz token_sort_ratio, 0-100)
VENDOR_MATCH_THRESHOLD = 85

# Purpose code plausibility: minimum keyword-score gap for the declared code
# to be accepted even when it isn't the top-scoring code (avoids false flags
# on near-ties).
PURPOSE_CODE_MIN_SCORE = 1

# Legal suffixes stripped during vendor name normalization
LEGAL_SUFFIXES = [
    "private limited", "pvt ltd", "pvt", "private", "limited", "ltd",
    "llp", "llc", "inc", "incorporated", "corporation", "corp",
    "company", "co",
]

# Currency symbol/alias -> ISO 4217 code
CURRENCY_ALIASES = {
    "₹": "INR", "rs": "INR", "rs.": "INR", "inr": "INR",
    "$": "USD", "us$": "USD", "usd": "USD",
    "€": "EUR", "eur": "EUR",
    "£": "GBP", "gbp": "GBP",
}
