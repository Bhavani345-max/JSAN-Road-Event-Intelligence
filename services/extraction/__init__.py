"""Turns raw source records into candidate events (rule-based in this phase)."""

from .event_factory import build_event_from_article, names_a_place
from .keyword_classifier import ArticleRelevance, ClassificationResult, KeywordClassifier
from .source_event import build_event_from_source, classify_source_record

__all__ = [
    "ArticleRelevance",
    "ClassificationResult",
    "KeywordClassifier",
    "build_event_from_article",
    "build_event_from_source",
    "classify_source_record",
    "names_a_place",
]
