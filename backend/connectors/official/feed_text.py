"""Putting a feed's own text fields together (21 October 2026)."""

from .feature_feed import clean


def sentences(*parts: str) -> str:
    """The non-empty parts as sentences: each ends with a stop, none gets two."""
    kept = [text for part in parts if (text := clean(part))]
    return " ".join(text if text[-1] in ".!?" else f"{text}." for text in kept)


def stretch(street: str, start_at: str = "", end_at: str = "") -> str:
    """'Main St from 1st Ave to 2nd Ave', with only the parts the source names."""
    parts = (street, f"from {start_at}" if start_at else "", f"to {end_at}" if end_at else "")
    return " ".join(part for part in parts if part)
