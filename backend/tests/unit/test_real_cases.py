"""Real Hyderabad cases, from real published articles (tests/fixtures/).

These check that REI turns a real article into an event that says exactly what
the article says and nothing more.
"""

from datetime import datetime, timedelta, timezone

import pytest

from packages.event_schema import EventStatus, EventType
from services.extraction import KeywordClassifier, build_event_from_article
from services.geo_resolution import default_resolver
from tests.support import iiit_junction_article, khajaguda_article, load_located_events

NOW = datetime(2026, 10, 2, 9, 0, tzinfo=timezone.utc)
IST = timezone(timedelta(hours=5, minutes=30))
# Never derived from an article: these need an assessment REI does not make yet.
NOT_ESTABLISHED = ("severity", "direction", "confidence")


@pytest.fixture(scope="module")
def classifier():
    return KeywordClassifier.from_file()


def event_for(record, classifier):
    classification = classifier.classify(record)
    assert classification.is_relevant
    return build_event_from_article(
        record, classification, now=NOW, resolver=default_resolver()
    )


def test_khajaguda_junction_diversions(classifier):
    record = khajaguda_article()
    event = event_for(record, classifier)

    assert event.source_id == "telangana-today"
    assert event.title == "Traffic diversions at Khajaguda junction for 60 days from September 26"
    assert event.source_reference == (
        "https://telanganatoday.com/traffic-diversions-at-khajaguda-junction-for-60-days-from-september-26"
    )
    assert event.event_type is EventType.TRAFFIC_DIVERSION
    assert event.city == "Hyderabad"
    assert event.status is EventStatus.VALIDATION_REQUIRED
    assert event.description == record.summary
    assert "traffic diversion" in event.detection.matched_keywords


def test_khajaguda_event_records_only_the_places_the_article_names(classifier):
    record = khajaguda_article()
    event = event_for(record, classifier)

    # The article says "Khajaguda junction" and "Biodiversity Junction". It does
    # not name a "Khajaguda Road", so none is recorded.
    assert event.affected_road == "Khajaguda junction; Biodiversity Junction"
    assert "khajaguda road" not in event.affected_road.lower()
    for mention in event.detection.road_mentions:
        assert mention.lower() in (record.title + " " + record.summary).lower()


def test_khajaguda_event_takes_its_period_from_the_articles_own_words(classifier):
    """"For 60 days from September 26" is read as 26 September to 24 November, whole days."""
    event = event_for(khajaguda_article(), classifier)
    assert event.detection.stated_period == "for 60 days from September 26"
    assert event.start_time == datetime(2026, 9, 26, 0, 0, tzinfo=IST)
    assert event.end_time == datetime(2026, 11, 24, 23, 59, 59, tzinfo=IST)


def test_khajaguda_event_is_located_by_the_junction_its_headline_names(classifier):
    event = event_for(khajaguda_article(), classifier)
    location = event.detection.location
    assert location.mention == "Khajaguda junction"
    assert (location.place_kind, location.found_in) == ("junction", "title")
    assert location.reference.startswith("OpenStreetMap node/")
    longitude, latitude = event.geometry.coordinates
    # Khajaguda Junction, as mapped on OpenStreetMap.
    assert 78.37 < longitude < 78.39 and 17.41 < latitude < 17.43
    assert event.detection.attributed_to == ["Cyberabad Police"]


def test_iiit_junction_closure(classifier):
    record = iiit_junction_article()
    event = event_for(record, classifier)

    assert event.source_id == "deccan-chronicle"
    assert event.title == "Traffic Curbs Near IIIT Junction from July 1 for Flyover Works"
    assert event.source_reference.endswith("traffic-curbs-near-iiit-junction-from-july-1-for-flyover-works-1967063")
    assert event.city == "Hyderabad"  # from the "Hyderabad:" dateline
    assert event.status is EventStatus.VALIDATION_REQUIRED
    assert "traffic curb" in event.detection.matched_keywords
    # "Curbs … for Flyover Works": the works are the only kind of event named.
    assert event.event_type is EventType.ROAD_CONSTRUCTION
    # The headline is in Title Case and the summary names no road in a form the
    # matcher recognises, so no road is recorded rather than a wrong one.
    assert event.affected_road is None


def test_iiit_junction_closure_period_and_location(classifier):
    event = event_for(iiit_junction_article(), classifier)

    # "…for a period of 90 days starting from July 1, 2026."
    assert event.detection.stated_period == "for a period of 90 days starting from July 1, 2026"
    assert event.start_time == datetime(2026, 7, 1, 0, 0, tzinfo=IST)
    assert event.end_time == datetime(2026, 9, 28, 23, 59, 59, tzinfo=IST)
    # The summary names "Gachibowli Traffic PS", one end of the closed stretch.
    location = event.detection.location
    assert location.mention == "Gachibowli Traffic PS"
    assert location.place_name.lower() == "gachibowli traffic police station"
    assert location.found_in == "summary"
    assert "DLF road" in event.detection.places
    assert event.detection.attributed_to == ["Cyberabad Police"]


@pytest.mark.parametrize("article", [khajaguda_article, iiit_junction_article])
def test_real_events_carry_no_invented_values(article, classifier):
    record = article()
    event = event_for(record, classifier)
    for name in NOT_ESTABLISHED:
        assert getattr(event, name) is None, name
    assert event.status not in {EventStatus.APPROVED, EventStatus.ACTIVE, EventStatus.SCHEDULED}
    # The evidence keeps the publisher's timestamps and link.
    assert record.url.startswith("https://")
    assert record.published_at is not None
    assert record.retrieved_at is not None


def test_test_only_located_events_have_no_confidence_either():
    """Even the test fixtures carry no made-up confidence values."""
    assert all(event.confidence is None for event in load_located_events(NOW))
