"""The console's lists filtered by the database give exactly what the view rule gives.

`EventRepository.list` without a text search lets the database apply the
column part of `matches_event_view` and loads only the page (decision 0029).
These tests compare it with the rule itself, event by event, on a mix of
events: every status phase, with and without times, location, a past end,
and an end the source reports.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.models import Event
from app.repositories.events import EventRepository, to_rei_event
from packages.common.time import utc_now
from services.lifecycle.current import EventListView, matches_event_view
from tests.support import TEST_SOURCE

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
DAY = timedelta(days=1)
POINT = {"type": "Point", "coordinates": [78.4867, 17.385]}
CASES = [
    # status, start, end, located, reported over
    ("VALIDATION_REQUIRED", NOW - DAY, NOW + DAY, True, False),
    ("VALIDATION_REQUIRED", NOW - DAY, NOW + DAY, False, False),
    ("VALIDATION_REQUIRED", NOW - DAY, None, True, False),
    ("VALIDATION_REQUIRED", None, NOW + DAY, True, False),
    ("VALIDATION_REQUIRED", NOW - 3 * DAY, NOW - DAY, True, False),
    ("QC_PENDING", NOW + DAY, NOW + 2 * DAY, True, False),
    ("QC_PENDING", NOW - DAY, NOW + DAY, True, True),
    ("APPROVED", NOW - DAY, NOW + DAY, True, False),
    ("APPROVED", NOW + DAY, NOW + 2 * DAY, True, False),
    ("APPROVED", NOW - DAY, NOW, True, False),
    ("APPROVED", NOW - DAY, NOW + DAY, True, True),
    ("APPROVED", NOW - 3 * DAY, NOW - DAY, True, False),
    ("APPROVED", None, None, True, False),
    ("SCHEDULED", NOW + DAY, NOW + 3 * DAY, True, False),
    ("REJECTED", NOW - DAY, NOW + DAY, True, False),
    ("EXPIRED", NOW - 3 * DAY, NOW - DAY, True, False),
    # For the history and rejected views (19 October 2026).
    ("REJECTED", NOW - 3 * DAY, NOW - DAY, True, True),
    ("CANCELLED", NOW + DAY, NOW + 2 * DAY, False, False),
    ("SUPERSEDED", None, None, True, False),
    ("VALIDATION_REQUIRED", None, None, False, True),
    ("VALIDATION_REQUIRED", None, NOW - DAY, False, False),
    ("APPROVED", None, NOW + DAY, True, True),
]


@pytest.fixture
def mixed(session):
    for index, (status, start, end, located, over) in enumerate(CASES):
        session.add(
            Event(
                event_id=f"EVT-LIST{index:06d}",
                source_id=TEST_SOURCE.source_id,
                title=f"Case {index}",
                status=status,
                start_time=start,
                end_time=end,
                geometry=POINT if located else None,
                detection={"method": "test", "matched_keywords": [], "source_reports_ended": over},
                version=1,
                # Different creation times give a definite order.
                created_at=utc_now() - timedelta(minutes=index),
                updated_at=utc_now(),
            )
        )
    session.commit()
    return session


@pytest.mark.parametrize("view", list(EventListView))
def test_the_database_filtered_list_equals_the_view_rule(mixed, view):
    repository = EventRepository(mixed)
    # The rule applied by hand to every event, in the list's own order.
    ordered = sorted(
        mixed.query(Event).all(), key=lambda row: (-row.created_at.timestamp(), row.event_id)
    )
    expected = [row.event_id for row in ordered if matches_event_view(to_rei_event(row), view, now=NOW)]
    assert expected, "every view lists at least one of the cases"
    shown, total = repository.list(view=view, limit=1000, now=NOW)
    assert [row.event_id for row in shown] == expected
    assert total == len(expected)


@pytest.mark.parametrize("view", [EventListView.HISTORY, EventListView.REJECTED])
def test_the_history_and_rejected_lists_keep_every_record_hidden_or_not(mixed, view):
    """`include_hidden` changes nothing for them, and a text search gives the same rule."""
    repository = EventRepository(mixed)
    plain = [row.event_id for row in repository.list(view=view, limit=1000, now=NOW)[0]]
    hidden_too = [row.event_id for row in repository.list(view=view, include_hidden=True, limit=1000, now=NOW)[0]]
    searched = [row.event_id for row in repository.list(view=view, q="case", limit=1000, now=NOW)[0]]
    assert plain == hidden_too == searched


@pytest.mark.parametrize("view", [EventListView.VALIDATION, EventListView.HISTORY])
def test_the_database_filtered_list_pages_without_losing_or_repeating_events(mixed, view):
    repository = EventRepository(mixed)
    _, total = repository.list(view=view, limit=1000, now=NOW)
    pages = [
        [row.event_id for row in repository.list(view=view, limit=1, offset=n, now=NOW)[0]]
        for n in range(total + 1)
    ]
    flat = [event_id for page in pages for event_id in page]
    assert len(flat) == len(set(flat)) == total
    assert pages[-1] == []


def test_the_overview_counts_per_city_what_each_view_lists(mixed, client):
    """GET /api/events/summary: per entry, its own events, by status and type; a
    country's list is its row plus its cities' rows (decisions 0035, 0036)."""
    from packages.cities import area_of, get_city

    canada = mixed.get(Event, "EVT-LIST000000")
    canada.city = "Canada"
    mixed.commit()
    for view in ("current_upcoming", "validation"):
        summary = client.get("/api/events/summary", params={"view": view}).json()
        by_city = {entry["city_id"]: entry for entry in summary["cities"]}
        assert {"canada", "australia", "south-africa", "hyderabad", "india"} <= set(by_city)
        for city_id, entry in by_city.items():
            listed = client.get("/api/events", params={"view": view, "city": city_id, "limit": 500}).json()
            rows = [by_city[city.id] for city in area_of(get_city(city_id))]
            assert sum(row["total"] for row in rows) == listed["total"], (view, city_id)
            assert sum(entry["by_status"].values()) == entry["total"]
            statuses = {status for row in rows for status in row["by_status"]}
            assert sorted(statuses) == sorted({item["status"] for item in listed["items"]})
    assert client.get("/api/events/summary", params={"view": "history"}).status_code == 422
