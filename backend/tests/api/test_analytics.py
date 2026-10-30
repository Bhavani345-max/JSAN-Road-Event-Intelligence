"""The Analytics endpoint (decision 0051): exact counts of known events, read only."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.models import Event, EventVersion
from app.repositories.events import EventRepository
from app.repositories.sources import SourceRepository
from connectors.rss.telangana_today import TELANGANA_TODAY
from packages.event_schema import EventDetection, EventStatus, GisResolution, LocationClass, ReiEvent
from packages.geo_models import Point
from tests.support import TEST_SOURCE

NOW = datetime.now(timezone.utc)
# 19:00 UTC on 1 October is 00:30 on 2 October in Hyderabad (UTC+05:30).
LATE_UTC = datetime(2026, 10, 1, 19, 0, tzinfo=timezone.utc)


def add(session, event_id, *, status="VALIDATION_REQUIRED", city="Hyderabad", event_type="ROAD_WORKS",
        source=TEST_SOURCE, created=None, located=True, location_class=LocationClass.SOURCE_PROVIDED,
        start=None, end=None, gis_pending=False, merged_into=None):  # fmt: skip
    created = created or NOW - timedelta(days=1)
    gis = (
        GisResolution(engine="test", network="test", resolved_at=created, applied=True, review_status="PENDING")
        if gis_pending
        else None
    )
    event = ReiEvent(
        event_id=event_id, source_id=source.source_id, title=f"Event {event_id}", event_type=event_type,
        city=city, start_time=start, end_time=end, status=EventStatus(status),
        geometry=Point(type="Point", coordinates=(78.4, 17.4)) if located else None,
        detection=EventDetection(
            method="source_provided", score=None, matched_keywords=[], location_class=location_class, gis=gis,
        ),
        created_at=created, updated_at=created,
    )  # fmt: skip
    row = EventRepository(session).add(event, artifact_id=None, change_reason="Created", changed_by="ingestion")
    row.merged_into = merged_into
    session.commit()


@pytest.fixture
def events(session):
    """Twelve stored events, one of them merged, with known statuses, places, types and locations."""
    SourceRepository(session).sync_registry([TEST_SOURCE, TELANGANA_TODAY])
    session.commit()
    started = NOW - timedelta(days=2)
    # Awaiting review: 4 (one approximate, one not located, one with a GIS match pending).
    add(session, "EVT-R1")
    add(session, "EVT-R2", location_class=LocationClass.APPROXIMATE, event_type="TRAFFIC_DIVERSION")
    add(session, "EVT-R3", located=False, location_class=None, event_type=None)
    add(session, "EVT-R4", status="QC_PENDING", location_class=LocationClass.GIS_RESOLVED, gis_pending=True)
    # Validated: 3; two on the operations map (located, started, not over), one ended.
    add(session, "EVT-V1", status="APPROVED", start=started, source=TELANGANA_TODAY)
    add(session, "EVT-V2", status="ACTIVE", start=started, city="London", event_type="LANE_RESTRICTION")
    add(session, "EVT-V3", status="SCHEDULED", start=started, end=NOW - timedelta(hours=1))
    # Closed: 2. Rejected: 2.
    add(session, "EVT-C1", status="EXPIRED")
    add(session, "EVT-C2", status="CANCELLED", city="London")
    add(session, "EVT-J1", status="REJECTED", location_class=LocationClass.APPROXIMATE)
    add(session, "EVT-J2", status="REJECTED", created=LATE_UTC)
    # Merged into EVT-R1: part of that event, not counted again.
    add(session, "EVT-M1", merged_into="EVT-R1")
    return session


def analytics(client, **params):
    response = client.get("/api/events/analytics", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_status_groups_are_exclusive_and_add_up_to_the_total(client, events):
    totals = analytics(client)["totals"]
    assert {key: value for key, value in totals.items() if key != "in_review_queue"} == {
        "total": 11,
        "awaiting_review": 4,
        "validated": 3,
        "closed": 2,
        "rejected": 2,
        "published": 2,
        "gis_pending": 4,
        "merged": 1,
    }
    assert sum(totals[g] for g in ("awaiting_review", "validated", "closed", "rejected")) == totals["total"]


def test_subsets_match_the_consoles_own_counts(client, events):
    # The same rules the console's coverage counts use (decision 0034): never two answers.
    totals = analytics(client)["totals"]
    coverage = client.get("/api/events/coverage").json()["cities"]
    assert totals["in_review_queue"] == sum(city["listed_review"] for city in coverage)
    assert totals["published"] == sum(city["on_map_operations"] for city in coverage)
    assert totals["awaiting_review"] == sum(city["pending_review"] for city in coverage)
    # A subset of awaiting review: the not-located event R3 is never in the queue.
    assert 0 < totals["in_review_queue"] < totals["awaiting_review"]


def test_subsets_are_counted_by_their_own_rules(client, events):
    totals = analytics(client)["totals"]
    # Published: validated, located, started and not over (EVT-V1, EVT-V2; EVT-V3 has ended).
    assert totals["published"] == 2
    # GIS pending: approximate (R2, J1), not located (R3), match awaiting review (R4).
    assert totals["gis_pending"] == 4


def test_breakdowns_count_every_event_once(client, events):
    body = analytics(client)
    as_dict = lambda rows: {row["key"]: row["count"] for row in rows}  # noqa: E731
    assert as_dict(body["by_city"]) == {"Hyderabad": 9, "London": 2}
    assert as_dict(body["by_category"]) == {
        "ROAD_WORKS": 8, "TRAFFIC_DIVERSION": 1, "LANE_RESTRICTION": 1, "UNCLASSIFIED": 1,
    }  # fmt: skip
    assert as_dict(body["by_status"])["REJECTED"] == 2
    assert sum(as_dict(body["by_status"]).values()) == 11
    assert as_dict(body["by_location"]) == {
        "SOURCE_PROVIDED": 7, "APPROXIMATE": 2, "NOT_LOCATED": 1, "GIS_PENDING": 1,
    }  # fmt: skip
    assert sum(row["count"] for row in body["by_day"]) == 11
    london = next(row for row in body["validation_by_city"] if row["key"] == "London")
    assert london == {"key": "London", "awaiting_review": 0, "validated": 1, "closed": 1, "rejected": 0}
    sources = {row["source_id"]: row for row in body["by_source"]}
    assert sources["telangana-today"]["total"] == 1
    assert sources["telangana-today"]["source_name"] == "Telangana Today"
    assert sources[TEST_SOURCE.source_id]["total"] == 10


def test_days_and_the_date_range_use_the_same_time_zone(client, events):
    # The rejected event stored at 19:00 UTC on 1 October: 2 October in Hyderabad.
    utc = analytics(client, start="2026-10-01", end="2026-10-01", tz="UTC")
    ist = analytics(client, start="2026-10-02", end="2026-10-02", tz="Asia/Kolkata")
    assert utc["totals"]["total"] == 1 and utc["by_day"] == [{"date": "2026-10-01", "count": 1}]
    assert ist["totals"]["total"] == 1 and ist["by_day"] == [{"date": "2026-10-02", "count": 1}]
    assert ist["time_zone"] == "Asia/Kolkata"
    # 1 October in Hyderabad ends at 18:30 UTC: the event is not in it.
    assert analytics(client, start="2026-10-01", end="2026-10-01", tz="Asia/Kolkata")["totals"]["total"] == 0


def test_filters_narrow_every_number(client, events):
    london = analytics(client, city="london")["totals"]
    assert (london["total"], london["validated"], london["closed"]) == (2, 1, 1)
    validated = analytics(client, status_group="validated")["totals"]
    assert (validated["total"], validated["validated"], validated["awaiting_review"]) == (3, 3, 0)
    both = analytics(client, status_group=["closed", "rejected"])["totals"]
    assert both["total"] == 4
    typed = analytics(client, event_type=["TRAFFIC_DIVERSION", "UNCLASSIFIED"])["totals"]
    assert typed["total"] == 2
    source = analytics(client, source_id="telangana-today")["totals"]
    assert (source["total"], source["published"]) == (1, 1)


def test_an_event_stored_before_cities_existed_is_hyderabads(client, events):
    # As the event list treats it (repositories/events.py): legacy events have no city.
    add(events, "EVT-L1", city=None)
    by_city = {row["key"]: row["count"] for row in analytics(client)["by_city"]}
    assert by_city["Hyderabad"] == 10
    assert analytics(client, city="hyderabad")["totals"]["total"] == 10


def test_no_events_is_an_empty_answer_not_an_error(client, events):
    body = analytics(client, start="2020-01-01", end="2020-01-03")
    assert body["totals"]["total"] == 0
    assert body["by_city"] == [] and body["by_source"] == []
    assert [day["count"] for day in body["by_day"]] == [0, 0, 0]


def test_every_number_is_defined_in_words(client, events):
    definitions = analytics(client)["definitions"]
    for key in ("total", "awaiting_review", "validated", "closed", "rejected", "published", "gis_pending"):
        assert definitions[key]
    assert "subset" in definitions["published"].lower()


@pytest.mark.parametrize(
    "params",
    [{"tz": "Mars/Olympus"}, {"start": "2026-10-05", "end": "2026-10-01"}, {"status_group": "done"},
     {"event_type": "TRAFFIC_JAM"}, {"city": "atlantis"}],  # fmt: skip
)
def test_bad_questions_are_refused(client, events, params):
    assert client.get("/api/events/analytics", params=params).status_code == 422


def test_counting_changes_nothing(client, events, session):
    def snapshot():
        session.expire_all()
        return (
            session.scalar(select(func.count()).select_from(Event)),
            session.scalar(select(func.count()).select_from(EventVersion)),
            tuple(session.execute(select(Event.event_id, Event.status, Event.version).order_by(Event.event_id))),
        )

    before = snapshot()
    analytics(client)
    analytics(client, city="hyderabad", tz="Asia/Kolkata", status_group="awaiting_review")
    assert snapshot() == before


def test_analytics_needs_a_signed_in_user(app, events):
    from fastapi.testclient import TestClient

    with TestClient(app) as anonymous:
        assert anonymous.get("/api/events/analytics").status_code == 401
