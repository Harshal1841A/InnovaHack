"""Small shared helpers used across validators."""
import re


def clean_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text: str) -> list:
    """Lowercase alnum tokenization for keyword matching."""
    return re.findall(r"[a-z0-9]+", text.lower())
