"""Official sources connected on 14 October 2026 (decision 0027): NYC permitted
events, DiaLog traffic orders (France) and the Métropole de Lyon's works.

The fixtures are real records each source returned on 14 October 2026, kept
unchanged. Events are built only from what the source states; every event
still needs validation.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from app.models import Event, SourceArtifact
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from app.services.reprocess_service import record_from_artifact
from connectors.official import (
    DialogTrafficOrdersConnector,
    LyonDisruptiveWorksConnector,
    NycPermittedEventsConnector,
    dialog_source,
    lyon_source,
    nyc_events_source,
)
from connectors.official import dialog, lyon, nyc_events
from connectors.registry import registered_sources
from packages.cities import get_city
from packages.event_schema import EventType, LocationClass
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass, TermsStatus
from services.extraction import KeywordClassifier, build_event_from_source, classify_source_record
from services.ingestion import run_ingestion
from tests.support import FakeConnector

FIXTURES = Path(__file__).parents[1] / "fixtures"
NYC_ROWS = json.loads((FIXTURES / "nyc_permitted_events_2026-10-14.json").read_text(encoding="utf-8"))["rows"]
REGULATIONS = json.loads((FIXTURES / "dialog_regulations_2026-10-14.json").read_text(encoding="utf-8"))[
    "regulations"
]
LYON = json.loads((FIXTURES / "lyon_chantiers_perturbants_2026-10-14.json").read_text(encoding="utf-8"))[
    "features"
]
NOW = datetime(2026, 10, 14, 16, 0, tzinfo=timezone.utc)
NEW_YORK = get_city("new-york")
FRANCE = get_city("france")


def row(event_id):
    return next(item for item in NYC_ROWS if item["event_id"] == event_id)


def regulation(uuid_start):
    return next(item for item in REGULATIONS if item["uuid"].startswith(uuid_start))


def feature(gid):
    return next(item for item in LYON if item["properties"]["gid"] == gid)


def event_of(record, city):
    return build_event_from_source(record, classify_source_record(record, city), now=NOW)


def client_for(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


# --- registry -------------------------------------------------------------------


@pytest.mark.parametrize(
    "source_id, city",
    [
        ("nyc-permitted-events", "new-york"),
        ("france-dialog-traffic-orders", "france"),
        ("lyon-disruptive-works", "france"),
    ],
)
def test_new_official_sources_are_tier_one_connected_and_run_by_hand(source_id, city):
    registered = {s.definition.source_id: s for s in registered_sources()}[source_id]
    definition = registered.definition
    assert definition.source_class is SourceClass.GOVERNMENT_OPEN_DATA
    assert definition.source_tier == 1 and definition.discovery_only is False
    assert definition.city == city
    assert definition.integration_status is IntegrationStatus.CONNECTED
    assert definition.active is False and registered.create_connector is not None
    # The licence was read; it is recorded, not taken as a legal review.
    assert definition.terms_status is TermsStatus.PERMITS_TESTING
    assert definition.terms_reviewed is False
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    assert definition.licence and definition.attribution
    scheduled = {s.definition.source_id: s.definition for s in registered_sources(official_feeds_scheduled=True)}
    assert scheduled[source_id].active is True


# --- NYC permitted events --------------------------------------------------------


def test_a_parade_closing_streets_is_a_procession_at_the_places_it_names():
    record = nyc_events.to_record(row("976387"), NOW)
    structured = record.structured
    assert record.title == "Parade: Breakthrough T1D Walk"
    assert structured.event_type == EventType.PUBLIC_PROCESSION.value
    # New York times without an offset: 08:30 EDT is 12:30 UTC.
    assert structured.start == datetime(2026, 10, 17, 12, 30, tzinfo=timezone.utc)
    assert structured.end == datetime(2026, 10, 17, 15, 30, tzinfo=timezone.utc)
    # A place written twice around a colon is kept once.
    assert [location.name for location in structured.locations] == [
        "Thomas Paine Park (Foley Square), Manhattan",
        "Brooklyn Bridge: Brooklyn Bridge Pedestrian: 1 between Park Row (S) and Tillary Street, Manhattan",
        "CENTRE STREET between DUANE STREET and PARK ROW, Manhattan",
    ]
    # The first place is not "STREET between A and B": no road is named.
    assert structured.affected_road is None
    assert structured.geometry is None


def test_a_race_is_a_marathon_and_names_the_street_closed():
    structured = nyc_events.to_record(row("970602"), NOW).structured
    assert structured.event_type == EventType.MARATHON.value
    assert structured.affected_road == "ASTORIA PARK SOUTH"
    assert len(structured.locations) == 3


def test_other_events_closing_a_street_are_special_events():
    for event_id in ("934014", "965106"):
        record = nyc_events.to_record(row(event_id), NOW)
        assert record.structured.event_type == EventType.SPECIAL_EVENT.value


def test_a_closure_of_the_curb_lane_only_is_not_read():
    assert row("910046")["street_closure_type"] == "Sidewalk and Curb Lane Closure"
    assert nyc_events.to_record(row("910046"), NOW) is None


def test_each_day_of_an_event_is_its_own_record():
    first = nyc_events.to_record(row("934014"), NOW)
    next_day = nyc_events.to_record(
        {**row("934014"), "start_date_time": "2026-10-15T08:00:00.000", "end_date_time": "2026-10-15T20:00:00.000"},
        NOW,
    )
    assert first.external_id != next_day.external_id


def test_a_permitted_event_has_no_position_until_a_reviewer_places_it():
    event = event_of(nyc_events.to_record(row("934014"), NOW), NEW_YORK)
    assert event.status.value == "VALIDATION_REQUIRED"
    assert event.geometry is None
    assert event.detection.location_class is LocationClass.UNRESOLVED


def test_the_nyc_events_connector_asks_only_for_full_closures_not_yet_ended():
    seen = []

    def handler(request):
        seen.append(dict(request.url.params))
        return httpx.Response(200, json=NYC_ROWS)

    connector = NycPermittedEventsConnector(
        nyc_events_source(scheduled=False), "ua", client=client_for(handler), clock=lambda: NOW
    )
    records = connector.fetch()
    where = seen[0]["$where"]
    # 16:00 UTC is 12:00 in New York.
    assert "end_date_time >= '2026-10-14T12:00:00'" in where
    assert "'Full Street Closure'" in where and "'Sidewalk and Street Closure'" in where
    # The curb-lane row is dropped; the rest are current or start within a week.
    assert sorted(record.external_id.split(":")[0] for record in records) == ["934014", "965106", "970602", "976387"]
    assert not hasattr(connector, "observed_ids")


# --- DiaLog ----------------------------------------------------------------------


def test_a_closure_order_keeps_its_streets_and_the_lines_of_its_geometry_collection():
    record = dialog.to_record(regulation("019851f7"), NOW)
    structured = record.structured
    assert structured.event_type == EventType.PLANNED_ROAD_CLOSURE.value
    assert structured.start == datetime(2024, 4, 12, 22, 0, tzinfo=timezone.utc)
    assert structured.end == datetime(2026, 10, 30, 23, 0, tzinfo=timezone.utc)
    assert structured.affected_road == "Boulevard Voltaire"
    assert structured.locations[0].name == "Boulevard Voltaire, from Rue de Belfort to Rue de Charonne, Paris"
    # DiaLog's GeometryCollection of lines becomes one MultiLineString of the same lines.
    collection = json.loads(regulation("019851f7")["measures"][0]["locations"][0]["geometry"])
    assert structured.geometry == {
        "type": "MultiLineString",
        "coordinates": [part["coordinates"] for part in collection["geometries"]],
    }
    assert record.title.endswith("(Paris)")
    assert record.summary == (
        "Road closed: Boulevard Voltaire, from Rue de Belfort to Rue de Charonne, Paris. Order by Paris (2024T11570)"
    )


def test_a_numbered_road_is_named_by_its_reference_points():
    record = dialog.to_record(regulation("01a03951"), NOW)
    assert record.structured.affected_road == "D62"
    assert record.structured.locations[0].name == "D62, from PR 22+400 to PR 22+580 (Lozère)"
    # The signed order is linked when the authority attached it.
    assert record.url.startswith("https://dialog.oos.cloudgouv-eu-west-1.outscale.com/regulationOrder/")


def test_an_order_that_only_bans_parking_is_not_a_road_event():
    assert dialog.to_record(regulation("019f190f"), NOW) is None
    assert dialog.to_record(regulation("01a13753"), NOW) is None


def test_a_diversion_and_an_incident_closure_keep_their_kind():
    assert dialog.to_record(regulation("019f651b"), NOW).structured.event_type == EventType.TRAFFIC_DIVERSION.value
    incident = dialog.to_record(regulation("019bd587"), NOW)
    assert incident.structured.event_type == EventType.EMERGENCY_ROAD_CLOSURE.value


def test_a_multipoint_keeps_its_first_point_and_nothing_is_computed():
    multipoint = regulation("01a13753")["measures"][0]["locations"][0]["geometry"]
    assert dialog._geometry(multipoint) == {"type": "Point", "coordinates": [5.552601475, 46.674850254]}


def test_a_traffic_order_is_located_by_its_own_geometry():
    event = event_of(dialog.to_record(regulation("01a03951"), NOW), FRANCE)
    assert event.detection.location_class is LocationClass.SOURCE_PROVIDED
    assert event.geometry.type == "MultiLineString"


def test_the_dialog_connector_reads_every_page_of_current_and_upcoming_orders():
    pages = {
        ("current", "1"): REGULATIONS[:3],
        ("current", "2"): REGULATIONS[3:4],
        ("upcoming", "1"): REGULATIONS[4:] + REGULATIONS[:1],
    }
    seen = []

    def handler(request):
        params = dict(request.url.params)
        seen.append((params["status"], params["page"], params["category"]))
        last = 2 if params["status"] == "current" else 1
        return httpx.Response(
            200,
            json={
                "metadata": {"page": int(params["page"]), "lastPage": last},
                "regulations": pages[(params["status"], params["page"])],
            },
        )

    connector = DialogTrafficOrdersConnector(dialog_source(scheduled=False), "ua", client=client_for(handler), clock=lambda: NOW)
    records = connector.fetch()
    assert seen == [
        ("current", "1", "temporaryRegulation"),
        ("current", "2", "temporaryRegulation"),
        ("upcoming", "1", "temporaryRegulation"),
    ]
    # Parking-only orders are dropped; an order listed twice is kept once.
    assert sorted(record.external_id[:8] for record in records) == ["019851f7", "019bd587", "019f651b", "01a03951"]


# --- Métropole de Lyon -----------------------------------------------------------


def test_a_closed_street_is_a_planned_closure_over_whole_days_in_paris_time():
    record = lyon.to_record(feature(416244), NOW)
    structured = record.structured
    assert record.title == "Circulation interdite: Rue Raoul Servant, Lyon 7e Arrondissement"
    assert structured.event_type == EventType.PLANNED_ROAD_CLOSURE.value
    assert structured.start == datetime(2026, 9, 30, 22, 0, tzinfo=timezone.utc)
    # 30 October is after the clocks go back: 23:59:59 CET.
    assert structured.end == datetime(2026, 10, 30, 22, 59, 59, tzinfo=timezone.utc)
    assert structured.geometry == feature(416244)["geometry"]
    # "Autre" (other) names no contractor.
    assert record.summary == "Travaux voirie"


@pytest.mark.parametrize("gid", [414328, 416338])
def test_reduced_or_alternating_traffic_is_a_lane_restriction(gid):
    assert lyon.to_record(feature(gid), NOW).structured.event_type == EventType.LANE_RESTRICTION.value


def test_a_lyon_work_is_located_by_its_work_site():
    event = event_of(lyon.to_record(feature(416244), NOW), FRANCE)
    assert event.detection.location_class is LocationClass.SOURCE_PROVIDED
    assert event.geometry.type == "MultiPolygon"


def test_the_lyon_connector_reports_every_work_it_lists():
    seen = []

    def handler(request):
        seen.append(dict(request.url.params))
        return httpx.Response(200, json={"type": "FeatureCollection", "features": LYON})

    connector = LyonDisruptiveWorksConnector(lyon_source(scheduled=False), "ua", client=client_for(handler), clock=lambda: NOW)
    records = connector.fetch()
    assert seen[0]["typename"] == "metropole-de-lyon:pvo_patrimoine_voirie.pvochantierperturbant"
    assert len(records) == 3
    assert connector.observed_ids == {"416244", "414328", "416338"}


# --- through the pipeline ------------------------------------------------------


@pytest.fixture
def france_session(session):
    SourceRepository(session).sync_registry([dialog_source(scheduled=False)])
    session.commit()
    return session


def test_traffic_orders_become_events_once_and_are_rebuilt_from_their_evidence(france_session):
    records = [record for item in REGULATIONS if (record := dialog.to_record(item, NOW))]

    def ingest():
        result = run_ingestion(
            FakeConnector(records, source=dialog_source(scheduled=False)),
            KeywordClassifier.for_city(FRANCE),
            SqlIngestionStore(france_session),
            None,
            FRANCE,
        )
        france_session.commit()
        return result

    first = ingest()
    assert (first.new_artifacts, first.events_created) == (4, 4)
    again = ingest()
    assert (again.new_artifacts, again.duplicates, again.events_created) == (0, 4, 0)
    assert {event.status for event in france_session.scalars(select(Event)).unique()} == {"VALIDATION_REQUIRED"}

    artifact = france_session.scalars(
        select(SourceArtifact).where(SourceArtifact.external_id == REGULATIONS[0]["uuid"])
    ).one()
    # The order exactly as DiaLog sent it is the evidence, and rebuilds the same record.
    assert artifact.raw_content["regulation"] == REGULATIONS[0]
    rebuilt = record_from_artifact(artifact)
    original = dialog.to_record(REGULATIONS[0], NOW)
    assert rebuilt.structured == original.structured
    assert rebuilt.summary == original.summary
