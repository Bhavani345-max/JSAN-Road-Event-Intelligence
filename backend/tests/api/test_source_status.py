"""Every source's state, and every city's events from detection to the map (decision 0034)."""

from collections import Counter
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import Event, Source
from app.repositories.sources import SourceRepository
from app.services.source_status import source_state
from connectors.registry import REGISTERED_SOURCES, get_registered_source
from tests.support import TEST_SOURCE

NOW = datetime.now(timezone.utc)


def _row(source_id: str, **polling) -> Source:
    definition = get_registered_source(source_id).definition
    return Source(**definition.model_dump(mode="json"), **polling)


@pytest.mark.parametrize(
    "source_id, code",
    [
        ("gdelt-delhi", "DISABLED"),  # off by default: never shown connected or healthy
        ("new-indian-express-chennai", "AWAITING_PERMISSION"),
        ("mid-day-mumbai", "BLOCKED_BY_TERMS"),
        ("siasat", "BLOCKED_BY_TERMS"),
        ("the-hans-india", "REMOVED"),
        ("mumbai-traffic-police-notifications", "REMOVED"),
        ("canada-provincial-511-apis", "NEEDS_CREDENTIALS"),
        ("manual-entry", "MANUAL_ONLY"),
        ("tfl-road-disruptions", "NOT_SCHEDULED"),  # connected, official feeds not scheduled here
        ("google-news-rss-hyderabad", "BLOCKED_BY_TERMS"),
    ],
)
def test_each_kind_of_source_has_its_own_state(source_id, code):
    state = source_state(_row(source_id))
    assert state.code == code and state.label
    assert state.polled is False


def test_a_polled_source_is_collecting_quiet_failing_or_not_polled_yet():
    never = _row("telangana-today")
    assert source_state(never).code == "NOT_POLLED_YET"

    ok = _row("telangana-today", last_poll_at=NOW, last_success_at=NOW)
    collecting = source_state(ok, Counter(recent=3))
    assert (collecting.code, collecting.polled) == ("COLLECTING", True)
    assert "3 road events" in collecting.reason
    # Polls well, found nothing lately: not failing.
    quiet = source_state(ok, Counter())
    assert quiet.code == "NO_RECENT_EVENTS" and "Polled successfully" in quiet.reason

    failing = _row(
        "telangana-today", last_poll_at=NOW, last_success_at=NOW - timedelta(hours=2),
        last_failure_at=NOW, last_error="HTTP 503",
    )  # fmt: skip
    assert source_state(failing, Counter(recent=5)).code == "FAILING"
    never_ok = _row("telangana-today", last_poll_at=NOW, last_failure_at=NOW, last_error="HTTP 500")
    assert "never been polled successfully" in source_state(never_ok).reason


def test_every_registered_source_gets_a_known_state():
    known = {
        "COLLECTING", "NO_RECENT_EVENTS", "FAILING", "NOT_POLLED_YET", "NOT_SCHEDULED", "DISABLED",
        "AWAITING_PERMISSION", "BLOCKED_BY_TERMS", "BLOCKED", "REMOVED", "NEEDS_CREDENTIALS",
        "RESEARCHED", "MANUAL_ONLY",
    }  # fmt: skip
    states = {s.definition.source_id: source_state(_row(s.definition.source_id)) for s in REGISTERED_SOURCES}
    assert {state.code for state in states.values()} <= known
    # Only connected and switched-on sources are ever polled.
    polled = {sid for sid, state in states.items() if state.polled}
    connected = {s.definition.source_id for s in REGISTERED_SOURCES if s.definition.active and s.create_connector}
    assert polled == connected


# --- through the API ---------------------------------------------------------------


def ingest(client):
    response = client.post("/api/ingestion/run", params={"source_id": TEST_SOURCE.source_id})
    assert response.status_code == 200


def test_the_api_lists_every_source_with_its_state(client, app):
    with app.state.session_factory() as session:
        SourceRepository(session).sync_registry(s.definition for s in REGISTERED_SOURCES)
        session.commit()
    sources = {s["source_id"]: s for s in client.get("/api/sources").json()}
    assert sources["gdelt-delhi"]["status"] == "DISABLED"
    assert sources["gdelt-delhi"]["status_label"] == "Off: disabled by configuration"
    assert "GDELT_SEARCH_ENABLED" in sources["gdelt-delhi"]["status_reason"]
    assert sources["mid-day-mumbai"]["status"] == "BLOCKED_BY_TERMS"
    assert sources["new-indian-express-delhi"]["status"] == "AWAITING_PERMISSION"
    # The connected filter still works for callers that want only those.
    connected = client.get("/api/sources", params={"integration_status": "CONNECTED"}).json()
    assert all(s["integration_status"] == "CONNECTED" for s in connected)


def test_a_sources_counts_are_its_real_events(client, session):
    ingest(client)
    test_news = next(s for s in client.get("/api/sources").json() if s["source_id"] == TEST_SOURCE.source_id)
    events = list(session.scalars(select(Event).where(Event.source_id == TEST_SOURCE.source_id)))
    assert test_news["status"] == "COLLECTING"
    assert test_news["recent_event_count"] == len(events) == test_news["pending_review_count"]
    # The synthetic articles give no location: none is on either map.
    assert (test_news["on_map_review_count"], test_news["on_map_operations_count"]) == (0, 0)
    assert "on_map_count" not in test_news


def test_coverage_separates_detected_review_validated_and_on_the_map(client, session):
    ingest(client)
    rows = list(session.scalars(select(Event).order_by(Event.event_id)))
    assert len(rows) >= 3
    for row in rows[:3]:
        row.geometry = {"type": "Point", "coordinates": [78.4867, 17.385]}
    rows[0].status, rows[0].start_time, rows[0].end_time = "APPROVED", NOW - timedelta(hours=1), NOW + timedelta(hours=1)
    rows[1].start_time, rows[1].end_time = NOW + timedelta(days=1), NOW + timedelta(days=2)
    rows[2].start_time, rows[2].end_time = NOW - timedelta(days=3), NOW - timedelta(days=1)  # ended
    session.commit()

    def hyderabad():
        cities = client.get("/api/events/coverage").json()["cities"]
        return next(c for c in cities if c["city_id"] == "hyderabad")

    found = hyderabad()
    assert found["detected"] == len(rows)
    assert (found["validated"], found["pending_review"]) == (1, len(rows) - 1)
    # Each map counted on its own, never added up.
    assert (found["on_map_review"], found["on_map_operations"]) == (1, 1)
    assert "on_map" not in found
    assert found["hidden_review"]["ended"] == 1
    assert found["hidden_review"].get("no_location", 0) == len(rows) - 3
    assert found["hidden_operations"] == {}
    # The same numbers the console's lists show.
    review = client.get("/api/events", params={"view": "validation", "city": "hyderabad"}).json()["total"]
    operations = client.get("/api/events", params={"view": "current_upcoming", "city": "hyderabad"}).json()["total"]
    assert (review, operations) == (found["on_map_review"], found["on_map_operations"])

    # Located but with no stated start: hidden, and counted as such.
    rows[2].start_time = rows[2].end_time = None
    session.commit()
    assert hyderabad()["hidden_review"]["no_start"] == 1


def test_a_validated_event_that_ended_is_hidden_from_the_operations_map_only(client, session):
    ingest(client)
    rows = list(session.scalars(select(Event).order_by(Event.event_id)))
    for row in rows[:2]:
        row.geometry = {"type": "Point", "coordinates": [78.4867, 17.385]}
        row.status = "APPROVED"
    rows[0].start_time, rows[0].end_time = NOW - timedelta(hours=1), NOW + timedelta(hours=1)
    rows[1].start_time, rows[1].end_time = NOW - timedelta(days=3), NOW - timedelta(days=1)
    session.commit()

    found = next(c for c in client.get("/api/events/coverage").json()["cities"] if c["city_id"] == "hyderabad")
    assert (found["validated"], found["on_map_operations"]) == (2, 1)
    assert found["hidden_operations"] == {"ended": 1}
    # Pending events never count towards the operations map.
    assert found["on_map_operations"] + sum(found["hidden_operations"].values()) == found["validated"]
    assert found["on_map_review"] + sum(found["hidden_review"].values()) == found["pending_review"]
    test_news = next(s for s in client.get("/api/sources").json() if s["source_id"] == TEST_SOURCE.source_id)
    assert (test_news["validated_count"], test_news["on_map_operations_count"]) == (2, 1)
    assert test_news["on_map_review_count"] == 0
