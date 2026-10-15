"""Canada and Australia (decision 0029): nine official feeds connected on 15 October 2026.

The fixtures are real items each feed returned on 15 October 2026 (a sample
of each, unchanged), fetched with the connectors' own fetch functions. Events
are built only from what the source states, at the source's own geometry;
every event still needs validation.
"""

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import select

from app.models import Event
from app.repositories.events import EventRepository
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from connectors.base import ConnectorError
from connectors.official import (
    calgary,
    drivebc,
    edmonton,
    gold_coast,
    main_roads_wa,
    ottawa,
    roads_act,
    winnipeg,
    wodonga,
)
from connectors.official.feature_feed import fetch_arcgis_features, fetch_socrata_rows
from connectors.registry import OFFICIAL_SOURCE_IDS, registered_sources
from packages.cities import get_city, load_cities
from packages.event_schema import LocationClass
from packages.source_models import CommercialUse, IntegrationStatus, TermsStatus
from services.extraction import KeywordClassifier, build_event_from_source, classify_source_record
from services.ingestion import run_ingestion
from services.lifecycle.current import EventListView
from tests.support import FakeConnector

FIXTURES = Path(__file__).parents[1] / "fixtures"
MODULES = {
    "drivebc-events": (drivebc, "canada"),
    "ottawa-traffic-events": (ottawa, "canada"),
    "edmonton-traffic-disruptions": (edmonton, "canada"),
    "winnipeg-lane-closures": (winnipeg, "canada"),
    "calgary-construction-detours": (calgary, "canada"),
    "main-roads-wa-webeoc": (main_roads_wa, "australia"),
    "gold-coast-temporary-road-closures": (gold_coast, "australia"),
    "roads-act-planned-closures": (roads_act, "australia"),
    "wodonga-roadworks": (wodonga, "australia"),
}


def fixture(source_id):
    body = json.loads((FIXTURES / f"{source_id.replace('-', '_')}_2026-10-15.json").read_text(encoding="utf-8"))
    return datetime.fromisoformat(body["fetched_at"]), body["items"]


def records(source_id):
    module, _ = MODULES[source_id]
    now, items = fixture(source_id)
    return now, [(item, record) for item in items if (record := module.to_record(item, now))]


def source_geometry(source_id, item):
    """The geometry exactly as the feed gave it."""
    if source_id == "drivebc-events":
        return item["geography"]
    if source_id in ("edmonton-traffic-disruptions",):
        return item["rows"][0]["point"]
    if source_id in ("winnipeg-lane-closures",):
        return item["geometry"]
    if source_id == "calgary-construction-detours":
        return item["point"]
    if source_id == "main-roads-wa-webeoc":
        return item["feature"]["geometry"]
    if source_id == "wodonga-roadworks":
        return item["works"]["geometry"]
    return item["geometry"]


# --- the registry -------------------------------------------------------------------


@pytest.mark.parametrize("source_id", MODULES)
def test_each_feed_is_an_official_located_source_run_by_hand(source_id):
    registered = {s.definition.source_id: s for s in registered_sources()}[source_id]
    definition = registered.definition
    _, city = MODULES[source_id]
    assert definition.city == city and definition.country == get_city(city).country
    assert definition.source_tier == 1 and definition.discovery_only is False
    assert definition.integration_status is IntegrationStatus.CONNECTED
    assert definition.active is False and registered.create_connector is not None
    assert definition.provides_geometry is True
    # The licence was read; it is recorded, not taken as a legal review.
    assert definition.terms_status is TermsStatus.PERMITS_TESTING and definition.terms_reviewed is False
    assert definition.licence and definition.attribution
    assert source_id in OFFICIAL_SOURCE_IDS


def test_roads_act_share_alike_licence_is_left_for_the_user():
    definition = roads_act.roads_act_source(scheduled=False)
    assert "ShareAlike" in definition.licence
    assert definition.commercial_use is CommercialUse.UNKNOWN
    assert "user's decision" in definition.notes


def test_canada_australia_and_south_africa_are_configured():
    cities = load_cities()
    assert (cities["canada"].country, cities["australia"].country, cities["south-africa"].country) == (
        "CA", "AU", "ZA",
    )  # fmt: skip
    registered = {s.definition.source_id for s in registered_sources()}
    for city in ("canada", "australia"):
        assert set(cities[city].source_time_zones) <= registered
        assert set(cities[city].official_sources) <= registered
    # South Africa has no source that passes the checks yet (docs/data-sources/south-africa-...).
    assert cities["south-africa"].official_sources == ()
    assert cities["canada"].source_time_zones["drivebc-events"] == "America/Vancouver"
    assert cities["australia"].source_time_zones["main-roads-wa-webeoc"] == "Australia/Perth"


# --- every feed ---------------------------------------------------------------------


@pytest.mark.parametrize("source_id", MODULES)
def test_every_record_keeps_the_source_geometry_and_states_its_times_with_a_zone(source_id):
    _, found = records(source_id)
    assert found
    for item, record in found:
        assert record.structured.geometry == source_geometry(source_id, item)
        for moment in (record.structured.start, record.structured.end):
            assert moment is None or moment.tzinfo is not None
        assert record.structured.attribution
        # The item itself is the evidence (less columns repeating others: Winnipeg's
        # KML copy of the geometry, Socrata's computed region codes).
        kept = record.raw["item"]
        assert all(item[key] == value for key, value in kept.items())
        assert set(item) - set(kept) <= {"kml"} | {k for k in item if k.startswith(":@computed")}


@pytest.mark.parametrize("source_id", MODULES)
def test_every_event_is_located_by_the_source_and_needs_validation(source_id):
    now, found = records(source_id)
    _, city = MODULES[source_id]
    for _, record in found:
        event = build_event_from_source(record, classify_source_record(record, get_city(city)), now=now)
        assert event is not None
        assert event.status.value == "VALIDATION_REQUIRED"
        assert event.detection.location_class is LocationClass.SOURCE_PROVIDED
        assert event.severity is None  # REI severity is a reviewer's; the source's words are kept apart


# --- DriveBC --------------------------------------------------------------------------


def test_drivebc_times_are_utc_as_written_and_an_open_interval_has_no_end():
    _, found = records("drivebc-events")
    item, record = next((i, r) for i, r in found if i["schedule"]["intervals"][0].split("/")[1])
    start, end = item["schedule"]["intervals"][0].split("/")
    assert record.structured.start == datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
    assert record.structured.end == datetime.fromisoformat(end).replace(tzinfo=timezone.utc)
    open_item = next((i for i, _ in found if not i["schedule"]["intervals"][0].split("/")[1]), None)
    if open_item is not None:
        assert drivebc.to_record(open_item, datetime.now(timezone.utc)).structured.end is None


def test_drivebc_rest_area_and_washroom_closures_are_not_road_events():
    now, items = fixture("drivebc-events")
    facility = [i for i in items if i["description"].lower().startswith(drivebc.NOT_ROAD_EVENTS)]
    assert facility and all(drivebc.to_record(item, now) is None for item in facility)


def test_a_closed_drivebc_road_is_a_closure():
    _, found = records("drivebc-events")
    closed = [(i, r) for i, r in found if any(road.get("state") == "CLOSED" for road in i.get("roads", []))]
    assert closed
    for item, record in closed:
        assert record.structured.event_type in ("PLANNED_ROAD_CLOSURE", "EMERGENCY_ROAD_CLOSURE")


# --- Ottawa -----------------------------------------------------------------------------


def test_ottawa_times_are_local_ottawa_time():
    _, found = records("ottawa-traffic-events")
    item, record = next((i, r) for i, r in found if i["properties"].get("schedule"))
    stated = item["properties"]["schedule"][0]["startDateTime"]
    assert record.structured.start == datetime.fromisoformat(stated).replace(tzinfo=ZoneInfo("America/Toronto"))


def test_an_ottawa_event_without_a_schedule_states_no_period():
    now, items = fixture("ottawa-traffic-events")
    unscheduled = [i for i in items if not i["properties"].get("schedule")]
    for item in unscheduled:
        record = ottawa.to_record(item, now)
        assert (record.structured.start, record.structured.end) == (None, None)


# --- Edmonton ---------------------------------------------------------------------------


def test_an_edmonton_disruption_listed_at_both_ends_is_one_event_with_both_points():
    _, found = records("edmonton-traffic-disruptions")
    item, record = next((i, r) for i, r in found if len(i["rows"]) == 2)
    assert record.external_id == item["disruption_id"]
    assert [place.geometry for place in record.structured.locations] == [row["point"] for row in item["rows"]]
    assert [place.kind for place in record.structured.locations] == ["from point", "to point"]


def test_edmonton_dates_are_whole_local_days():
    _, found = records("edmonton-traffic-disruptions")
    item, record = next((i, r) for i, r in found if i["rows"][0].get("finish_date"))
    zone = ZoneInfo("America/Edmonton")
    assert record.structured.start.tzinfo == zone and record.structured.start.hour == 0
    assert (record.structured.end.hour, record.structured.end.minute) == (23, 59)
    assert record.structured.end.date().isoformat() == item["rows"][0]["finish_date"][:10]


# --- Winnipeg ---------------------------------------------------------------------------


def test_winnipeg_placeholder_end_of_2099_is_no_stated_end():
    now, found = records("winnipeg-lane-closures")
    item = copy.deepcopy(found[0][0])
    item["date_closed_to"] = "2099-01-01T00:00:00.000"
    assert winnipeg.to_record(item, now).structured.end is None


def test_winnipeg_closure_of_one_day_from_midnight_to_midnight_is_that_whole_day():
    now, found = records("winnipeg-lane-closures")
    item = copy.deepcopy(found[0][0])
    item.update(
        date_closed_from="2026-10-25T00:00:00.000", date_closed_to="2026-10-25T00:00:00.000",
        time_closed_from="12:00 AM", time_closed_to="12:00 AM",
    )  # fmt: skip
    start, end = winnipeg.period(item)
    zone = ZoneInfo("America/Winnipeg")
    assert start == datetime(2026, 10, 25, 0, 0, tzinfo=zone)
    assert end == datetime(2026, 10, 25, 23, 59, 59, tzinfo=zone)


def test_winnipeg_sidewalk_parking_and_loading_closures_are_left_out():
    now, items = fixture("winnipeg-lane-closures")
    left_out = [item for item in items if winnipeg.to_record(item, now) is None]
    assert left_out
    for item in left_out:
        assert not winnipeg.closes_traffic(item)
        assert "lane" not in item.get("traffic_effect", "").lower()


# --- Calgary ----------------------------------------------------------------------------


def test_calgary_records_keep_their_key_when_the_table_is_rebuilt():
    now, found = records("calgary-construction-detours")
    item, record = found[0]
    rebuilt = {**copy.deepcopy(item), ":id": "row-new-after-refresh"}
    assert calgary.to_record(rebuilt, now + timedelta(hours=12)).external_id == record.external_id


def test_calgary_times_are_local_calgary_time():
    _, found = records("calgary-construction-detours")
    item, record = found[0]
    assert record.structured.start == datetime.fromisoformat(item["start_dt"]).replace(
        tzinfo=ZoneInfo("America/Edmonton")
    )


# --- Main Roads WA ----------------------------------------------------------------------


def test_main_roads_wa_times_are_western_australian_time():
    _, found = records("main-roads-wa-webeoc")
    item, record = next((i, r) for i, r in found if i["layer"] == "roadworks")
    stated = datetime.strptime(item["feature"]["properties"]["DateStarte"], "%d/%m/%Y %H:%M:%S")
    assert record.structured.start == stated.replace(tzinfo=ZoneInfo("Australia/Perth"))


def test_main_roads_wa_events_are_sporting_or_special_events():
    _, found = records("main-roads-wa-webeoc")
    events = [r for i, r in found if i["layer"] == "event"]
    assert events and {r.structured.event_type for r in events} <= {"SPORTING_EVENT", "SPECIAL_EVENT"}


# --- Gold Coast -------------------------------------------------------------------------


def test_gold_coast_footpath_and_parking_lane_closures_are_left_out():
    now, items = fixture("gold-coast-temporary-road-closures")
    for item in items:
        extent = (item["properties"].get("CLOSURE_EXTENT") or "").upper()
        if extent in gold_coast.NOT_TRAFFIC:
            assert gold_coast.to_record(item, now) is None


def test_gold_coast_street_and_permit_put_back_when_swapped():
    now, found = records("gold-coast-temporary-road-closures")
    item = copy.deepcopy(found[0][0])
    item["properties"].update(STREET="TRCI/2025/745", TRC_ID="CHRISTENSEN ROAD SOUTH")
    record = gold_coast.to_record(item, now)
    assert record.structured.affected_road == "Christensen Road South"
    assert "Permit TRCI/2025/745" in record.summary


def test_gold_coast_dates_are_whole_days_in_queensland():
    _, found = records("gold-coast-temporary-road-closures")
    _, record = next((i, r) for i, r in found if r.structured.end)
    assert record.structured.start.tzinfo == ZoneInfo("Australia/Brisbane")
    assert (record.structured.end.hour, record.structured.end.minute) == (23, 59)


# --- Roads ACT --------------------------------------------------------------------------


def test_only_plans_roads_act_approved_are_read():
    now, found = records("roads-act-planned-closures")
    item = copy.deepcopy(found[0][0])
    item["properties"]["roadsDelegateClosure"] = "no"
    assert roads_act.to_record(item, now) is None


def test_roads_act_times_are_utc_milliseconds():
    _, found = records("roads-act-planned-closures")
    item, record = found[0]
    stated = item["properties"]["startTimeClosure"]
    assert record.structured.start == datetime.fromtimestamp(stated / 1000, tz=timezone.utc)


# --- Wodonga ----------------------------------------------------------------------------


def test_wodonga_works_carry_their_closures_and_a_detour_is_named_not_drawn():
    _, found = records("wodonga-roadworks")
    item, record = next((i, r) for i, r in found if i["children"])
    kinds = [place.kind for place in record.structured.locations]
    assert kinds[0] == "impact area"
    assert set(kinds[1:]) <= {"closure", "disruption", "detour"}
    for place in record.structured.locations:
        if place.kind == "detour":
            assert place.geometry is None


# --- fetching ---------------------------------------------------------------------------


def client_for(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_arcgis_features_are_read_page_by_page_until_the_last():
    pages = [
        {"type": "FeatureCollection", "features": [{"type": "Feature", "id": n} for n in range(1000)],
         "properties": {"exceededTransferLimit": True}},
        {"type": "FeatureCollection", "features": [{"type": "Feature", "id": 1000}]},
    ]  # fmt: skip
    asked = []

    def handler(request):
        asked.append(dict(request.url.params))
        return httpx.Response(200, json=pages[len(asked) - 1])

    features = fetch_arcgis_features("https://example.test/layer/0", "test", client=client_for(handler))
    assert len(features) == 1001
    assert [a["resultOffset"] for a in asked] == ["0", "1000"]
    assert all(a["outSR"] == "4326" and a["f"] == "geojson" for a in asked)


def test_an_arcgis_error_answer_is_a_failed_run_not_an_empty_feed():
    client = client_for(lambda request: httpx.Response(200, json={"error": {"code": 400, "message": "Invalid"}}))
    with pytest.raises(ConnectorError):
        fetch_arcgis_features("https://example.test/layer/0", "test", client=client)


def test_a_socrata_answer_as_long_as_the_limit_is_reported_as_cut():
    client = client_for(lambda request: httpx.Response(200, json=[{"n": n} for n in range(10)]))
    with pytest.raises(ConnectorError):
        fetch_socrata_rows("https://example.test/resource/x.json", "test", client=client, limit=10)


# --- into the database and the console's views ------------------------------------------


@pytest.fixture
def canada_session(session):
    SourceRepository(session).sync_registry([ottawa.ottawa_source(scheduled=False)])
    session.commit()
    return session


def test_ottawa_events_are_stored_once_and_the_dated_ones_reach_the_review_queue(canada_session):
    now, found = records("ottawa-traffic-events")
    source = ottawa.ottawa_source(scheduled=False)

    def ingest():
        result = run_ingestion(
            FakeConnector([record for _, record in found], source=source),
            KeywordClassifier.for_city(get_city("canada")),
            SqlIngestionStore(canada_session),
            None,
            get_city("canada"),
        )
        canada_session.commit()
        return result

    first = ingest()
    assert first.events_created == len(found)
    assert ingest().events_created == 0
    rows = canada_session.scalars(select(Event)).unique().all()
    assert {row.status for row in rows} == {"VALIDATION_REQUIRED"} and {row.city for row in rows} == {"Canada"}
    shown, total = EventRepository(canada_session).list(view=EventListView.VALIDATION, limit=500, now=now)
    dated = [r for _, r in found if r.structured.start and r.structured.end and r.structured.end >= now]
    assert total == len(dated)


def test_calgary_rows_of_one_closure_are_each_kept_and_merged_into_one_event(session):
    """The City lists one closure per direction: two rows, same place, point and period."""
    from app.services import merge_service

    now, found = records("calgary-construction-detours")
    first = copy.deepcopy(found[0][0])
    second = {**copy.deepcopy(first), "description": "Southbound right lane closed (test variant of a real row)"}
    source = calgary.calgary_source(scheduled=False)
    rows = [calgary.to_record(first, now), calgary.to_record(second, now)]
    assert rows[0].external_id != rows[1].external_id  # each row is its own evidence
    SourceRepository(session).sync_registry([source])
    session.commit()
    run_ingestion(
        FakeConnector(rows, source=source), KeywordClassifier.for_city(get_city("canada")),
        SqlIngestionStore(session), None, get_city("canada"),
    )  # fmt: skip
    session.commit()
    merged = merge_service.merge_listed_rows(session, source.source_id)
    session.commit()
    assert merged.auto_merged == 1
    events = session.scalars(select(Event)).unique().all()
    assert len(events) == 2 and sum(1 for event in events if event.merged_into is None) == 1


def test_rows_identical_to_a_reader_become_one_event_and_different_ones_stay_apart(session):
    """Ottawa listed one nightly closure twice under two ids on 15 October 2026."""
    from app.services import merge_service

    now, found = records("ottawa-traffic-events")
    item = copy.deepcopy(found[0][0])
    twin = copy.deepcopy(item)
    twin["properties"]["id"] = "test-twin-of-a-real-row"
    other = copy.deepcopy(item)
    other["properties"]["id"] = "test-other-street"
    other["properties"]["headline"] = "A different street at the same spot (test)"
    source = ottawa.ottawa_source(scheduled=False)
    rows = [ottawa.to_record(feature, now) for feature in (item, twin, other)]
    SourceRepository(session).sync_registry([source])
    session.commit()
    run_ingestion(
        FakeConnector(rows, source=source), KeywordClassifier.for_city(get_city("canada")),
        SqlIngestionStore(session), None, get_city("canada"),
    )  # fmt: skip
    session.commit()
    merged = merge_service.merge_listed_rows(session, source.source_id)
    session.commit()
    assert merged.auto_merged == 1
    listed = [event for event in session.scalars(select(Event)).unique() if event.merged_into is None]
    assert sorted(event.title for event in listed) == sorted({rows[0].title, rows[2].title})
