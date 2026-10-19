"""A missing start date never stops a genuine road event from being stored and
reviewed; only a stated start puts it on a map (decision 0038).

Four levels: stored (every event, with its evidence, VALIDATION_REQUIRED);
listed for review (located, not known to be over: a stated start, or an end
still ahead, or an official record its source lists, or a recent report);
on the map (located, a stated start, not over); current and upcoming (also an
operational status, which only a reviewer gives).
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.models import Event
from packages.common.time import IST, end_of_day, start_of_day
from packages.event_schema import EventDetection, EventStatus, EventType, ReiEvent
from packages.geo_models import Point
from packages.source_models import RawSourceRecord
from services.extraction.event_factory import build_event_from_article, publication_day_known
from services.extraction.keyword_classifier import ArticleRelevance, ClassificationResult
from services.extraction.stated_period import find_stated_period
from services.lifecycle import approval_blockers
from services.lifecycle.current import EventListView, is_shown, listed_for_review, matches_event_view
from services.lifecycle.transitions import InvalidTransition, check_transition
from tests.support import TEST_SOURCE

NOW = datetime(2026, 10, 19, 6, 0, tzinfo=timezone.utc)  # 11:30 in India
DAY = timedelta(days=1)
POINT = Point(type="Point", coordinates=(78.4867, 17.385))


def event(*, status=EventStatus.VALIDATION_REQUIRED, start=None, end=None, located=True,
          method="keyword_rules", ended=False, event_type=None, created=NOW):  # fmt: skip
    return ReiEvent(
        event_id="EVT-START0000001", source_id="test", title="Road closed", status=status,
        start_time=start, end_time=end, event_type=event_type, geometry=POINT if located else None,
        detection=EventDetection(method=method, matched_keywords=[], source_reports_ended=ended),
        created_at=created, updated_at=created,
    )  # fmt: skip


def levels(e: ReiEvent, *, reported_at=None) -> tuple[bool, bool, bool]:
    """(listed for review, on the map, current or upcoming)"""
    return (
        matches_event_view(e, EventListView.VALIDATION, now=NOW, reported_at=reported_at),
        is_shown(e, now=NOW),
        matches_event_view(e, EventListView.CURRENT_UPCOMING, now=NOW, reported_at=reported_at),
    )


# --- missing dates ----------------------------------------------------------------


@pytest.mark.parametrize(
    "age_days, event_type, listed",
    [
        (0, None, True),
        (7, None, True),
        (8, None, False),  # probably over: stored, no longer listed
        (20, EventType.ROAD_CONSTRUCTION, True),  # road works run longer
        (31, EventType.ROAD_CONSTRUCTION, False),
    ],
)
def test_a_report_with_no_dates_is_listed_for_review_while_recent_and_never_mapped(age_days, event_type, listed):
    undated = event(event_type=event_type)
    assert levels(undated, reported_at=NOW - age_days * DAY) == (listed, False, False)


def test_an_official_record_with_no_dates_is_listed_while_its_source_lists_it():
    official = event(method="source_provided")
    assert levels(official, reported_at=NOW - 90 * DAY) == (True, False, False)
    assert levels(event(method="source_provided", ended=True)) == (False, False, False)


def test_an_unlocated_event_is_stored_but_not_listed():
    assert levels(event(located=False)) == (False, False, False)


# --- explicit start dates ---------------------------------------------------------


@pytest.mark.parametrize("status, expected", [
    (EventStatus.VALIDATION_REQUIRED, (True, True, False)),  # on the review map, not current
    (EventStatus.APPROVED, (False, True, True)),  # only a reviewer makes it operational
])  # fmt: skip
def test_a_stated_start_puts_a_located_event_on_the_map(status, expected):
    assert levels(event(status=status, start=NOW - DAY, end=NOW + DAY)) == expected


def published(hour_utc: int, day: int = 19) -> datetime:
    return datetime(2026, 10, day, hour_utc, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "headline, start_day, end_day",
    [
        ("Traffic restrictions near Charminar begin today", 19, None),
        ("Diversions at Khajaguda from tomorrow", 20, None),
        ("Road closed from today till October 25 for metro works", 19, 25),
        ("One-way rules at KBR Park with effect from today", 19, None),
        ("Till October 30: diversions near Gachibowli starting tomorrow", 20, 30),
    ],
)
def test_today_and_tomorrow_count_from_the_publication_day_as_whole_days(headline, start_day, end_day):
    period = find_stated_period(title=headline, published_at=published(6), zone=IST)
    assert period is not None
    assert period.start == start_of_day(datetime(2026, 10, start_day).date(), IST)  # a day, no time
    assert period.end == (end_of_day(datetime(2026, 10, end_day).date(), IST) if end_day else None)
    assert period.text  # the words, kept for the reviewer


def test_the_publication_day_is_the_citys():
    # 20:00 UTC on 19 October is already 20 October in India, still 19 October in London.
    late = published(20)
    india = find_stated_period(title="Diversions begin today", published_at=late, zone=IST)
    london = find_stated_period(title="Diversions begin today", published_at=late, zone=ZoneInfo("Europe/London"))
    assert india.start.astimezone(IST).date().day == 20
    assert london.start.astimezone(ZoneInfo("Europe/London")).date().day == 19


@pytest.mark.parametrize(
    "headline",
    [
        "Traffic restrictions near Charminar lifted from today",
        "Road reopens from tomorrow after repairs",
        "Curbs eased from today at Tank Bund",
        "Diversions end today",
        "Read more from Telangana Today",
        "From Today's edition: city roads",
    ],
)
def test_no_start_is_read_where_today_does_not_start_the_measure(headline):
    assert find_stated_period(title=headline, published_at=published(6), zone=IST) is None


def test_today_is_not_read_without_the_publishers_own_publication_day():
    assert find_stated_period(
        title="Diversions begin today", published_at=published(6), zone=IST, publication_day_known=False
    ) is None


def record(title: str, raw: dict) -> RawSourceRecord:
    return RawSourceRecord(
        source_id=TEST_SOURCE.source_id, external_id=title, url="https://news.example.com/x", title=title,
        summary=None, content_text=None, categories=[], published_at=published(6), retrieved_at=NOW,
        raw=raw, content_hash="0" * 64,
    )  # fmt: skip


RELEVANT = ClassificationResult(
    label=ArticleRelevance.RELEVANT_TRAFFIC_ARTICLE, score=1.0, matched_keywords=["diversions"],
    event_type=None, city="Hyderabad", classifier_version="test",
)  # fmt: skip


@pytest.mark.parametrize(
    "raw, known",
    [
        ({}, True),  # a feed's own publication time
        ({"search_result": {"date": "3 days ago"}}, False),  # a search engine's
        ({"search_result": {}, "published_at_from": "search_result"}, False),
        ({"search_result": {}, "published_at_from": "article"}, True),  # the article page's own
    ],
)
def test_a_search_results_approximate_time_gives_no_day_to_count_from(raw, known):
    found = record("Diversions near Charminar begin today", raw)
    assert publication_day_known(found) is known
    built = build_event_from_article(found, RELEVANT, now=NOW)
    assert (built.start_time is not None) is known
    assert built.status is EventStatus.VALIDATION_REQUIRED


# --- end date only ----------------------------------------------------------------


def test_an_end_alone_gives_no_start():
    period = find_stated_period(
        title="Mumbai-Pune highway restrictions in place until 20 October", published_at=published(6), zone=IST
    )
    assert period.start is None
    assert period.end == end_of_day(datetime(2026, 10, 20).date(), IST)


def test_an_end_only_event_is_listed_until_its_end_and_never_mapped():
    until = end_of_day(datetime(2026, 10, 20).date(), IST)
    assert levels(event(end=until)) == (True, False, False)
    # After the end: over. Kept, shown in history, its status unchanged.
    over = event(end=NOW - DAY)
    assert levels(over) == (False, False, False)
    assert matches_event_view(over, EventListView.HISTORY, now=NOW)
    assert over.status is EventStatus.VALIDATION_REQUIRED and over.start_time is None


# --- expired events ---------------------------------------------------------------


@pytest.mark.parametrize("status", [EventStatus.VALIDATION_REQUIRED, EventStatus.APPROVED, EventStatus.ACTIVE])
def test_an_expired_event_is_only_in_history_and_keeps_its_status(status):
    expired = event(status=status, start=NOW - 5 * DAY, end=NOW - DAY)
    assert levels(expired) == (False, False, False)
    assert matches_event_view(expired, EventListView.HISTORY, now=NOW)
    assert expired.status is status


def test_an_open_ended_article_event_over_30_days_old_is_off_the_map_and_the_queue():
    lapsed = event(start=NOW - 31 * DAY)
    assert levels(lapsed) == (False, False, False)


# --- pending review: nothing is approved, activated or scheduled by these rules ---


def test_an_undated_event_stays_pending_and_cannot_be_approved_without_a_start():
    undated = event(status=EventStatus.QC_PENDING)
    assert listed_for_review(undated, now=NOW)
    assert "It has no start time." in approval_blockers(undated)
    with pytest.raises(InvalidTransition):
        check_transition(undated, EventStatus.APPROVED)
    assert undated.status is EventStatus.QC_PENDING


def test_reading_today_creates_a_pending_event_not_an_active_or_scheduled_one():
    built = build_event_from_article(record("Diversions near Charminar from tomorrow", {}), RELEVANT, now=NOW)
    assert built.start_time is not None
    assert built.status is EventStatus.VALIDATION_REQUIRED


# --- through the API --------------------------------------------------------------


@pytest.fixture
def stored(session, client):
    now = datetime.now(timezone.utc)
    point = {"type": "Point", "coordinates": [78.4867, 17.385]}
    rows = {
        "EVT-DATES0000001": dict(start_time=None, end_time=None),  # no dates, reported now
        "EVT-DATES0000002": dict(start_time=None, end_time=now + 2 * DAY),  # until a day ahead
        "EVT-DATES0000003": dict(start_time=now - DAY, end_time=now + DAY),  # stated period
        "EVT-DATES0000004": dict(start_time=now - 5 * DAY, end_time=now - DAY),  # expired
        "EVT-DATES0000005": dict(start_time=None, end_time=None, created_at=now - 10 * DAY),  # old report
    }
    for event_id, fields in rows.items():
        session.add(
            Event(
                event_id=event_id, source_id=TEST_SOURCE.source_id, title=f"Road closed {event_id}",
                status="VALIDATION_REQUIRED", geometry=point,
                detection={"method": "keyword_rules", "matched_keywords": []}, version=1,
                created_at=fields.pop("created_at", now), updated_at=now, **fields,
            )
        )  # fmt: skip
    session.commit()
    return client


def listed(client, view: str) -> dict[str, dict]:
    body = client.get("/api/events", params={"view": view, "limit": 500}).json()
    return {item["event_id"]: item for item in body["items"] if item["event_id"].startswith("EVT-DATES")}


def test_the_review_queue_lists_undated_events_and_the_api_says_which_a_map_may_draw(stored):
    review = listed(stored, "validation")
    assert set(review) == {"EVT-DATES0000001", "EVT-DATES0000002", "EVT-DATES0000003"}
    assert {event_id: (e["map_eligible"], e["off_map_reason"]) for event_id, e in review.items()} == {
        "EVT-DATES0000001": (False, "no_start"),
        "EVT-DATES0000002": (False, "no_start"),
        "EVT-DATES0000003": (True, None),
    }
    assert all(e["status"] == "VALIDATION_REQUIRED" for e in review.values())
    # None is current or upcoming: no reviewer has validated one.
    assert listed(stored, "current_upcoming") == {}
    assert set(listed(stored, "history")) == {"EVT-DATES0000004"}


def test_counts_follow_the_review_queue(stored):
    total = stored.get("/api/events", params={"view": "validation", "limit": 500}).json()["total"]
    summary = stored.get("/api/events/summary", params={"view": "validation"}).json()["cities"]
    assert sum(row["total"] for row in summary) == total
    coverage = stored.get("/api/events/coverage").json()["cities"]
    assert sum(row["listed_review"] for row in coverage) == total
    assert sum(row["on_map_review"] for row in coverage) == 1  # only the event with a stated start
    # Every event is still stored.
    assert sum(row["detected"] for row in coverage) == 5
