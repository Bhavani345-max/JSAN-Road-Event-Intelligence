"""Cross-source event matching (see matcher.py)."""

from .matcher import EventFacts, Match, MatchClass, compare, headline_similarity

__all__ = ["EventFacts", "Match", "MatchClass", "compare", "headline_similarity"]
