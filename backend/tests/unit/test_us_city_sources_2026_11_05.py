"""US city feeds of 5 November 2026: DDOT construction permits (Washington, DC),
Louisville Metro right-of-way construction permits and City of Cambridge
(Massachusetts) excavation permits.

The fixtures are real items each feed returned on 5 November 2026 (a trimmed
sample), fetched with the connectors' own queries; the columns naming people
and the free text naming staff hold placeholders. Events are built only from
what each source states, at the source's own point; every event still needs
validation. No test reaches any service.
"""

import copy
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import String, select

from app.models import Event, EventVersion, Source, SourceArtifact
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from connectors.official import cambridge_ma_excavations, dc_ddot_permits, louisville_row_permits
from packages.cities import get_city
from packages.event_schema import EventType, LocationClass
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass, TermsStatus
from services.extraction import KeywordClassifier, build_event_from_source, classify_source_record
from services.ingestion import run_ingestion
from tests.support import FakeConnector

FIXTURES = Path(__file__).parents[1] / "fixtures"
DC = "dc-ddot-construction-permits"
LOUISVILLE = "louisville-row-construction-permits"
CAMBRIDGE = "us-cambridge-ma-street-excavations"
FEEDS = {
    DC: (dc_ddot_permits, dc_ddot_permits.dc_ddot_source, dc_ddot_permits.DcDdotConstructionPermitsConnector, "dc_ddot_construction_permits_2026-11-05.json"),
    LOUISVILLE: (louisville_row_permits, louisville_row_permits.louisville_source, louisville_row_permits.LouisvilleRowConstructionPermitsConnector, "louisville_row_construction_permits_2026-11-05.json"),
    CAMBRIDGE: (cambridge_ma_excavations, cambridge_ma_excavations.cambridge_ma_source, cambridge_ma_excavations.CambridgeMaStreetExcavationsConnector, "cambridge_ma_street_excavations_2026-11-05.json"),
}  # fmt: skip
SOCRATA = {CAMBRIDGE}
# Columns each connector leaves out of the stored evidence: people, free text naming staff, row ids.
LEFT_OUT = {
    DC: dc_ddot_permits.PERSONAL | dc_ddot_permits.FREE_TEXT | dc_ddot_permits.ROW_NUMBERS,
    LOUISVILLE: louisville_row_permits.PERSONAL | louisville_row_permits.FREE_TEXT | {"ObjectId"},
}
PLANTED = "A Person, a.person@example.org, 555-0100 (test value)"
UNITED_STATES = get_city("united-states")


def fixture(source_id):
    body = json.loads((FIXTURES / FEEDS[source_id][3]).read_text(encoding="utf-8"))
    return datetime.fromisoformat(body["fetched_at"]), body["items"]


def records(source_id):
    module = FEEDS[source_id][0]
    now, items = fixture(source_id)
    return now, [(item, record) for item in items if (record := module.to_record(item, now))]


def stated(source_id, item):
    return item if source_id in SOCRATA else item["properties"]


def source_geometry(source_id, item):
    return item["coordinates"] if source_id == CAMBRIDGE else item["geometry"]


# --- the definitions ------------------------------------------------------------------


SOURCE_LIMITS = {
    column.name: column.type.length
    for column in Source.__table__.columns
    if isinstance(column.type, String) and column.type.length
}


@pytest.mark.parametrize("source_id", FEEDS)
def test_each_feed_is_a_connected_tier_one_open_data_source_run_by_hand(source_id):
    make = FEEDS[source_id][1]
    definition = make(scheduled=False)
    assert definition.source_id == source_id == FEEDS[source_id][0].SOURCE_ID
    assert definition.integration_status is IntegrationStatus.CONNECTED
    assert definition.active is False and make(scheduled=True).active is True
    assert definition.source_tier == 1 and definition.discovery_only is False
    assert definition.source_class is SourceClass.GOVERNMENT_OPEN_DATA
    assert definition.city == "united-states" and definition.country == "US"
    assert definition.region and definition.language == "en"
    assert definition.polling_frequency_minutes and definition.polling_frequency_minutes >= 60
    assert definition.provides_geometry is True
    # The licence was read; it is recorded, not taken as a legal review.
    assert definition.terms_status is TermsStatus.PERMITS_TESTING
    assert definition.terms_reviewed is False
    assert definition.licence and definition.attribution
    # Never recorded as settled: no legal review (decision 0009).
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    assert definition.evidence_retention and "5 November 2026" in definition.notes
    values = definition.model_dump(mode="json")
    too_long = {
        name: len(str(values[name]))
        for name, limit in SOURCE_LIMITS.items()
        if values.get(name) is not None and len(str(values[name])) > limit
    }
    assert not too_long and len(definition.parser_type) <= 32 and len(source_id) <= 64


# --- every feed -------------------------------------------------------------------------


@pytest.mark.parametrize("source_id", FEEDS)
def test_every_record_keeps_the_source_point_and_states_whole_local_days(source_id):
    _, found = records(source_id)
    assert found
    for item, record in found:
        assert record.source_id == source_id
        assert record.structured.geometry == source_geometry(source_id, item)
        assert record.structured.geometry["type"] == "Point"
        start, end = record.structured.start, record.structured.end
        assert start.tzinfo is not None and end.tzinfo is not None
        assert (start.hour, start.minute) == (0, 0) and (end.hour, end.minute) == (23, 59)
        assert record.structured.attribution and record.structured.covers_city is True


@pytest.mark.parametrize("source_id", LEFT_OUT)
def test_the_item_is_the_evidence_less_people_staff_free_text_and_row_ids(source_id):
    now, found = records(source_id)
    dropped = LEFT_OUT[source_id]
    for item, record in found:
        planted = copy.deepcopy(item)
        for column in dropped:
            planted["properties"][column] = PLANTED
        again = FEEDS[source_id][0].to_record(planted, now)
        assert again.raw["item"] == record.raw["item"]
        assert PLANTED not in json.dumps(again.raw) and PLANTED not in (again.summary or "")
        kept = record.raw["item"]["properties"]
        assert set(kept) == set(item["properties"]) - dropped
        assert all(item["properties"][key] == value for key, value in kept.items())
        assert "id" not in record.raw["item"]  # the feature id is the row number


@pytest.mark.parametrize("source_id", FEEDS)
def test_every_event_is_located_by_the_source_and_needs_validation(source_id):
    now, found = records(source_id)
    for _, record in found:
        event = build_event_from_source(record, classify_source_record(record, UNITED_STATES), now=now)
        assert event is not None and event.city == UNITED_STATES.name
        assert event.status.value == "VALIDATION_REQUIRED"
        assert event.detection.location_class is LocationClass.SOURCE_PROVIDED
        assert event.severity is None


@pytest.mark.parametrize("source_id", FEEDS)
def test_external_ids_are_the_permit_numbers_unique_and_stable(source_id):
    now, found = records(source_id)
    ids = [record.external_id for _, record in found]
    assert len(ids) == len(set(ids))
    module = FEEDS[source_id][0]
    later = now + timedelta(hours=6)
    assert [module.to_record(copy.deepcopy(item), later).external_id for item, _ in found] == ids


# --- Washington, DC ---------------------------------------------------------------------------


def test_dc_keeps_issued_permits_that_excavate_or_pave_and_leaves_out_the_rest():
    now, items = fixture(DC)
    by_permit = {item["properties"]["PERMITNUMBER"]: item for item in items}
    for permit in ("PA493244", "PA497740", "PA501256", "PA498566"):  # fixture, landscaping, projections, no work
        assert dc_ddot_permits.to_record(by_permit[permit], now) is None
    kept = {r.external_id: r for item in items if (r := dc_ddot_permits.to_record(item, now))}
    assert set(kept) == set(by_permit) - {"PA493244", "PA497740", "PA501256", "PA498566"}
    assert {r.structured.event_type for r in kept.values()} == {EventType.ROAD_WORKS.value}
    assert kept["PA484849"].structured.category == "Construction permit / Excavation / Paving / Fixture / Landscaping / Projections"
    assert "PA459935-R1" in kept  # a revised permit is its own record
    approved = copy.deepcopy(by_permit["PA489229"])
    approved["properties"]["STATUS"] = "Approved (Pending Payment)"
    assert dc_ddot_permits.to_record(approved, now) is None


def test_a_dc_address_the_geocoder_could_not_match_is_unlocated_and_left_out():
    now, items = fixture(DC)
    unmatched = copy.deepcopy(items[0])
    unmatched["properties"].update({"XCOORD": 0, "YCOORD": 0})
    assert dc_ddot_permits.to_record(unmatched, now) is None
    unmatched = copy.deepcopy(items[0])
    unmatched["geometry"] = {"type": "Point", "coordinates": [0, 0]}
    assert dc_ddot_permits.to_record(unmatched, now) is None


def test_dc_days_are_washington_days_and_the_title_is_the_address():
    now, found = records(DC)
    zone = ZoneInfo("America/New_York")
    for item, record in found:
        p = item["properties"]
        first = datetime.fromtimestamp(p["EFFECTIVEDATE"] / 1000, tz=zone)
        last = datetime.fromtimestamp(p["EXPIRATIONDATE"] / 1000, tz=zone)
        assert record.structured.start == first and record.structured.end.date() == last.date()
        assert record.title == f"Road works: {p['WLFULLADDRESS']} (Washington, DC)"
        assert "work detail" not in json.dumps(record.raw).lower()


def test_dc_asks_for_issued_permits_not_expired_and_follows_the_second_page():
    now, items = fixture(DC)
    asked = []

    def handler(request):
        asked.append(request)
        offset = int(request.url.params["resultOffset"])
        if offset == 0:  # the server's first page is marked as cut
            body = {"type": "FeatureCollection", "features": items[:10], "exceededTransferLimit": True,
                    "properties": {"exceededTransferLimit": True}}  # fmt: skip
        else:
            body = {"type": "FeatureCollection", "features": items[10:]}
        return httpx.Response(200, json=body)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    connector = dc_ddot_permits.DcDdotConstructionPermitsConnector(
        dc_ddot_permits.dc_ddot_source(scheduled=True), "test-agent", client=client, clock=lambda: now
    )
    kept = connector.fetch()
    assert [request.url.params["resultOffset"] for request in asked] == ["0", "1000"]
    params = dict(asked[0].url.params)
    assert params["where"] == "STATUS = 'Issued' AND EXPIRATIONDATE >= DATE '2026-11-04'"
    assert params["outSR"] == "4326" and params["f"] == "geojson" and params["resultRecordCount"] == "1000"
    assert asked[0].headers["User-Agent"] == "test-agent"
    _, found = records(DC)
    assert connector.observed_ids == {record.external_id for _, record in found}
    # PA488782 starts on 1 January 2028, beyond the run window.
    assert {r.external_id for r in kept} == connector.observed_ids - {"PA488782"}


def test_a_dc_permit_ended_by_the_run_clock_is_dropped():
    now, items = fixture(DC)
    later = datetime(2026, 11, 13, 17, 0, tzinfo=ZoneInfo("UTC"))  # PA459935-R1 ended on 12 November
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"type": "FeatureCollection", "features": items}))
    )
    connector = dc_ddot_permits.DcDdotConstructionPermitsConnector(
        dc_ddot_permits.dc_ddot_source(scheduled=False), "ua", client=client, clock=lambda: later
    )
    kept = connector.fetch()
    assert "PA459935-R1" not in {r.external_id for r in kept} and "PA489229" in {r.external_id for r in kept}
    assert all(r.structured.end >= later for r in kept)


# --- Louisville -------------------------------------------------------------------------------


def test_louisville_work_types_give_the_event_type_and_the_title():
    _, found = records(LOUISVILLE)
    for item, record in found:
        kinds = {kind.upper() for kind in louisville_row_permits.work_types(item["properties"])}
        if "ROAD CLOSURE" in kinds:
            expected, label = EventType.PLANNED_ROAD_CLOSURE.value, "Road closure"
        elif "LANE CLOSURE" in kinds:
            expected, label = EventType.LANE_RESTRICTION.value, "Lane closure"
        else:
            expected, label = EventType.ROAD_WORKS.value, "Road works"
        assert record.structured.event_type == expected
        p = item["properties"]
        assert record.title == f"{label}: {p['STREET_ADDRESS']} ({p['CITY']}, KY)"
    types = {record.structured.event_type for _, record in found}
    assert types == {EventType.PLANNED_ROAD_CLOSURE.value, EventType.LANE_RESTRICTION.value, EventType.ROAD_WORKS.value}
    both = next(r for i, r in found if i["properties"]["PERMIT_NO"] == "PW-REP-26-00910")  # lane and road closure
    assert both.structured.event_type == EventType.PLANNED_ROAD_CLOSURE.value
    assert both.structured.locations[0].closure == "Road Closure"


def test_louisville_days_are_louisville_days():
    _, found = records(LOUISVILLE)
    zone = ZoneInfo("America/Kentucky/Louisville")
    for item, record in found:
        p = item["properties"]
        assert record.structured.start == datetime.fromtimestamp(p["FROM_DATE"] / 1000, tz=zone)
        assert record.structured.end.date() == datetime.fromtimestamp(p["TO_DATE"] / 1000, tz=zone).date()


def test_louisville_fetch_keeps_what_is_in_effect_or_coming_and_drops_the_ended():
    now, items = fixture(LOUISVILLE)
    asked = []

    def handler(request):
        asked.append(request)
        return httpx.Response(200, json={"type": "FeatureCollection", "features": items})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    connector = louisville_row_permits.LouisvilleRowConstructionPermitsConnector(
        louisville_row_permits.louisville_source(scheduled=True), "test-agent", client=client, clock=lambda: now
    )
    kept = {r.external_id for r in connector.fetch()}
    assert len(asked) == 1 and asked[0].url.path.endswith("/FeatureServer/0/query")
    assert dict(asked[0].url.params)["orderByFields"] == "ObjectId"
    ended = {"PW-REP-26-03405", "PW-REP-26-03427", "PW-REP-26-03421"}  # ended 2 and 4 November
    coming = {"PW-REP-26-03479", "PW-REP-26-03503", "PW-REP-26-03514"}  # start 6 and 7 November
    assert not kept & ended and coming <= kept
    assert kept == connector.observed_ids - ended


# --- Cambridge, Massachusetts -------------------------------------------------------------------


def test_cambridge_titles_use_the_permit_type_not_street_excavation():
    _, found = records(CAMBRIDGE)
    for item, record in found:
        assert record.title.startswith(item["permit_type"])
        assert "street excavation" not in record.title.lower()
        assert record.structured.event_type == EventType.ROAD_WORKS.value
    sidewalk = next(r for i, r in found if i["cutting_the_street_and_or"] == "Yes - Sidewalk")
    assert sidewalk.title == "Excavation: 330 Mt Auburn St, Cambridge, MA 02138"  # utility "Other": not named
    assert "Other utility work: Power feed from utility manhole" in sidewalk.summary
    gas = next(r for i, r in found if i["id"] == "1234746")
    assert gas.title == "Excavation (Eversource Gas): 468 Massachusetts Ave, Cambridge, MA 02139"


def test_cambridge_days_are_cambridge_days_and_only_active_roadway_permits_are_kept():
    now, found = records(CAMBRIDGE)
    zone = ZoneInfo("America/New_York")
    for item, record in found:
        assert record.structured.start == datetime.fromisoformat(item["start_date"]).replace(tzinfo=zone)
        assert record.structured.end.date().isoformat() == item["end_date"][:10]
        assert record.raw["item"] == item  # the selected columns only
    item = found[0][0]
    for change in ({"status": "Complete"}, {"public_roadway": False}, {"coordinates": None, "latitude": "0", "longitude": "0"}):
        assert cambridge_ma_excavations.to_record({**item, **change}, now) is None
    without_point = {key: value for key, value in item.items() if key != "coordinates"}
    assert cambridge_ma_excavations.to_record(without_point, now).structured.geometry == item["coordinates"]


def test_cambridge_asks_only_for_the_columns_it_keeps_and_for_permits_not_ended():
    now, items = fixture(CAMBRIDGE)
    asked = []

    def handler(request):
        asked.append(request)
        return httpx.Response(200, json=items)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    connector = cambridge_ma_excavations.CambridgeMaStreetExcavationsConnector(
        cambridge_ma_excavations.cambridge_ma_source(scheduled=True), "test-agent", client=client, clock=lambda: now
    )
    kept = connector.fetch()
    params = dict(asked[0].url.params)
    assert len(asked) == 1 and params["$limit"] == "5000"
    assert params["$where"] == "status='Active' AND public_roadway=true AND end_date>='2026-11-05'"
    columns = params["$select"].split(",")
    assert columns == list(cambridge_ma_excavations.COLUMNS)
    assert not {"applicant_name", "contractor", "company_name", "hoisting_license"} & set(columns)
    assert len(kept) == len(items)
    later = datetime(2026, 11, 12, 12, 0, tzinfo=ZoneInfo("UTC"))  # 1232936 (10 Nov) and 1186909 (11 Nov) have ended
    connector = cambridge_ma_excavations.CambridgeMaStreetExcavationsConnector(
        cambridge_ma_excavations.cambridge_ma_source(scheduled=False), "ua", client=client, clock=lambda: later
    )
    kept = {r.external_id for r in connector.fetch()}
    assert not {"1232936", "1186909"} & kept and len(kept) == len(items) - 2


# --- into the database --------------------------------------------------------------------------


def test_events_are_stored_once_and_every_value_fits_its_column(session):
    definitions = [make(scheduled=False) for _, make, _, _ in FEEDS.values()]
    SourceRepository(session).sync_registry(definitions)
    session.commit()
    created = {}
    for definition in definitions:
        _, found = records(definition.source_id)

        def ingest(found=found, definition=definition):
            result = run_ingestion(
                FakeConnector([record for _, record in found], source=definition),
                KeywordClassifier.for_city(UNITED_STATES), SqlIngestionStore(session), None, UNITED_STATES,
            )  # fmt: skip
            session.commit()
            return result

        created[definition.source_id] = (ingest().events_created, len(found))
        assert ingest().events_created == 0
    assert all(made == expected for made, expected in created.values()), created
    rows = session.scalars(select(Event).where(Event.source_id.in_(FEEDS))).unique().all()
    assert rows and {row.status for row in rows} == {"VALIDATION_REQUIRED"}
    assert all(row.geometry is not None for row in rows)
    too_long = []
    for model in (Event, SourceArtifact, EventVersion):
        limits = {
            column.name: column.type.length
            for column in model.__table__.columns
            if isinstance(column.type, String) and column.type.length
        }
        for row in session.scalars(select(model)).unique():
            for name, limit in limits.items():
                value = getattr(row, name)
                if value is not None and len(str(value)) > limit:
                    too_long.append((model.__tablename__, name, len(str(value)), limit))
    assert not too_long, too_long[:10]
