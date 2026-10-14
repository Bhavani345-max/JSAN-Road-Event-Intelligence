"""Hyderabad scope detection from the article dateline (Deccan Chronicle fix).

REGRESSION FIXTURE: DLF_ARTICLE reproduces the real Deccan Chronicle article of
29 June 2026 (headline, summary, section tags and opening paragraph as
published). It is no longer in the live feed, so it is preserved here.
"""

from datetime import datetime, timezone

import pytest

from packages.event_schema import EventStatus
from packages.source_models import RawSourceRecord
from services.extraction import ArticleRelevance, KeywordClassifier, build_event_from_article
from services.extraction.keyword_classifier import extract_dateline

NOW = datetime(2026, 10, 2, tzinfo=timezone.utc)
DC_TAGS = ("Southern States,Telangana",)


def article(title, summary="", body=None, categories=DC_TAGS, source="deccan-chronicle"):
    return RawSourceRecord(
        source_id=source,
        external_id=title,
        url="https://example.net/a",
        title=title,
        summary=summary or None,
        content_text=body,
        categories=list(categories),
        published_at=None,
        retrieved_at=NOW,
        raw={},
        content_hash="0" * 64,
    )


@pytest.fixture(scope="module")
def classifier():
    return KeywordClassifier.from_file()


DLF_ARTICLE = article(
    "Traffic Curbs Near IIIT Junction from July 1 for Flyover Works",
    "DLF Gate No.1 to Gachibowli Traffic PS stretch to remain closed for 90 days; "
    "commuters advised to take alternate routes",
    "Hyderabad: The Cyberabad Police have issued a traffic advisory in view of the ongoing "
    "multi-level flyover and underpass construction at IIIT Junction, which is expected to "
    "continue for nearly a year. To expedite the works, authorities have decided to close the "
    "road stretch from DLF Gate No.1 to Gachibowli Traffic Police Station for a period of 90 "
    "days starting from July 1, 2026.",
)


def test_dlf_iiit_junction_article_is_detected_in_scope_and_becomes_an_event(classifier):
    result = classifier.classify(DLF_ARTICLE)
    assert "traffic curb" in result.matched_keywords  # traffic detection: PASS
    assert result.score >= classifier.threshold
    assert result.city == "Hyderabad"  # Hyderabad scope: PASS
    assert result.label is ArticleRelevance.RELEVANT_TRAFFIC_ARTICLE

    event = build_event_from_article(DLF_ARTICLE, result, now=NOW)  # event creation: PASS
    assert event.source_id == "deccan-chronicle"
    assert event.city == "Hyderabad"
    assert event.status is EventStatus.VALIDATION_REQUIRED  # never approved automatically
    assert event.geometry is None and event.start_time is None


def test_the_same_article_without_its_dateline_was_the_old_failure(classifier):
    """Tags, headline and summary never name the city: this is what used to be lost."""
    result = classifier.classify(DLF_ARTICLE.model_copy(update={"content_text": None}))
    assert result.score >= classifier.threshold
    assert result.city is None
    assert result.label is ArticleRelevance.NOT_RELEVANT


def test_hyderabad_dateline_with_a_hyderabad_road_restriction_is_in_scope(classifier):
    result = classifier.classify(
        article(
            "Road Closure Near Orchard Flyover This Weekend",
            "The stretch will remain shut.",
            "HYDERABAD: The traffic police will close the stretch for bridge repairs.",
        )
    )
    assert result.is_relevant and result.city == "Hyderabad"


def test_warangal_article_casually_mentioning_hyderabad_is_not_in_scope(classifier):
    result = classifier.classify(
        article(
            "Traffic Diversions In Warangal For Flyover Works",
            "Vehicles will be diverted for two weeks.",
            "Warangal: Traffic will be diverted near the fort for two weeks. Buses coming from "
            "Hyderabad will take the bypass, the police said.",
        )
    )
    assert result.score >= classifier.threshold
    assert result.city is None and not result.is_relevant


@pytest.mark.parametrize(
    "body",
    [
        # Another district's dateline.
        "Suryapet: Road closure on the highway stretch. Officials in Hyderabad were informed.",
        # No dateline at all.
        "The highway stretch will be closed for repairs. Traffic towards Hyderabad is affected.",
        # A sentence containing a colon is not a dateline.
        "Officials in Hyderabad said: the stretch will be closed for repairs.",
    ],
)
def test_hyderabad_only_later_in_the_body_is_not_enough(classifier, body):
    result = classifier.classify(article("Road Closure On Highway Stretch For Repairs", "", body))
    assert result.score >= classifier.threshold
    assert result.city is None and not result.is_relevant


def test_dateline_alone_does_not_make_an_article_a_traffic_article(classifier):
    result = classifier.classify(
        article(
            "Telangana Records Highest GST Collection",
            "Collections rose 12 per cent.",
            "Hyderabad: The state recorded its highest collection.",
        )
    )
    assert result.city == "Hyderabad" and not result.is_relevant


def test_existing_scope_evidence_still_works_without_a_body(classifier):
    # Telangana Today style: publisher tag. The Hindu style: no body, city in the headline.
    tagged = article(
        "Traffic diversions at Lakeview Junction",
        categories=("Hyderabad", "News"),
        source="telangana-today",
    )
    headline = article(
        "Heavy rain leaves roads waterlogged in Secunderabad",
        categories=("Telangana",),
        source="the-hindu",
    )
    elsewhere = article(
        "Traffic diversions in Warangal for flyover works",
        categories=("Telangana",),
        source="the-hindu",
    )
    assert classifier.classify(tagged).is_relevant
    assert classifier.classify(headline).is_relevant
    assert not classifier.classify(elsewhere).is_relevant


@pytest.mark.parametrize(
    "body, expected",
    [
        ("Hyderabad: The police said", "Hyderabad"),
        ("HYDERABAD: The police said", "HYDERABAD"),
        ("Hyderabad : A spell of rain", "Hyderabad"),
        ("Jayashankar Bhupalpally: A woman", "Jayashankar Bhupalpally"),
        ("Nalgonda, : The court", "Nalgonda"),
        ("By Our Legal Correspondent Hyderabad: The High Court", "By Our Legal Correspondent Hyderabad"),
        ("The highway will be closed: officials", None),
        ("Officials in Hyderabad said: closed", None),
        ("Union home minister Amit Shah will visit", None),
        ("", None),
        (None, None),
    ],
)
def test_extract_dateline(body, expected):
    assert extract_dateline(body) == expected
