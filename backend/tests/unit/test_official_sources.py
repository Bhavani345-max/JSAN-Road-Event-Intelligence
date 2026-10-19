"""Official sources (6 October 2026): Transport for London and the City of Toronto.

The fixtures are real records returned by each feed on 6 October 2026, kept
unchanged. Their events are built from what the source states, the source's
geometry is preserved as it is, and every event still needs validation.
"""

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy import func, select

from app.models import Event, SourceArtifact
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from app.services.reprocess_service import record_from_artifact
from connectors.base import ConnectorError
from connectors.official import (
    TflRoadDisruptionsConnector,
    TorontoRoadRestrictionsConnector,
    tfl_source,
    toronto_source,
)
from connectors.official.common import select_for_run
from connectors.official.tfl import ATTRIBUTION as TFL_ATTRIBUTION
from connectors.official.tfl import to_record as tfl_record
from connectors.official.toronto import to_record as toronto_record
from connectors.registry import registered_sources
from packages.cities import get_city
from packages.event_schema import EventDirection, EventStatus, EventType, LocationClass
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass, TermsStatus
from services.extraction import KeywordClassifier, build_event_from_source, classify_source_record
from services.ingestion import run_ingestion
from tests.support import FakeConnector


@pytest.fixture(autouse=True)
def _no_minimum_length(monkeypatch):
    """These tests use the real 28 m Toronto closure in the fixtures to test
    something else; the 200 m minimum is tested in test_road_block_minimum.py."""
    monkeypatch.setattr("packages.source_models.road_block.MIN_ROAD_BLOCK_LENGTH_M", 0)


FIXTURES = Path(__file__).parents[1] / "fixtures"
TFL = json.loads((FIXTURES / "tfl_road_disruptions_2026-10-06.json").read_text(encoding="utf-8"))[
    "records"
]
TORONTO = json.loads(
    (FIXTURES / "toronto_road_restrictions_2026-10-06.json").read_text(encoding="utf-8")
)["Closure"]
NOW = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
LONDON = get_city("london")
TORONTO_CITY = get_city("toronto")


def by_id(records, record_id):
    return next(record for record in records if record["id"] == record_id)


def event_of(record, city):
    return build_event_from_source(record, classify_source_record(record, city), now=NOW)


# --- registry -------------------------------------------------------------------


@pytest.mark.parametrize("source_id, city", [("tfl-road-disruptions", "london"), ("toronto-road-restrictions", "toronto")])
def test_official_sources_are_tier_one_and_connected_but_not_scheduled(source_id, city):
    registered = {s.definition.source_id: s for s in registered_sources()}[source_id]
    definition = registered.definition
    assert definition.source_class is SourceClass.AUTHORITATIVE_OFFICIAL
    assert definition.source_tier == 1 and definition.discovery_only is False
    assert definition.city == city
    assert definition.integration_status is IntegrationStatus.CONNECTED
    # International test phase: run by hand, never by the scheduler.
    assert definition.active is False and registered.create_connector is not None
    assert definition.provides_geometry and definition.real_time
    # The licence was read; it is recorded, not taken as a legal review.
    assert definition.terms_status is TermsStatus.PERMITS_TESTING
    assert definition.terms_reviewed is False
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    assert definition.licence and definition.attribution


def test_official_sources_are_scheduled_only_when_asked():
    sources = {s.definition.source_id: s.definition for s in registered_sources(official_feeds_scheduled=True)}
    assert sources["tfl-road-disruptions"].active and sources["toronto-road-restrictions"].active


# --- Transport for London ----------------------------------------------------


def test_a_tfl_collision_keeps_tfls_own_area_streets_and_direction():
    record = tfl_record(by_id(TFL, "TIMS-235979"), NOW)
    event = event_of(record, LONDON)
    disruption = by_id(TFL, "TIMS-235979")

    assert event.title.startswith("Vehicle collision: [A13] NEWHAM WAY")
    assert event.event_type is EventType.ACCIDENT
    assert event.city == "London"
    assert event.start_time == datetime(2026, 10, 6, 7, 56, 15, tzinfo=timezone.utc)
    assert event.end_time == datetime(2026, 10, 6, 23, 59, 59, tzinfo=timezone.utc)
    # TfL's polygon, exactly as published.
    assert event.geometry.type == "Polygon"
    assert [list(p) for p in event.geometry.coordinates[0]] == disruption["geometry"]["coordinates"][0]
    assert event.detection.location_class is LocationClass.SOURCE_PROVIDED
    assert event.detection.location.method == "source_provided"
    # The street, its segments as lines, its direction and lane closure.
    [street] = event.detection.affected_locations
    assert street.name.startswith("[A13] NEWHAM WAY")
    assert street.geometry.type == "MultiLineString"
    assert street.resolution is LocationClass.SOURCE_PROVIDED
    assert (street.direction, street.closure) == ("Westbound", "Open")
    assert event.direction is EventDirection.WESTBOUND
    # TfL's severity in TfL's words; REI's own severity and confidence stay empty.
    assert event.detection.source_severity == "Serious"
    assert event.severity is None and event.confidence is None
    assert event.detection.attribution == TFL_ATTRIBUTION
    assert event.status is EventStatus.VALIDATION_REQUIRED


def test_a_tfl_multipolygon_is_preserved():
    event = event_of(tfl_record(by_id(TFL, "TIMS-235733"), NOW), LONDON)
    assert event.geometry.type == "MultiPolygon"
    assert event.event_type is EventType.ROAD_WORKS
    assert event.detection.source_category == "Works / Utility works"


def test_a_tfl_category_with_no_clear_type_gets_none():
    event = event_of(tfl_record(by_id(TFL, "TIMS-235973"), NOW), LONDON)
    assert event.event_type is None
    assert event.detection.source_category == "Emergency service incidents / Police activity"
    # A point is all TfL gives here, and it is TfL's point.
    assert event.geometry.type == "Point"


def test_a_tfl_record_with_no_position_and_no_streets_makes_no_event():
    disruption = copy.deepcopy(by_id(TFL, "TIMS-235973"))
    disruption.update(point=None, geography=None, geometry=None, streets=[])
    record = tfl_record(disruption, NOW)
    assert record.structured.geometry is None
    assert not classify_source_record(record, LONDON).is_relevant
    assert event_of(record, LONDON) is None


def test_a_tfl_record_with_streets_but_no_position_keeps_them_unresolved():
    disruption = copy.deepcopy(by_id(TFL, "TIMS-235979"))
    disruption.update(point=None, geography=None, geometry=None)
    for street in disruption["streets"]:
        street["segments"] = []
    event = event_of(tfl_record(disruption, NOW), LONDON)
    assert event.geometry is None
    assert event.detection.location_class is LocationClass.UNRESOLVED
    assert [loc.resolution for loc in event.detection.affected_locations] == [LocationClass.UNRESOLVED]


# --- City of Toronto ----------------------------------------------------------


def test_a_toronto_closure_keeps_the_citys_line_and_both_directions():
    item = by_id(TORONTO, "Tor-RD1S2026-338-1")
    event = event_of(toronto_record(item, NOW), TORONTO_CITY)
    assert event.title.startswith("Road closed: ")
    assert event.event_type is EventType.PLANNED_ROAD_CLOSURE
    assert event.city == "Toronto"
    assert event.geometry.type == "LineString"
    assert [list(p) for p in event.geometry.coordinates] == json.loads(f"[{item['geoPolyline']}]")
    assert event.direction is EventDirection.BOTH_DIRECTIONS
    assert event.start_time == datetime.fromtimestamp(int(item["startTime"]) / 1000, tz=timezone.utc)
    assert event.detection.attribution.startswith("Contains information licensed")


def test_a_toronto_work_type_sent_as_a_table_fragment_is_read():
    event = event_of(toronto_record(by_id(TORONTO, "Tor-RD52026-5941-2"), NOW), TORONTO_CITY)
    assert event.event_type is EventType.ROAD_WORKS
    assert "{" not in event.detection.source_category
    # "ONE_DIRECTION" does not say which one: the event's direction stays empty.
    assert event.direction is None
    assert event.detection.affected_locations[0].direction == "ONE_DIRECTION"


def test_a_toronto_polyline_of_one_position_is_a_point():
    event = event_of(toronto_record(by_id(TORONTO, "Tor-RDAR2024-3900-1"), NOW), TORONTO_CITY)
    assert event.geometry.type == "Point"


# --- city boundary ------------------------------------------------------------


def test_a_record_outside_the_citys_area_is_not_that_citys_event():
    item = copy.deepcopy(by_id(TORONTO, "Tor-RD1S2026-338-1"))
    item["geoPolyline"] = "[-73.567,45.501],[-73.566,45.502]"  # Montreal
    record = toronto_record(item, NOW)
    classification = classify_source_record(record, TORONTO_CITY)
    assert not classification.is_relevant and classification.city is None
    assert event_of(record, TORONTO_CITY) is None
    # And a London record is not Toronto's.
    assert event_of(tfl_record(by_id(TFL, "TIMS-235979"), NOW), TORONTO_CITY) is None


# --- choosing what a run keeps ------------------------------------------------


def test_a_run_keeps_current_and_upcoming_records_most_recent_first_up_to_the_limit():
    items = [
        ("ended", NOW - timedelta(days=9), NOW - timedelta(days=1), 5),
        ("now-old-update", NOW - timedelta(days=3), NOW + timedelta(days=3), 1),
        ("now-new-update", NOW - timedelta(days=3), NOW + timedelta(days=3), 9),
        ("next-week", NOW + timedelta(days=5), NOW + timedelta(days=9), 7),
        ("next-month", NOW + timedelta(days=30), NOW + timedelta(days=40), 8),
    ]
    kept = select_for_run(
        items, now=NOW, start=lambda i: i[1], end=lambda i: i[2], order=lambda i: i[3], limit=2
    )
    assert [i[0] for i in kept] == ["now-new-update", "next-week"]
    everything = select_for_run(
        items, now=NOW, start=lambda i: i[1], end=lambda i: i[2], order=lambda i: i[3], limit=None
    )
    assert [i[0] for i in everything] == ["now-new-update", "next-week", "now-old-update"]


def test_the_tfl_connector_applies_the_limit():
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=TFL)))
    connector = TflRoadDisruptionsConnector(
        tfl_source(scheduled=False), "ua", max_records=2, client=client, clock=lambda: NOW
    )
    assert len(connector.fetch()) == 2


@pytest.mark.parametrize(
    "response, message",
    [
        (httpx.Response(429), "rate limited"),
        (httpx.Response(503), "rate limited"),
        (httpx.Response(500), "HTTP 500"),
        (httpx.Response(200, content=b"<html>maintenance</html>"), "did not return JSON"),
        (httpx.Response(200, json={"not": "a list"}), r"not a list \(keys: not\)"),
        (
            httpx.Response(
                200,
                json={
                    "$type": "Tfl.Api.Presentation.Entities.ApiError, Tfl.Api.Presentation.Entities",
                    "httpStatusCode": 500,
                    "message": "Service temporarily unavailable",
                },
            ),
            r"not a list: \$type Tfl\.Api\.Presentation\.Entities\.ApiError.*httpStatusCode 500; "
            r"message Service temporarily unavailable",
        ),
    ],
)
def test_tfl_failures_are_errors_not_events(response, message):
    client = httpx.Client(transport=httpx.MockTransport(lambda r: response))
    connector = TflRoadDisruptionsConnector(tfl_source(scheduled=False), "ua", client=client)
    with pytest.raises(ConnectorError, match=message):
        connector.fetch()


def test_a_toronto_timeout_is_an_error():
    def handler(request):
        raise httpx.ReadTimeout("timed out", request=request)

    connector = TorontoRoadRestrictionsConnector(
        toronto_source(scheduled=False), "ua", client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(ConnectorError, match="timed out"):
        connector.fetch()


def test_an_app_key_is_sent_only_when_configured():
    seen = []

    def handler(request):
        seen.append(dict(request.url.params))
        return httpx.Response(200, json=[])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    TflRoadDisruptionsConnector(tfl_source(scheduled=False), "ua", client=client).fetch()
    TflRoadDisruptionsConnector(tfl_source(scheduled=False), "ua", app_key="k", client=client).fetch()
    assert seen == [{}, {"app_key": "k"}]


# --- through the pipeline ------------------------------------------------------


@pytest.fixture
def london_session(session):
    SourceRepository(session).sync_registry([tfl_source(scheduled=False)])
    session.commit()
    return session


def ingest(session, records):
    result = run_ingestion(
        FakeConnector(records, source=tfl_source(scheduled=False)),
        KeywordClassifier.for_city(LONDON),
        SqlIngestionStore(session),
        None,
        LONDON,
    )
    session.commit()
    return result


def test_official_records_become_events_once(london_session):
    records = [tfl_record(item, NOW) for item in TFL]
    first = ingest(london_session, records)
    assert (first.new_artifacts, first.events_created) == (4, 4)
    again = ingest(london_session, records)
    assert (again.new_artifacts, again.duplicates, again.events_created) == (0, 4, 0)
    events = london_session.scalars(select(Event)).unique().all()
    assert {event.status for event in events} == {"VALIDATION_REQUIRED"}
    artifacts = london_session.scalars(select(SourceArtifact)).all()
    assert {a.classification for a in artifacts} == {"SOURCE_PROVIDED_EVENT"}
    assert {a.classification_details["method"] for a in artifacts} == {"source_provided"}


def test_stored_evidence_rebuilds_the_same_event(london_session):
    ingest(london_session, [tfl_record(by_id(TFL, "TIMS-235979"), NOW)])
    artifact = london_session.scalars(select(SourceArtifact)).one()
    # The disruption exactly as TfL sent it is the evidence.
    assert artifact.raw_content["disruption"] == by_id(TFL, "TIMS-235979")
    rebuilt = record_from_artifact(artifact)
    assert rebuilt.structured == tfl_record(by_id(TFL, "TIMS-235979"), NOW).structured
    row = london_session.scalars(select(Event)).one()
    assert event_of(rebuilt, LONDON).geometry.model_dump(mode="json") == row.geometry


def test_a_failing_source_keeps_the_evidence_it_already_gave(london_session):
    ingest(london_session, [tfl_record(item, NOW) for item in TFL])
    before = london_session.scalar(select(func.count()).select_from(SourceArtifact))
    with pytest.raises(ConnectorError):
        run_ingestion(
            FakeConnector([], source=tfl_source(scheduled=False), error="feed down"),
            KeywordClassifier.for_city(LONDON),
            SqlIngestionStore(london_session),
            None,
            LONDON,
        )
    london_session.rollback()
    assert london_session.scalar(select(func.count()).select_from(SourceArtifact)) == before
    assert london_session.scalar(select(func.count()).select_from(Event)) == before
