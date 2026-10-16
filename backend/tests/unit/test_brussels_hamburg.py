"""Brussels traffic events and Hamburg police traffic messages (decision 0034),
on real responses saved 16 October 2026. No test reaches either service."""

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from app.models import Event
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from connectors.official import brussels, hamburg
from connectors.registry import OFFICIAL_SOURCE_IDS, get_registered_source
from packages.cities import get_city
from packages.event_schema import EventType
from packages.source_models import IntegrationStatus
from services.extraction import KeywordClassifier
from services.ingestion import run_ingestion

FIXTURES = Path(__file__).parents[1] / "fixtures"
BRUSSELS = json.loads((FIXTURES / "brussels_traffic_events_2026-10-16.geojson").read_text(encoding="utf-8"))
HAMBURG = json.loads((FIXTURES / "hamburg_police_traffic_2026-10-16.geojson").read_text(encoding="utf-8"))
NOW = datetime(2026, 10, 16, 12, 30, tzinfo=timezone.utc)


def test_brussels_types_come_from_the_datex_code_and_times_are_brussels_time():
    by_code = {}
    for feature in BRUSSELS["features"]:
        record = brussels.to_record(feature, NOW)
        by_code.setdefault(feature["properties"]["datex_codes"], set()).add(record.structured.event_type)
    assert by_code == {
        "RWK": {EventType.ROAD_WORKS.value},
        "RCA": {EventType.PLANNED_ROAD_CLOSURE.value},
        "BKD": {EventType.ROAD_HAZARD.value},
    }
    first = BRUSSELS["features"][0]
    record = brussels.to_record(first, NOW)
    # "2026-10-16T09:00:00" in Brussels (CEST, UTC+2) is 07:00 UTC.
    assert first["properties"]["start_time"] == "2026-10-16T09:00:00"
    assert record.structured.start == datetime(2026, 10, 16, 7, 0, tzinfo=timezone.utc)
    assert record.structured.geometry == first["geometry"] and record.structured.direction is None


def test_hamburg_takes_works_closures_and_lanes_not_traffic_flow():
    taken = {}
    for feature in HAMBURG["features"]:
        record = hamburg.to_record(feature, NOW)
        key = (feature["properties"]["art"], feature["properties"]["art_detail"])
        taken[key] = record.structured.event_type if record else "not taken"
    assert taken[("ConstructionWorks", "constructionWork")] == EventType.ROAD_WORKS.value
    assert taken[("RoadOrCarriagewayOrLaneManagement", "roadClosed")] == EventType.PLANNED_ROAD_CLOSURE.value
    assert taken[("RoadOrCarriagewayOrLaneManagement", "narrowLanes")] == EventType.LANE_RESTRICTION.value
    for kind in ("AbnormalTraffic", "Conditions", "GeneralInstructionOrMessageToRoadUsers"):
        assert all(value == "not taken" for (art, _), value in taken.items() if art == kind)


def test_hamburg_times_are_utc_as_the_message_text_confirms():
    feature = next(f for f in HAMBURG["features"] if f["properties"].get("end") == "2034-01-31 05:00:00")
    record = hamburg.to_record(feature, NOW) or hamburg.to_record(
        {**feature, "properties": {**feature["properties"], "art": "ConstructionWorks"}}, NOW
    )
    assert record.structured.end == datetime(2034, 1, 31, 5, 0, tzinfo=timezone.utc)
    assert "06:00 Uhr" in feature["properties"]["description"]  # 06:00 Hamburg time = 05:00 UTC


@pytest.mark.parametrize(
    "make, connector_class, document, city_id",
    [
        (brussels.brussels_source, brussels.BrusselsTrafficEventsConnector, BRUSSELS, "brussels"),
        (hamburg.hamburg_source, hamburg.HamburgPoliceTrafficConnector, HAMBURG, "hamburg"),
    ],
)
def test_events_through_the_pipeline_and_registered_run_by_hand(session, make, connector_class, document, city_id):
    source = make(scheduled=True)
    body = json.dumps(document)
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, text=body)))
    connector = connector_class(source, "ua", client=client, clock=lambda: NOW)
    SourceRepository(session).sync_registry([source])
    session.commit()
    result = run_ingestion(connector, KeywordClassifier.from_file(), SqlIngestionStore(session), None, get_city(city_id))
    session.commit()
    events = list(session.scalars(select(Event).where(Event.source_id == source.source_id)))
    assert result.events_created == len(events) > 0
    assert all(e.geometry and e.start_time for e in events)
    registered = get_registered_source(source.source_id)
    assert registered.definition.integration_status is IntegrationStatus.CONNECTED and registered.create_connector
    assert registered.definition.active is False and source.source_id in OFFICIAL_SOURCE_IDS
