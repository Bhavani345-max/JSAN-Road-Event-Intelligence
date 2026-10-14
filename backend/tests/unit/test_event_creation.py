from datetime import datetime, timezone

import pytest

from packages.event_schema import EventStatus, EventType, ReiEvent
from packages.geo_models import Point
from services.extraction import KeywordClassifier, build_event_from_article
from services.extraction.event_factory import event_id_for
from services.extraction.road_mentions import find_road_mentions
from services.lifecycle import InvalidTransition, check_transition

NOW = datetime(2026, 10, 2, 9, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def classifier() -> KeywordClassifier:
    return KeywordClassifier.from_file()


def build(record, classifier) -> ReiEvent:
    return build_event_from_article(record, classifier.classify(record), now=NOW)


def test_event_carries_only_what_the_article_states(records, classifier):
    record = records[0]
    event = build(record, classifier)

    assert event.title == record.title
    assert event.source_id == "test-news"
    assert event.source_reference == record.url
    assert event.description == record.summary
    assert event.city == "Hyderabad"
    assert event.event_type is EventType.TRAFFIC_DIVERSION
    assert event.affected_road == "Lakeview Junction; Station Road"
    assert event.created_at == event.updated_at == NOW

    # Nothing the article did not provide is filled in.
    assert event.start_time is None
    assert event.end_time is None
    assert event.severity is None
    assert event.direction is None
    assert event.geometry is None
    assert event.confidence is None


def test_new_events_always_require_validation(records, classifier):
    for record in records:
        assert build(record, classifier).status is EventStatus.VALIDATION_REQUIRED


def test_detection_details_are_kept_for_the_reviewer(records, classifier):
    detection = build(records[0], classifier).detection
    assert detection.method == "keyword_rules"
    assert "traffic diversion" in detection.matched_keywords
    assert detection.road_mentions == ["Lakeview Junction", "Station Road"]
    assert detection.score >= 3


def test_article_without_summary_or_road_leaves_those_fields_empty(records, classifier):
    record = next(r for r in records if "waterlogged" in r.title)
    event = build(record, classifier)
    assert event.affected_road is None
    assert event.detection.road_mentions == []


def test_event_id_is_deterministic_per_source_item(records, classifier):
    first = build(records[0], classifier)
    again = build(records[0], classifier)
    other = build(records[1], classifier)
    assert first.event_id == again.event_id == event_id_for("test-news", records[0].external_id)
    assert first.event_id != other.event_id
    assert first.event_id.startswith("EVT-")


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Traffic diversions at Khajaguda junction for 60 days", ["Khajaguda junction"]),
        ("Vehicles diverted via Necklace Road and Raj Bhavan Road", ["Necklace Road", "Raj Bhavan Road"]),
        ("NH-65 traffic diversion between two towns", ["NH-65"]),
        ("Works on NH 44 near the ORR", ["NH-44", "ORR"]),
        ("Congestion near Hyderabad’s RTC X Roads", ["RTC X Roads"]),
        # Descriptions of a road are not names of a road.
        ("The road was damaged. A new flyover is planned.", []),
        ("Pothole-ridden road leaves market deserted", []),
        ("No location is mentioned here", []),
        # In a Title Case headline every word is capitalised, so capitals do not
        # mark a name; only road numbers are still recognisable.
        ("Traffic Diversions At Khajaguda Junction For Sixty Days", []),
        ("Modified Silencers Crushed Under Road Roller In City", []),
        ("Traffic Diverted On NH-65 Near Patancheru For Bridge Works", ["NH-65"]),
    ],
)
def test_road_mentions(text, expected):
    assert find_road_mentions(text) == expected


def test_road_mentions_are_deduplicated_and_limited():
    text = "MG Road, mg road, Station Road, Park Road and Lake Road were affected"
    assert find_road_mentions(text) == ["MG Road", "Station Road", "Park Road"]


def test_review_can_send_an_event_to_qc_or_reject_it(records, classifier):
    event = build(records[0], classifier)
    check_transition(event, EventStatus.QC_PENDING)
    check_transition(event, EventStatus.REJECTED)


@pytest.mark.parametrize("status", [EventStatus.APPROVED, EventStatus.ACTIVE, EventStatus.SCHEDULED])
def test_unreviewed_event_cannot_jump_to_a_published_status(records, classifier, status):
    with pytest.raises(InvalidTransition):
        check_transition(build(records[0], classifier), status)


def test_event_without_location_cannot_be_approved_even_from_qc(records, classifier):
    event = build(records[0], classifier).model_copy(update={"status": EventStatus.QC_PENDING})
    with pytest.raises(InvalidTransition, match="resolved location"):
        check_transition(event, EventStatus.APPROVED)

    located = event.model_copy(
        update={"geometry": Point(type="Point", coordinates=(78.47, 17.4)), "start_time": NOW}
    )
    check_transition(located, EventStatus.APPROVED)
