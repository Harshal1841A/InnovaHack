"""Deterministic, keyword-based RBI purpose code matcher.

No ML, no embeddings. Scores each candidate purpose code by counting how
many of its keyword phrases appear in the (tokenized) invoice description,
then picks the highest-scoring code.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

from .utils import tokenize

_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "purpose_codes.json")


@dataclass
class PurposeCodeMatch:
    best_code: Optional[str]
    best_score: int
    matched_keywords: list
    scores: dict  # code -> score, for transparency/debugging


def load_purpose_codes(path: str = _DATA_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["codes"]


def _keyword_hits(description_tokens: list, keyword: str) -> bool:
    """A multi-word keyword matches if all its tokens appear, in order,
    as a contiguous subsequence of the description tokens."""
    kw_tokens = tokenize(keyword)
    if not kw_tokens:
        return False
    n, m = len(description_tokens), len(kw_tokens)
    for i in range(n - m + 1):
        if description_tokens[i:i + m] == kw_tokens:
            return True
    return False


def score_description(description: str, codes: dict) -> PurposeCodeMatch:
    """Score every purpose code against the invoice description."""
    desc_tokens = tokenize(description or "")
    scores = {}
    matched_by_code = {}

    for code, meta in codes.items():
        matched = [kw for kw in meta["keywords"] if _keyword_hits(desc_tokens, kw)]
        scores[code] = len(matched)
        matched_by_code[code] = matched

    if not scores or max(scores.values()) == 0:
        return PurposeCodeMatch(best_code=None, best_score=0, matched_keywords=[], scores=scores)

    best_code = max(scores, key=lambda c: scores[c])
    return PurposeCodeMatch(
        best_code=best_code,
        best_score=scores[best_code],
        matched_keywords=matched_by_code[best_code],
        scores=scores,
    )
