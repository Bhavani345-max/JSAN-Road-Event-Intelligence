"""US WZDx work-zone feeds (decision 0034), on real responses saved 16 October 2026.

No test reaches a feed: each fixture is served to the connector.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from connectors.official.wzdx import FEEDS, connector_for, source_id_for, to_record_for, wzdx_source
from connectors.registry import OFFICIAL_SOURCE_IDS, registered_sources
from packages.cities import get_city
from packages.event_schema import EventType
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass
from services.ingestion.pipeline import classify

FIXTURES = Path(__file__).parents[1] / "fixtures"
FEED = {feed.key: feed for feed in FEEDS}
# A moment when the Delaware work zones of the saved response were in effect.
NOW = datetime(2026, 10, 16, 13, 0, tzinfo=timezone.utc)


def records(key: str, fixture: str, now: datetime = NOW):
    body = (FIXTURES / fixture).read_text(encoding="utf-8")
    feed = FEED[key]
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, text=body)))
    connector = connector_for(feed)(wzdx_source(feed, scheduled=True), "ua", client=client, clock=lambda: now)
    return connector.fetch(), connector


def test_every_work_zone_has_its_own_geometry_dates_and_the_feeds_words():
    found, connector = records("deldot", "wzdx_deldot_2026-10-16.geojson")
    assert len(connector.observed_ids) == 19
    assert found and all(r.structured.geometry and r.structured.start and r.structured.end for r in found)
    first = next(r for r in found if r.external_id == "1af6784b-0fe8-4fff-8243-112eee78e631")
    assert first.title == "Road works: Broom Street SB (one direction) southbound (Delaware)"
    assert first.structured.start == datetime(2026, 10, 16, 12, 5, 44, tzinfo=timezone.utc)
    assert first.structured.direction == "SOUTHBOUND"
    assert "(not verified)" in first.structured.stated_period or "(verified)" in first.structured.stated_period
    assert first.raw["item"]["id"] == first.external_id  # the feature itself is the evidence


def test_what_a_work_zone_does_to_traffic_decides_its_type():
    found, _ = records("deldot", "wzdx_deldot_2026-10-16.geojson")
    by_impact = {}
    for record in found:
        by_impact.setdefault(record.raw["item"]["properties"].get("vehicle_impact"), set()).add(record.structured.event_type)
    assert by_impact.get("all-lanes-closed", {EventType.PLANNED_ROAD_CLOSURE.value}) == {EventType.PLANNED_ROAD_CLOSURE.value}
    assert by_impact.get("unknown", {EventType.ROAD_WORKS.value}) == {EventType.ROAD_WORKS.value}
    for impact in ("some-lanes-closed", "alternating-one-way", "flagging"):
        assert by_impact.get(impact, {EventType.LANE_RESTRICTION.value}) == {EventType.LANE_RESTRICTION.value}


def test_a_multipoint_keeps_its_first_point_and_a_detour_is_not_an_event():
    sample = json.loads((FIXTURES / "wzdx_indot_sample_2026-10-16.geojson").read_text(encoding="utf-8"))
    read = to_record_for(FEED["indot"])
    by_id = {f["id"]: (f, read(f, NOW)) for f in sample["features"]}
    kinds = {f["properties"]["core_details"]["event_type"] for f, _ in by_id.values()}
    assert kinds == {"work-zone", "detour"}
    for feature, record in by_id.values():
        if feature["properties"]["core_details"]["event_type"] == "detour":
            assert record is None  # where traffic is sent is not the event
        elif feature["geometry"]["type"] == "MultiPoint":
            assert record.structured.geometry == {"type": "Point", "coordinates": feature["geometry"]["coordinates"][0]}
        if feature["properties"].get("vehicle_impact") == "all-lanes-closed":
            assert record.structured.event_type == EventType.PLANNED_ROAD_CLOSURE.value


def test_a_work_zone_in_the_country_is_an_official_source_event():
    found, _ = records("deldot", "wzdx_deldot_2026-10-16.geojson")
    city = get_city("united-states")
    assert {classify(r, None, city).label.value for r in found} == {"SOURCE_PROVIDED_EVENT"}


@pytest.mark.parametrize("feed", FEEDS, ids=lambda feed: feed.key)
def test_each_feed_is_a_connected_official_feed_run_by_hand_unless_scheduled(feed):
    registered = {s.definition.source_id: s for s in registered_sources()}[source_id_for(feed)]
    definition = registered.definition
    assert definition.integration_status is IntegrationStatus.CONNECTED and registered.create_connector
    # Like every official feed: not polled unless OFFICIAL_FEEDS_SCHEDULED(_SOURCES) names it.
    assert definition.active is False and definition.source_id in OFFICIAL_SOURCE_IDS
    assert definition.source_class is SourceClass.GOVERNMENT_OPEN_DATA and definition.source_tier == 1
    # CC0, yet recorded with attribution: REI claims no unconditional rights without legal review.
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION and "CC0" in definition.licence
    assert definition.city == "united-states" and definition.provides_geometry
    scheduled = {s.definition.source_id: s for s in registered_sources(official_feeds_scheduled_sources=[definition.source_id])}
    assert scheduled[definition.source_id].definition.active is True


def test_work_zones_become_events_through_the_pipeline(session):
    # The whole way: evidence stored, an event per work zone, with its direction.
    from sqlalchemy import select

    from app.models import Event
    from app.repositories.ingestion_store import SqlIngestionStore
    from app.repositories.sources import SourceRepository
    from services.extraction import KeywordClassifier
    from services.ingestion import run_ingestion

    feed = FEED["deldot"]
    body = (FIXTURES / "wzdx_deldot_2026-10-16.geojson").read_text(encoding="utf-8")
    source = wzdx_source(feed, scheduled=True)
    connector = connector_for(feed)(
        source, "ua", client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, text=body))),
        clock=lambda: NOW,
    )  # fmt: skip
    SourceRepository(session).sync_registry([source])
    session.commit()
    result = run_ingestion(connector, KeywordClassifier.from_file(), SqlIngestionStore(session), None, get_city("united-states"))
    session.commit()
    events = list(session.scalars(select(Event).where(Event.source_id == source.source_id)))
    assert result.events_created == len(events) == result.new_artifacts > 0
    assert all(e.geometry and e.start_time and e.end_time and e.city == "United States" for e in events)
    assert {e.direction for e in events} <= {"NORTHBOUND", "SOUTHBOUND", "EASTBOUND", "WESTBOUND", "BOTH_DIRECTIONS", None}


def test_a_feed_sent_as_a_json_string_is_read_the_same():
    # New Jersey's feed (16 October 2026) wraps the document in a JSON string.
    document = (FIXTURES / "wzdx_deldot_2026-10-16.geojson").read_text(encoding="utf-8")
    body = json.dumps(document)
    feed = FEED["deldot"]
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, text=body)))
    connector = connector_for(feed)(wzdx_source(feed, scheduled=True), "ua", client=client, clock=lambda: NOW)
    assert len(connector.fetch()) == len(records("deldot", "wzdx_deldot_2026-10-16.geojson")[0])


def test_a_geometry_with_a_bbox_member_keeps_its_shape():
    # Maryland's and North Dakota's features (16 October 2026) carry GeoJSON's
    # optional "bbox" member; the shape must not be thrown away for it.
    from services.extraction.source_event import _geometry

    line = {"type": "LineString", "coordinates": [[-76.562305, 38.778233], [-76.5701, 38.77701]],
            "bbox": [-76.5701, 38.77701, -76.562305, 38.778233]}  # fmt: skip
    geometry = _geometry(line)
    assert geometry is not None and geometry.type == "LineString"
    assert [list(p) for p in geometry.coordinates] == line["coordinates"]


def test_a_position_with_an_altitude_keeps_longitude_and_latitude():
    # North Dakota's features (16 October 2026) give positions as [lon, lat, 0.0].
    from services.extraction.source_event import _geometry

    line = {"type": "LineString", "coordinates": [[-97.619901, 48.411486, 0.0], [-97.620318, 48.41186, 0.0]]}
    geometry = _geometry(line)
    assert geometry is not None
    assert [list(p) for p in geometry.coordinates] == [[-97.619901, 48.411486], [-97.620318, 48.41186]]
