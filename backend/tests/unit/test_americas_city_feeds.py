"""US and Canadian city feeds of 21 October 2026: Seattle, Baton Rouge, Halifax,
Cambridge (Ontario), Kitchener and Sherbrooke.

The fixtures are real items each feed returned on 21 October 2026 (a trimmed
sample; the columns naming people are removed), fetched with the connectors'
own queries. Events are built only from what each source states, at the
source's own geometry; every event still needs validation. No test reaches
any service.
"""

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import String, select

from app.models import Event, EventVersion, Source, SourceArtifact
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from connectors.official import baton_rouge, cambridge_on, halifax, kitchener, seattle, sherbrooke
from connectors.official.feed_text import sentences
from packages.cities import get_city
from packages.event_schema import EventType, LocationClass
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass, TermsStatus
from services.extraction import KeywordClassifier, build_event_from_source, classify_source_record
from services.ingestion import run_ingestion
from tests.support import FakeConnector

FIXTURES = Path(__file__).parents[1] / "fixtures"
FEEDS = {
    "seattle-sdot-street-closures": (seattle, seattle.seattle_source, seattle.SeattleStreetClosuresConnector, "united-states"),
    "baton-rouge-road-closures": (baton_rouge, baton_rouge.baton_rouge_source, baton_rouge.BatonRougeRoadClosuresConnector, "united-states"),
    "halifax-street-closures": (halifax, halifax.halifax_source, halifax.HalifaxStreetClosuresConnector, "canada"),
    "cambridge-on-road-closures": (cambridge_on, cambridge_on.cambridge_source, cambridge_on.CambridgeRoadClosuresConnector, "canada"),
    "kitchener-traffic-closures": (kitchener, kitchener.kitchener_source, kitchener.KitchenerTrafficClosuresConnector, "canada"),
    "sherbrooke-travaux": (sherbrooke, sherbrooke.sherbrooke_source, sherbrooke.SherbrookeTravauxConnector, "canada"),
}  # fmt: skip
SOCRATA = {"seattle-sdot-street-closures", "baton-rouge-road-closures"}
# Columns each connector leaves out of the stored evidence (people's names, telephone numbers).
PERSONAL = {
    "baton-rouge-road-closures": baton_rouge.PERSONAL,
    "cambridge-on-road-closures": cambridge_on.PERSONAL,
    "kitchener-traffic-closures": kitchener.PERSONAL,
}


def fixture(source_id):
    name = f"{source_id.replace('-', '_')}_2026-10-21.json"
    body = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return datetime.fromisoformat(body["fetched_at"]), body["items"]


def records(source_id):
    module = FEEDS[source_id][0]
    now, items = fixture(source_id)
    return now, [(item, record) for item in items if (record := module.to_record(item, now))]


def source_geometry(source_id, item):
    """The geometry exactly as the feed gave it."""
    if source_id == "seattle-sdot-street-closures":
        return item["line_string"]
    if source_id == "baton-rouge-road-closures":
        return item["the_geom"]
    return item["geometry"]


def properties(source_id, item):
    return item if source_id in SOCRATA else item["properties"]


# --- the definitions ------------------------------------------------------------------


SOURCE_LIMITS = {
    column.name: column.type.length
    for column in Source.__table__.columns
    if isinstance(column.type, String) and column.type.length
}


@pytest.mark.parametrize("source_id", FEEDS)
def test_each_feed_is_a_connected_tier_one_open_data_source_run_by_hand(source_id):
    _, make, _, city = FEEDS[source_id]
    definition = make(scheduled=False)
    assert definition.source_id == source_id
    assert definition.integration_status is IntegrationStatus.CONNECTED
    assert definition.active is False and make(scheduled=True).active is True
    assert definition.source_tier == 1 and definition.discovery_only is False
    assert definition.source_class is SourceClass.GOVERNMENT_OPEN_DATA
    assert definition.city == city and definition.country == get_city(city).country
    assert definition.provides_geometry is True
    # The licence was read; it is recorded, not taken as a legal review.
    assert definition.terms_status is TermsStatus.PERMITS_TESTING
    assert definition.terms_reviewed is False
    assert definition.licence and definition.attribution
    # Never recorded as settled: no legal review (decision 0009).
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    values = definition.model_dump(mode="json")
    too_long = {
        name: len(str(values[name]))
        for name, limit in SOURCE_LIMITS.items()
        if values.get(name) is not None and len(str(values[name])) > limit
    }
    assert not too_long and len(definition.parser_type) <= 32 and len(source_id) <= 64


# --- every feed -------------------------------------------------------------------------


@pytest.mark.parametrize("source_id", FEEDS)
def test_every_record_keeps_the_source_geometry_and_states_its_times_with_a_zone(source_id):
    _, found = records(source_id)
    assert found
    for item, record in found:
        assert record.source_id == source_id
        assert record.structured.geometry == source_geometry(source_id, item)
        for moment in (record.structured.start, record.structured.end):
            assert moment is None or moment.tzinfo is not None
        assert record.structured.attribution
        assert record.structured.covers_city is True


@pytest.mark.parametrize("source_id", FEEDS)
def test_the_item_is_the_evidence_less_the_columns_naming_people(source_id):
    now, found = records(source_id)
    dropped = PERSONAL.get(source_id, frozenset())
    for item, record in found:
        planted = copy.deepcopy(item)
        for column in dropped:
            properties(source_id, planted)[column] = "A Person 555-0100 (test value)"
        kept = record.raw["item"]
        again = FEEDS[source_id][0].to_record(planted, now).raw["item"]
        assert again == kept
        assert set(properties(source_id, again)) == set(properties(source_id, item)) - dropped
        stated = properties(source_id, item)
        assert all(stated[key] == value for key, value in properties(source_id, kept).items())


@pytest.mark.parametrize("source_id", FEEDS)
def test_every_event_is_located_by_the_source_and_needs_validation(source_id):
    now, found = records(source_id)
    city = get_city(FEEDS[source_id][3])
    for _, record in found:
        event = build_event_from_source(record, classify_source_record(record, city), now=now)
        assert event is not None and event.city == city.name
        assert event.status.value == "VALIDATION_REQUIRED"
        assert event.detection.location_class is LocationClass.SOURCE_PROVIDED
        # REI severity is a reviewer's; the source's words are kept apart.
        assert event.severity is None


@pytest.mark.parametrize("source_id", FEEDS)
def test_external_ids_are_unique_and_stable(source_id):
    now, found = records(source_id)
    ids = [record.external_id for _, record in found]
    assert len(ids) == len(set(ids))
    module = FEEDS[source_id][0]
    later = now + timedelta(hours=6)
    assert [module.to_record(copy.deepcopy(item), later).external_id for item, _ in found] == ids


# --- Seattle --------------------------------------------------------------------------------


def test_seattle_dates_are_whole_seattle_days_and_the_weekday_hours_are_kept_as_text():
    _, found = records("seattle-sdot-street-closures")
    zone = ZoneInfo("America/Los_Angeles")
    for item, record in found:
        assert record.structured.event_type == EventType.SPECIAL_EVENT.value
        first_day = datetime.fromisoformat(item["start_date"][:10])
        assert record.structured.start == first_day.replace(tzinfo=zone)
        end = record.structured.end
        assert end.tzinfo == zone and (end.hour, end.minute) == (23, 59)
        assert end.date().isoformat() == item["end_date"][:10]
    item, record = next((i, r) for i, r in found if i.get("saturday"))
    assert f"Sat {item['saturday']}" in record.summary


def test_two_periods_of_one_seattle_permit_segment_are_two_records():
    _, found = records("seattle-sdot-street-closures")
    pairs = {}
    for item, record in found:
        pairs.setdefault((item["permit_number"], item["segkey"]), []).append(record.external_id)
    assert any(len(set(ids)) == 2 for ids in pairs.values())


# --- Baton Rouge ----------------------------------------------------------------------------


def test_baton_rouge_times_are_utc_as_written():
    _, found = records("baton-rouge-road-closures")
    for item, record in found:
        assert item["start_date"].endswith("Z")
        assert record.structured.start == datetime.fromisoformat(item["start_date"])
        assert record.structured.start.utcoffset() == timedelta(0)
    now, items = fixture("baton-rouge-road-closures")
    unzoned = {**copy.deepcopy(items[0]), "start_date": "2026-10-21T11:00:00.000"}
    assert baton_rouge.to_record(unzoned, now).structured.start is None  # no zone stated: not taken


def test_baton_rouge_closure_kinds_and_only_both_names_the_directions():
    _, found = records("baton-rouge-road-closures")
    kinds = {(i["full_closure"], r.structured.event_type) for i, r in found}
    assert kinds == {
        ("Full", EventType.PLANNED_ROAD_CLOSURE.value),
        ("Partial", EventType.LANE_RESTRICTION.value),
        ("Bridge", EventType.BRIDGE_TUNNEL_RESTRICTION.value),
    }
    for item, record in found:
        expected = "BOTH_DIRECTIONS" if item.get("direction") == "BOTH" else None
        assert record.structured.direction == expected
        assert record.structured.severity == item.get("severity")


def test_baton_rouge_rows_alike_but_for_their_lines_are_two_records():
    _, found = records("baton-rouge-road-closures")
    third = [r for i, r in found if i["street"] == "N. 3rd St"]
    assert len(third) == 2 and third[0].external_id != third[1].external_id


# --- Halifax --------------------------------------------------------------------------------


def test_halifax_dates_are_whole_atlantic_days_and_alternate_dates_stay_text():
    _, found = records("halifax-street-closures")
    zone = ZoneInfo("America/Halifax")
    for item, record in found:
        stated_end = datetime.fromtimestamp(item["properties"]["END_DATE"] / 1000, tz=zone)
        assert record.structured.start.tzinfo == zone and record.structured.start.hour == 0
        assert record.structured.end.date() == stated_end.date()
        assert (record.structured.end.hour, record.structured.end.minute) == (23, 59)
    item, record = next((i, r) for i, r in found if i["properties"].get("ALT_END_DATE"))
    alternate = datetime.fromtimestamp(item["properties"]["ALT_END_DATE"] / 1000, tz=zone).date()
    assert alternate.isoformat() in record.summary and record.structured.end.date() != alternate


def test_halifax_events_are_special_events_and_the_rest_street_closures():
    _, found = records("halifax-street-closures")
    for item, record in found:
        kind = item["properties"]["CLOSURE_TYPE"]
        events = ("Special Event", "Block Party")
        expected = "SPECIAL_EVENT" if kind in events else "PLANNED_ROAD_CLOSURE"
        assert record.structured.event_type == expected
        assert record.structured.status == "Approved"


# --- Cambridge ------------------------------------------------------------------------------


def test_cambridge_parking_lane_closures_are_left_out():
    now, items = fixture("cambridge-on-road-closures")
    parking = [i for i in items if " - Parking Lane - " in (i["properties"].get("DETAILS") or "")]
    assert parking and all(cambridge_on.to_record(item, now) is None for item in parking)
    assert all(not cambridge_on.closes_traffic(item["properties"]) for item in parking)


def test_cambridge_lanes_and_direction_come_from_the_details():
    _, found = records("cambridge-on-road-closures")
    by_details = {i["properties"]["DETAILS"]: r.structured for i, r in found}
    both = by_details["High - All Lanes - Both_Directions"]
    assert both.event_type == EventType.PLANNED_ROAD_CLOSURE.value
    assert both.direction == "BOTH_DIRECTIONS"
    assert by_details["High - All Lanes - Eastbound"].direction == "EASTBOUND"
    assert by_details["Low - One Lane - Northbound"].event_type == EventType.LANE_RESTRICTION.value
    assert by_details["Low - N/A - N/A"].event_type == EventType.ROAD_WORKS.value
    assert by_details["Low - N/A - N/A"].direction is None


def test_cambridge_and_kitchener_times_are_utc_milliseconds():
    for source_id in ("cambridge-on-road-closures", "kitchener-traffic-closures"):
        _, found = records(source_id)
        for item, record in found:
            stated_period = (("DATE_FROM", record.structured.start), ("DATE_TO", record.structured.end))
            for field, moment in stated_period:
                stated = item["properties"][field]
                utc = datetime.fromtimestamp(stated / 1000, tz=timezone.utc) if stated else None
                assert moment == utc


# --- Kitchener ------------------------------------------------------------------------------


def test_a_kitchener_closure_without_dates_states_no_period():
    _, found = records("kitchener-traffic-closures")
    undated = [r for i, r in found if not (i["properties"]["DATE_FROM"] or i["properties"]["DATE_TO"])]
    assert undated and all((r.structured.start, r.structured.end) == (None, None) for r in undated)


def test_kitchener_sidewalk_trail_and_open_closures_are_left_out():
    now, found = records("kitchener-traffic-closures")
    item = found[0][0]
    for change in ({"CLOSURE_TYPE": "Sidewalk"}, {"CLOSURE_TYPE": "Trail"}, {"STATUS": "Open"}):
        variant = copy.deepcopy(item)
        variant["properties"].update(change)
        assert kitchener.to_record(variant, now) is None


def test_kitchener_statuses_give_the_event_type():
    _, found = records("kitchener-traffic-closures")
    expected = {
        "Closed": EventType.PLANNED_ROAD_CLOSURE.value,
        "No Through Traffic": EventType.PLANNED_ROAD_CLOSURE.value,
        "Local Access Only": EventType.PLANNED_ROAD_CLOSURE.value,
        "Partially Closed": EventType.LANE_RESTRICTION.value,
        "Lane Reduced": EventType.LANE_RESTRICTION.value,
        "Tentative": EventType.ROAD_WORKS.value,
        None: EventType.ROAD_WORKS.value,
    }
    for item, record in found:
        p = item["properties"]
        if p["REASON"] == "Special Event":
            assert record.structured.event_type == EventType.SPECIAL_EVENT.value
        else:
            assert record.structured.event_type == expected[p["STATUS"]]


# --- Sherbrooke -----------------------------------------------------------------------------


def test_sherbrooke_works_without_effect_on_road_traffic_are_left_out():
    now, items = fixture("sherbrooke-travaux")
    for item in items:
        stated = item["properties"]["CIRCULATION"]
        record = sherbrooke.to_record(item, now)
        if stated in ("Aucun impact sur la circulation", "Trottoir ou voie cyclable fermé"):
            assert record is None
        else:
            assert record is not None and record.structured.locations[0].closure == stated


def test_sherbrooke_times_are_utc_and_match_the_eastern_time_text():
    _, found = records("sherbrooke-travaux")
    eastern = ZoneInfo("America/Toronto")
    for item, record in found:
        p = item["properties"]
        stated = datetime.strptime(p["DATEDEBUTHE"], "%Y-%m-%d %H:%M").replace(tzinfo=eastern)
        assert record.structured.start == stated
        utc = datetime.fromtimestamp(p["DATE_DEBUT"] / 1000, tz=timezone.utc)
        assert record.structured.start == utc


def test_one_sherbrooke_work_id_at_two_places_is_two_records():
    _, found = records("sherbrooke-travaux")
    twins = [r for i, r in found if i["properties"]["ID"] == 10147]
    assert len(twins) == 2 and twins[0].external_id != twins[1].external_id
    assert {r.structured.event_type for r in twins} == {
        EventType.PLANNED_ROAD_CLOSURE.value,
        EventType.LANE_RESTRICTION.value,
    }


def test_sherbrooke_remarks_lose_their_html_line_breaks():
    _, found = records("sherbrooke-travaux")
    record = next(r for i, r in found if "<br>" in (i["properties"].get("REMARQUE") or ""))
    assert "<br>" not in record.summary


def test_sentences_end_with_one_stop():
    joined = sentences("Detour in place.", "", "Hours: 7AM - 7PM", None)
    assert joined == "Detour in place. Hours: 7AM - 7PM."


# --- fetching -------------------------------------------------------------------------------


@pytest.mark.parametrize("source_id", FEEDS)
def test_the_connector_asks_for_wgs84_and_keeps_what_is_in_effect(source_id):
    _, make, connector_class, _ = FEEDS[source_id]
    now, items = fixture(source_id)
    asked = []

    def handler(request):
        asked.append(request)
        if source_id in SOCRATA:
            return httpx.Response(200, json=items)
        return httpx.Response(200, json={"type": "FeatureCollection", "features": items})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    source = make(scheduled=True)
    connector = connector_class(source, "test-agent", client=client, clock=lambda: now)
    kept = connector.fetch()
    assert len(asked) == 1 and asked[0].headers["User-Agent"] == "test-agent"
    params = dict(asked[0].url.params)
    if source_id in SOCRATA:
        assert params["$limit"] == "5000"
    else:
        assert asked[0].url.path.endswith("/query")
        assert params["outSR"] == "4326" and params["f"] == "geojson" and params["outFields"] == "*"
    _, found = records(source_id)
    assert connector.observed_ids == {record.external_id for _, record in found}
    assert kept and all(r.structured.end is None or r.structured.end >= now for r in kept)


def test_halifax_and_seattle_ask_only_for_closures_not_yet_ended():
    asked = {}
    for source_id in ("halifax-street-closures", "seattle-sdot-street-closures"):
        _, make, connector_class, _ = FEEDS[source_id]
        now, _ = fixture(source_id)

        def handler(request, source_id=source_id):
            asked[source_id] = dict(request.url.params)
            body = [] if source_id in SOCRATA else {"type": "FeatureCollection", "features": []}
            return httpx.Response(200, json=body)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        source = make(scheduled=False)
        connector_class(source, "ua", client=client, clock=lambda now=now: now).fetch()
    # 21 October 2026, 11:05 UTC: 08:05 in Halifax, 04:05 in Seattle.
    assert asked["halifax-street-closures"]["where"] == "END_DATE >= DATE '2026-10-20'"
    assert asked["seattle-sdot-street-closures"]["$where"] == "end_date >= '2026-10-21'"


# --- into the database -----------------------------------------------------------------------


def test_events_are_stored_once_and_every_value_fits_its_column(session):
    definitions = [make(scheduled=False) for _, make, _, _ in FEEDS.values()]
    SourceRepository(session).sync_registry(definitions)
    session.commit()
    created = {}
    for definition in definitions:
        _, found = records(definition.source_id)
        city = get_city(FEEDS[definition.source_id][3])

        def ingest(found=found, definition=definition, city=city):
            result = run_ingestion(
                FakeConnector([record for _, record in found], source=definition),
                KeywordClassifier.for_city(city), SqlIngestionStore(session), None, city,
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
