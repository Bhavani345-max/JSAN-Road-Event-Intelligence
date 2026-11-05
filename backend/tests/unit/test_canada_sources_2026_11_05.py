"""Canadian city and regional feeds approved on 5 November 2026: Ville de Québec
(WZDx 3.1), Longueuil, Saguenay, the Region of Waterloo and Burlington.

The fixtures are real items each feed returned on 5 November 2026 (trimmed
samples, except Saguenay's whole file; columns naming people replaced by a
placeholder), fetched with the connectors' own queries. Events are built only
from what each source states, at the source's own geometry; every event still
needs validation. No test reaches any service.
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
from connectors.base import ConnectorError
from connectors.official import (
    burlington,
    cambridge_on,
    kitchener,
    longueuil,
    quebec_city_entraves,
    saguenay,
    waterloo_region,
)
from packages.cities import get_city
from packages.event_schema import EventType, LocationClass
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass, TermsStatus
from services.extraction import KeywordClassifier, build_event_from_source, classify_source_record
from services.ingestion import run_ingestion
from tests.support import FakeConnector

FIXTURES = Path(__file__).parents[1] / "fixtures"
EASTERN = ZoneInfo("America/Toronto")
FEEDS = {
    "ca-quebec-city-entraves-wzdx": (quebec_city_entraves, quebec_city_entraves.quebec_city_source, quebec_city_entraves.QuebecCityEntravesConnector, "quebec_city_entraves_wzdx"),
    "ca-longueuil-entraves": (longueuil, longueuil.longueuil_source, longueuil.LongueuilEntravesConnector, "longueuil_entraves"),
    "ca-saguenay-chantiers-511": (saguenay, saguenay.saguenay_source, saguenay.SaguenayChantiersConnector, "saguenay_chantiers_511"),
    "ca-waterloo-region-road-closures": (waterloo_region, waterloo_region.waterloo_region_source, waterloo_region.WaterlooRegionRoadClosuresConnector, "region_of_waterloo_road_closures"),
    "ca-burlington-road-closures": (burlington, burlington.burlington_source, burlington.BurlingtonRoadClosuresConnector, "burlington_road_closures"),
}  # fmt: skip
# Columns each connector leaves out of the stored evidence (people's names, e-mail, telephone).
PERSONAL = {
    "ca-waterloo-region-road-closures": waterloo_region.PERSONAL,
    "ca-burlington-road-closures": burlington.PERSONAL,
}
PLACEHOLDER = "A Person - person@example.invalid - 555-0100 (placeholder)"


def body(source_id):
    name = f"{FEEDS[source_id][3]}_2026-11-05.json"
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def longueuil_names():
    return longueuil.domain_names(body("ca-longueuil-entraves")["domains"])


def fixture(source_id):
    """The fixture's fetch time and the items the connector reads, as its fetch gives them."""
    data = body(source_id)
    now = datetime.fromisoformat(data["fetched_at"])
    if source_id == "ca-longueuil-entraves":
        names = longueuil_names()
        return now, [longueuil.labelled(item, names) for item in data["items"]]
    if source_id == "ca-waterloo-region-road-closures":
        return now, data["current"] + data["future"]
    return now, data["items"]


def records(source_id):
    module = FEEDS[source_id][0]
    now, items = fixture(source_id)
    return now, [(item, record) for item in items if (record := module.to_record(item, now))]


def by_id(source_id, external_id):
    _, found = records(source_id)
    return next(record for _, record in found if record.external_id == external_id)


def feature_collection(features, **extra):
    return {"type": "FeatureCollection", **extra, "features": features}


def serve(source_id):
    """A handler answering each request the connector makes with the fixture's items."""
    data = body(source_id)
    asked = []

    def handler(request):
        asked.append(request)
        path = str(request.url.copy_with(query=None))
        if source_id == "ca-quebec-city-entraves-wzdx":
            info = data["road_event_feed_info"]
            return httpx.Response(200, json=feature_collection(data["items"], road_event_feed_info=info))
        if source_id == "ca-longueuil-entraves":
            if path == longueuil.LAYER:
                fields = [{"name": name, "domain": domain} for name, domain in data["domains"].items()]
                return httpx.Response(200, json={"name": "Gestion des entraves - Localisation", "fields": fields})
            return httpx.Response(200, json=feature_collection(data["items"]))
        if source_id == "ca-waterloo-region-road-closures":
            layers = {
                f"{waterloo_region.CURRENT_LAYER}/query": data["current"],
                f"{waterloo_region.FUTURE_LAYER}/query": data["future"],
                f"{kitchener.LAYER}/query": data["kitchener"],
                f"{cambridge_on.LAYER}/query": data["cambridge"],
            }
            return httpx.Response(200, json=feature_collection(layers[path]))
        return httpx.Response(200, json=feature_collection(data["items"]))

    return handler, asked


def connector_for(source_id, now, handler):
    _, make, connector_class, _ = FEEDS[source_id]
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return connector_class(make(scheduled=True), "test-agent", client=client, clock=lambda: now)


# --- the definitions ------------------------------------------------------------------


SOURCE_LIMITS = {
    column.name: column.type.length
    for column in Source.__table__.columns
    if isinstance(column.type, String) and column.type.length
}


@pytest.mark.parametrize("source_id", FEEDS)
def test_each_feed_is_a_connected_tier_one_open_data_source_run_by_hand(source_id):
    module, make, _, _ = FEEDS[source_id]
    definition = make(scheduled=False)
    assert definition.source_id == source_id == module.SOURCE_ID
    assert definition.integration_status is IntegrationStatus.CONNECTED
    assert definition.active is False and make(scheduled=True).active is True
    assert definition.source_tier == 1 and definition.discovery_only is False
    assert definition.source_class is SourceClass.GOVERNMENT_OPEN_DATA
    assert definition.city == "canada" and definition.country == "CA"
    assert definition.region and definition.language in ("en", "fr")
    assert definition.polling_frequency_minutes and definition.provides_geometry is True
    # The licence was read; it is recorded, not taken as a legal review.
    assert definition.terms_status is TermsStatus.PERMITS_TESTING
    assert definition.terms_reviewed is False
    assert definition.licence and definition.attribution
    assert definition.evidence_retention and "5 November 2026" in definition.notes
    # Never recorded as settled: no legal review (decision 0009).
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    values = definition.model_dump(mode="json")
    too_long = {
        name: len(str(values[name]))
        for name, limit in SOURCE_LIMITS.items()
        if values.get(name) is not None and len(str(values[name])) > limit
    }
    assert not too_long and len(definition.parser_type) <= 32 and len(source_id) <= 64


def test_the_licences_are_the_ones_read_on_5_november():
    assert "CC BY 4.0" in quebec_city_entraves.quebec_city_source(scheduled=False).licence
    assert "CC BY 4.0" in longueuil.longueuil_source(scheduled=False).licence
    assert "CC BY 4.0" in saguenay.saguenay_source(scheduled=False).licence
    assert "CC BY 4.0" in burlington.burlington_source(scheduled=False).licence
    region = waterloo_region.waterloo_region_source(scheduled=False)
    assert region.licence.startswith("Region of Waterloo Open Data Licence v.2.0")
    assert region.attribution == (
        "Contains information provided by the Regional Municipality of Waterloo under licence."
    )


# --- every feed -------------------------------------------------------------------------


@pytest.mark.parametrize("source_id", FEEDS)
def test_every_record_keeps_the_source_geometry_and_states_its_times_with_a_zone(source_id):
    _, found = records(source_id)
    assert found
    for item, record in found:
        assert record.source_id == source_id
        assert record.structured.geometry == item["geometry"]
        assert record.structured.geometry["type"] in (
            "Point", "LineString", "MultiLineString"
        )  # fmt: skip
        for moment in (record.structured.start, record.structured.end):
            assert moment is None or moment.tzinfo is not None
        assert record.structured.attribution
        assert record.structured.covers_city is True
        assert record.structured.event_type in {kind.value for kind in EventType}


@pytest.mark.parametrize("source_id", FEEDS)
def test_the_item_is_the_evidence_less_the_columns_naming_people(source_id):
    now, found = records(source_id)
    dropped = PERSONAL.get(source_id, frozenset())
    for item, record in found:
        planted = copy.deepcopy(item)
        for column in dropped:
            planted["properties"][column] = "A Person 555-0100 (test value)"
        kept = record.raw["item"]
        again = FEEDS[source_id][0].to_record(planted, now).raw["item"]
        assert again == kept
        assert set(again["properties"]) == set(item["properties"]) - dropped
        assert all(item["properties"][key] == value for key, value in kept["properties"].items())
        assert PLACEHOLDER not in json.dumps(record.raw, ensure_ascii=False)
        assert "example.invalid" not in (record.summary or "") + record.title


@pytest.mark.parametrize("source_id", FEEDS)
def test_every_event_is_located_by_the_source_and_needs_validation(source_id):
    now, found = records(source_id)
    city = get_city("canada")
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


# --- Ville de Québec (WZDx 3.1) --------------------------------------------------------------


def test_quebec_detours_and_work_zones_with_all_lanes_open_are_left_out():
    now, items = fixture("ca-quebec-city-entraves-wzdx")
    for item in items:
        properties = item["properties"]
        record = quebec_city_entraves.to_record(item, now)
        if properties["event_type"] == "detour" or properties["vehicle_impact"] == "all-lanes-open":
            assert record is None
        else:
            assert record is not None
    # The detour without geometry is among them; nothing is drawn for it.
    assert any(item.get("geometry") is None for item in items)


def test_quebec_vehicle_impact_gives_the_event_type_and_the_direction_is_the_feeds():
    _, found = records("ca-quebec-city-entraves-wzdx")
    expected = {
        "all-lanes-closed": EventType.PLANNED_ROAD_CLOSURE.value,
        "some-lanes-closed": EventType.LANE_RESTRICTION.value,
        "alternating-one-way": EventType.LANE_RESTRICTION.value,
    }
    compass = {word: f"{word.upper()}" for word in ("northbound", "southbound", "eastbound", "westbound")}
    assert {item["properties"]["vehicle_impact"] for item, _ in found} == set(expected)
    for item, record in found:
        properties = item["properties"]
        assert record.structured.event_type == expected[properties["vehicle_impact"]]
        assert record.structured.direction == compass[properties["direction"]]
        assert record.structured.status == properties["event_status"]
        roads = properties.get("road_names") or [None]
        assert record.structured.affected_road == roads[0]
        assert properties["description"] in record.summary
        assert record.title.endswith("(Québec)")


def test_quebec_times_are_utc_as_written_and_their_accuracy_is_kept():
    _, found = records("ca-quebec-city-entraves-wzdx")
    for item, record in found:
        properties = item["properties"]
        assert properties["start_date"].endswith("Z")
        assert record.structured.start == datetime.fromisoformat(properties["start_date"])
        assert record.structured.start.utcoffset() == timedelta(0)
        assert record.structured.end == datetime.fromisoformat(properties["end_date"])
        assert "(estimated)" in record.structured.stated_period
    now, items = fixture("ca-quebec-city-entraves-wzdx")
    unzoned = copy.deepcopy(next(i for i in items if i["properties"]["event_type"] == "work-zone"))
    unzoned["properties"]["start_date"] = "2026-11-11T13:00:00"
    assert quebec_city_entraves.to_record(unzoned, now).structured.start is None  # no zone: not taken


def test_one_quebec_id_on_two_streets_is_two_records():
    _, found = records("ca-quebec-city-entraves-wzdx")
    twins = [r for i, r in found if i["id"] == "ACL-20261022-SPA-01"]
    assert len(twins) == 2
    assert {r.external_id for r in twins} == {
        "ACL-20261022-SPA-01|Rue Arago O",
        "ACL-20261022-SPA-01|Rue St-Germain",
    }
    # The two directions of one works are two features with two ids.
    pair = {r.external_id for i, r in found if i["id"].startswith("ARIV-20261026-EC-001")}
    assert pair == {"ARIV-20261026-EC-001|Rue Jean-Clément", "ARIV-20261026-EC-001_1|Rue Jean-Clément"}


def test_quebec_completed_or_cancelled_events_are_reported_ended():
    now, found = records("ca-quebec-city-entraves-wzdx")
    item = copy.deepcopy(found[0][0])
    for status, ended in (("completed", True), ("cancelled", True), ("active", False)):
        item["properties"]["event_status"] = status
        assert quebec_city_entraves.to_record(item, now).structured.reported_ended is ended


def test_quebec_feed_in_another_wzdx_version_is_refused():
    data = body("ca-quebec-city-entraves-wzdx")
    info = {**data["road_event_feed_info"], "version": "4.2"}
    answer = feature_collection(data["items"], road_event_feed_info=info)
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=answer)))
    with pytest.raises(ConnectorError, match="WZDx version 4.2"):
        quebec_city_entraves.fetch_features("ua", client=client)


# --- Longueuil -----------------------------------------------------------------------------


def test_longueuil_coded_values_are_named_from_the_layers_domains():
    names = longueuil_names()
    assert names["TYPE_ENTRAVE"][4] == "Voies de circulation et trottoirs"
    assert names["TYPE_ENTRAVE"][5] == "Événements spéciaux"
    assert names["STATUT_ENTRAVE"][3] == "Entraves proposées (non publiée)"
    assert names["DEBUT_PREVU"][13] == "Printemps"
    _, items = fixture("ca-longueuil-entraves")
    for item in items:
        properties, labels = item["properties"], item["labels"]
        assert labels["TYPE_ENTRAVE"] == names["TYPE_ENTRAVE"][properties["TYPE_ENTRAVE"]]
        assert labels["STATUT_ENTRAVE"] == names["STATUT_ENTRAVE"][properties["STATUT_ENTRAVE"]]
    record = by_id("ca-longueuil-entraves", "{B69447F2-9386-498D-9D65-FBFE7E7A154E}")
    assert record.structured.status == "Entraves en cours"
    assert record.structured.category.startswith("Voies de circulation et trottoirs / Fermeture_Complete")
    assert "Responsable : Ville de Longueuil" in record.summary


def test_longueuil_keeps_published_road_and_event_obstructions_with_an_effect_on_traffic():
    now, items = fixture("ca-longueuil-entraves")
    kept, left_out = set(), set()
    for item in items:
        record = longueuil.to_record(item, now)
        (kept if record else left_out).add(item["properties"]["OBJECTID"])
    # Roads and sidewalks (4), published, with a closure or a diverted or alternating flow.
    assert {2249, 7364, 8001, 7684, 13, 2250, 12162, 2566, 8649, 3209} <= kept
    # Finished obstructions and the half marathon (a special event) are kept, reported ended.
    assert {8646, 8644, 11533} <= kept
    assert 14 in left_out  # status 3, proposed (not published)
    assert {2889, 12165} <= left_out  # "Aucune"; parking and sidewalks only
    assert {12174, 321} <= left_out  # filming (6); a park (1)
    assert kept | left_out == {item["properties"]["OBJECTID"] for item in items}


def test_longueuil_event_types_come_from_the_category_and_the_effects():
    _, found = records("ca-longueuil-entraves")
    for item, record in found:
        properties = item["properties"]
        stated = properties["REPERCUSSIONS_ENTRAVE"].split(",")
        if properties["TYPE_ENTRAVE"] == 5:
            expected = EventType.SPECIAL_EVENT.value
        elif "Fermeture_Complete" in stated:
            expected = EventType.PLANNED_ROAD_CLOSURE.value
        else:
            expected = EventType.LANE_RESTRICTION.value
        assert record.structured.event_type == expected
        assert record.structured.reported_ended is (properties["STATUT_ENTRAVE"] == 0)
    event = by_id("ca-longueuil-entraves", "{E28720E7-F7E8-4BDA-9634-62AC194DE852}")
    assert event.structured.event_type == EventType.SPECIAL_EVENT.value


def test_longueuil_dates_are_whole_eastern_days():
    _, found = records("ca-longueuil-entraves")
    dated = [(i, r) for i, r in found if i["properties"]["DATE_DEBUT"] and i["properties"]["DATE_FIN"]]
    assert dated
    for item, record in dated:
        properties = item["properties"]
        # Stated at local noon: the day is the noon's day in Eastern time.
        noon = datetime.fromtimestamp(properties["DATE_DEBUT"] / 1000, tz=EASTERN)
        assert noon.hour == 12
        assert record.structured.start == datetime.combine(noon.date(), datetime.min.time(), tzinfo=EASTERN)
        last = datetime.fromtimestamp(properties["DATE_FIN"] / 1000, tz=EASTERN).date()
        assert record.structured.end.date() == last and record.structured.end.tzinfo == EASTERN
        assert (record.structured.end.hour, record.structured.end.minute) == (23, 59)
    record = by_id("ca-longueuil-entraves", "{B69447F2-9386-498D-9D65-FBFE7E7A154E}")
    assert record.structured.stated_period == "du 2026-06-01 au 2026-11-30 (début prévu juin, fin prévue novembre)"


def test_longueuil_obstructions_planned_for_a_month_only_keep_no_times():
    _, found = records("ca-longueuil-entraves")
    undated = [(i, r) for i, r in found if not (i["properties"]["DATE_DEBUT"] or i["properties"]["DATE_FIN"])]
    assert undated
    for _, record in undated:
        assert (record.structured.start, record.structured.end) == (None, None)
    spring = by_id("ca-longueuil-entraves", "{92090BB7-1D75-433A-9970-B4486F44D548}")
    assert spring.structured.stated_period == "début prévu printemps, fin prévue automne"
    # Only one of the two days stated: the other stays unstated.
    only_end = by_id("ca-longueuil-entraves", "{6B00251C-FBDE-453C-BFFD-436E42244650}")
    assert only_end.structured.start is None and only_end.structured.end is not None


def test_longueuil_fetch_reads_the_domains_once_and_names_each_point():
    now, _ = fixture("ca-longueuil-entraves")
    handler, asked = serve("ca-longueuil-entraves")
    client = httpx.Client(transport=httpx.MockTransport(handler))
    items = longueuil.fetch_obstructions("ua", client=client, now=now)
    assert [str(r.url.copy_with(query=None)) for r in asked] == [longueuil.LAYER, f"{longueuil.LAYER}/query"]
    assert dict(asked[0].url.params) == {"f": "json"}
    assert items and all(item["labels"]["TYPE_ENTRAVE"] for item in items)
    # A layer that no longer names its categories is not guessed at.
    bare = {"fields": [{"name": "OBJECTID"}]}
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=bare)))
    with pytest.raises(ConnectorError, match="no longer names"):
        longueuil.fetch_obstructions("ua", client=client)


# --- Saguenay ------------------------------------------------------------------------------


def test_saguenay_times_are_eastern_local_times_and_an_empty_end_stays_unstated():
    _, found = records("ca-saguenay-chantiers-511")
    assert len(found) == 20
    for item, record in found:
        properties = item["properties"]
        start = datetime.fromisoformat(properties["date_debut"]).replace(tzinfo=EASTERN)
        assert record.structured.start == start and record.structured.start.tzinfo == EASTERN
        if properties["date_fin"]:
            assert record.structured.end == datetime.fromisoformat(properties["date_fin"]).replace(tzinfo=EASTERN)
        else:
            assert record.structured.end is None
    # Fractions of a second as the file writes them.
    route = by_id("ca-saguenay-chantiers-511", "35311")
    assert route.structured.start == datetime(2026, 10, 19, 8, 32, 51, 880000, tzinfo=EASTERN)


def test_saguenay_effect_and_kind_give_the_event_type():
    _, found = records("ca-saguenay-chantiers-511")
    for item, record in found:
        state, kind = item["properties"]["etat"], item["properties"]["type"]
        if state in ("Fermeture complète", "Circulation locale"):
            expected = (
                EventType.EMERGENCY_ROAD_CLOSURE.value
                if kind == "Travaux d'urgence"
                else EventType.PLANNED_ROAD_CLOSURE.value
            )
        else:
            expected = EventType.LANE_RESTRICTION.value
        assert record.structured.event_type == expected
        assert record.structured.locations[0].closure == state
        assert record.title.startswith(f"{state}: ")
    assert by_id("ca-saguenay-chantiers-511", "35141").title == (
        "Fermeture complète: Chemin Saint-Wilbrod, Jonquière (Saguenay)"
    )


def test_two_saguenay_worksites_at_one_place_are_two_records():
    _, found = records("ca-saguenay-chantiers-511")
    wilbrod = [r for i, r in found if i["properties"]["localisation"] == "Chemin Saint-Wilbrod"]
    assert {r.external_id for r in wilbrod} == {"35141", "35142"}


# --- Region of Waterloo -------------------------------------------------------------------


def test_waterloo_no_closure_and_sidewalk_closures_are_left_out():
    now, items = fixture("ca-waterloo-region-road-closures")
    for item in items:
        properties = item["properties"]
        record = waterloo_region.to_record(item, now)
        if properties["STATUS"] == "No Closure" or properties["CLOSURE_TYPE"] == "Sidewalk":
            assert record is None
        else:
            assert record is not None
    variant = copy.deepcopy(next(i for i in items if i["properties"]["STATUS"] == "Closed"))
    variant["properties"]["CLOSURE_TYPE"] = "Trail"
    assert waterloo_region.to_record(variant, now) is None


def test_waterloo_statuses_and_reasons_give_the_event_type():
    _, found = records("ca-waterloo-region-road-closures")
    for item, record in found:
        properties = item["properties"]
        if properties["REASON"] == "Special Event":
            expected = EventType.SPECIAL_EVENT.value
        elif properties["STATUS"] == "Closed":
            emergency = properties["REASON"] == "Emergency"
            expected = EventType.EMERGENCY_ROAD_CLOSURE.value if emergency else EventType.PLANNED_ROAD_CLOSURE.value
        else:
            expected = EventType.LANE_RESTRICTION.value
        assert record.structured.event_type == expected
    floradale = by_id("ca-waterloo-region-road-closures", "4069407")
    assert floradale.structured.event_type == EventType.EMERGENCY_ROAD_CLOSURE.value
    assert floradale.structured.end is None  # the Region states no end


def test_waterloo_times_are_utc_milliseconds_and_region_numbers_stay_in_the_evidence():
    _, found = records("ca-waterloo-region-road-closures")
    for item, record in found:
        for field, moment in (("DATE_FROM", record.structured.start), ("DATE_TO", record.structured.end)):
            stated = item["properties"][field]
            assert moment == (datetime.fromtimestamp(stated / 1000, tz=timezone.utc) if stated else None)
    frederick = by_id("ca-waterloo-region-road-closures", "4068961")
    assert frederick.title == "Closed: Frederick St from Edna St to Ann St (Kitchener, Region of Waterloo)"
    assert frederick.structured.affected_road == "Frederick St"
    assert frederick.raw["item"]["properties"]["STREET_NAME"] == "Frederick St(6)"
    assert "Detour: Edna Street - Victoria Street - Bruce Street" in frederick.summary


def city_listing(now):
    """What the Kitchener and Cambridge feeds list now, read from the fixture's City samples."""
    handler, _ = serve("ca-waterloo-region-road-closures")
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return waterloo_region.city_closures("ua", client=client, now=now)


def region_closure(now, **changes):
    _, items = fixture("ca-waterloo-region-road-closures")
    item = copy.deepcopy(next(i for i in items if i["properties"]["CLOSURE_ID"] == 4069288))
    item["properties"].update(changes)
    return item


def test_street_names_are_compared_without_region_numbers_case_or_punctuation():
    assert waterloo_region.street_key("Fischer-Hallman Rd(58)") == "FISCHER HALLMAN RD"
    assert waterloo_region.street_key("FISCHER HALLMAN RD") == "FISCHER HALLMAN RD"
    assert waterloo_region.closure_key("King St E(8)", "Ottawa St N", "Stirling Ave N") == (
        waterloo_region.closure_key("KING ST E", "STIRLING AVE N", "OTTAWA ST N")
    )
    assert waterloo_region.closure_key("", "A St", "B St") is None


def test_on_5_november_no_region_closure_was_in_a_city_feed():
    now, items = fixture("ca-waterloo-region-road-closures")
    listed = city_listing(now)
    assert listed["KITCHENER"] and listed["CAMBRIDGE"]
    assert not any(waterloo_region.carried_by_city(item, listed) for item in items)


def test_a_region_closure_a_city_feed_already_lists_is_left_out():
    now, _ = fixture("ca-waterloo-region-road-closures")
    listed = city_listing(now)
    # Kitchener lists King St E between Stirling Ave N and Ottawa St N (Aug 2026 - Aug 2027).
    twin = region_closure(now, STREET_NAME="King St E(8)", STREET_FROM="Ottawa St N", STREET_TO="Stirling Ave N")
    assert waterloo_region.carried_by_city(twin, listed)
    # The same street and stretch in another period is another closure.
    earlier = {"DATE_FROM": 1735732800000, "DATE_TO": 1738411200000}  # January 2025
    assert not waterloo_region.carried_by_city({**twin, "properties": {**twin["properties"], **earlier}}, listed)
    # In another municipality, or another stretch: not the City's closure.
    elsewhere = {**twin, "properties": {**twin["properties"], "MUNICIPALITY": "Waterloo"}}
    assert not waterloo_region.carried_by_city(elsewhere, listed)
    other = {**twin, "properties": {**twin["properties"], "STREET_FROM": "Cameron St N"}}
    assert not waterloo_region.carried_by_city(other, listed)
    # Cambridge lists Birch St from Albert St to Elm St, all lanes (September - November 2026).
    birch = region_closure(
        now, STREET_NAME="Birch St", STREET_FROM="Albert St", STREET_TO="Elm St",
        MUNICIPALITY="Cambridge", DATE_FROM=1790000000000, DATE_TO=1795000000000,
    )  # fmt: skip
    assert waterloo_region.carried_by_city(birch, listed)


def test_a_region_closure_matching_a_city_item_rei_leaves_out_is_kept():
    now, _ = fixture("ca-waterloo-region-road-closures")
    listed = city_listing(now)
    # Cambridge's Addison Crt closure closes only a parking lane: its connector keeps nothing.
    addison = region_closure(
        now, STREET_NAME="Addison Crt", STREET_FROM="Bayne Cres", STREET_TO="End", MUNICIPALITY="Cambridge"
    )
    assert not waterloo_region.carried_by_city(addison, listed)


def test_waterloo_fetch_reads_both_region_layers_and_both_city_feeds():
    now, _ = fixture("ca-waterloo-region-road-closures")
    data = body("ca-waterloo-region-road-closures")
    twin = region_closure(
        now, CLOSURE_ID=9999001, STREET_NAME="King St E(8)", STREET_FROM="Stirling Ave N",
        STREET_TO="Ottawa St N",
    )  # fmt: skip
    moved = copy.deepcopy(data["current"][0])  # listed in both layers at the moment it moves
    layers = {
        f"{waterloo_region.CURRENT_LAYER}/query": data["current"] + [twin],
        f"{waterloo_region.FUTURE_LAYER}/query": data["future"] + [moved],
        f"{kitchener.LAYER}/query": data["kitchener"],
        f"{cambridge_on.LAYER}/query": data["cambridge"],
    }
    asked = []

    def handler(request):
        asked.append(str(request.url.copy_with(query=None)))
        return httpx.Response(200, json=feature_collection(layers[asked[-1]]))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    items = waterloo_region.fetch_closures("ua", client=client, now=now)
    assert asked == list(layers)
    ids = [item["properties"]["CLOSURE_ID"] for item in items]
    assert 9999001 not in ids  # Kitchener lists it
    assert len(ids) == len(set(ids)) == len(data["current"]) + len(data["future"])


def test_waterloo_run_fails_when_a_city_feed_cannot_be_read():
    now, _ = fixture("ca-waterloo-region-road-closures")
    data = body("ca-waterloo-region-road-closures")

    parts = {
        waterloo_region.CURRENT_LAYER: "current",
        waterloo_region.FUTURE_LAYER: "future",
        kitchener.LAYER: "kitchener",
    }

    def handler(request):
        layer = str(request.url.copy_with(query=None)).removesuffix("/query")
        if layer == cambridge_on.LAYER:
            return httpx.Response(404)
        return httpx.Response(200, json=feature_collection(data[parts[layer]]))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(ConnectorError):
        waterloo_region.fetch_closures("ua", client=client, now=now)


# --- Burlington ----------------------------------------------------------------------------


def test_burlington_empty_rows_are_left_out():
    now, items = fixture("ca-burlington-road-closures")
    empty = [item for item in items if not item["properties"]["blocknm"]]
    assert len(empty) == 4 and all(burlington.to_record(item, now) is None for item in empty)
    assert all(burlington.to_record(item, now) for item in items if item["properties"]["blocknm"])


def test_burlington_full_closure_reason_and_direction():
    _, found = records("ca-burlington-road-closures")
    for item, record in found:
        properties = item["properties"]
        if properties["blocktype"] == "Event":
            expected = EventType.SPECIAL_EVENT.value
        elif properties["fullclose"] == "Yes":
            expected = EventType.PLANNED_ROAD_CLOSURE.value
        elif properties["fullclose"] == "No":
            expected = EventType.LANE_RESTRICTION.value
        else:
            expected = EventType.ROAD_WORKS.value
        assert record.structured.event_type == expected
        # Only "Both" names the directions; another word stays on the location.
        both = properties["direction"] == "Both"
        assert record.structured.direction == ("BOTH_DIRECTIONS" if both else None)
        assert record.structured.locations[0].direction == properties["direction"]
        assert record.title.endswith(f"{properties['blocknm']} (Burlington)")
    now, _ = fixture("ca-burlington-road-closures")
    incident = copy.deepcopy(found[0][0])
    incident["properties"].update(blocktype="Incident", fullclose="Yes")
    assert burlington.to_record(incident, now).structured.event_type == EventType.EMERGENCY_ROAD_CLOSURE.value


def test_burlington_times_are_utc_milliseconds():
    _, found = records("ca-burlington-road-closures")
    for item, record in found:
        stated = item["properties"]["startdate"]
        assert record.structured.start == datetime.fromtimestamp(stated / 1000, tz=timezone.utc)


# --- fetching -------------------------------------------------------------------------------


@pytest.mark.parametrize("source_id", FEEDS)
def test_the_connector_fetches_without_a_key_and_keeps_what_is_in_effect(source_id):
    now, _ = fixture(source_id)
    handler, asked = serve(source_id)
    connector = connector_for(source_id, now, handler)
    kept = connector.fetch()
    assert asked and all(request.headers["User-Agent"] == "test-agent" for request in asked)
    for request in asked:
        params = dict(request.url.params)
        assert "key" not in params and "token" not in params
        if request.url.path.endswith("/query"):
            assert params["outSR"] == "4326" and params["f"] == "geojson" and params["outFields"] == "*"
    _, found = records(source_id)
    assert connector.observed_ids == {record.external_id for _, record in found}
    assert kept and all(r.structured.end is None or r.structured.end >= now for r in kept)
    ended = [r for _, r in found if r.structured.end is not None and r.structured.end < now]
    assert {r.external_id for r in kept} == {r.external_id for _, r in found} - {r.external_id for r in ended}


def test_ended_items_are_dropped_by_the_run_window():
    expected_ended = {
        "ca-longueuil-entraves": {"{494DED83-50B5-4CAD-81D3-E40F0D3D8346}", "{E28720E7-F7E8-4BDA-9634-62AC194DE852}"},
        "ca-saguenay-chantiers-511": {"2774377", "2780977"},
    }
    for source_id, ended in expected_ended.items():
        now, _ = fixture(source_id)
        handler, _ = serve(source_id)
        kept = {r.external_id for r in connector_for(source_id, now, handler).fetch()}
        assert ended and not ended & kept
    now, _ = fixture("ca-burlington-road-closures")
    handler, _ = serve("ca-burlington-road-closures")
    assert len(connector_for("ca-burlington-road-closures", now, handler).fetch()) == 6
    # A month later, Québec's work zones of early November are over.
    now, _ = fixture("ca-quebec-city-entraves-wzdx")
    handler, _ = serve("ca-quebec-city-entraves-wzdx")
    later = now + timedelta(days=30)
    kept = connector_for("ca-quebec-city-entraves-wzdx", later, handler).fetch()
    assert all(r.structured.end >= later for r in kept)
    assert len(kept) < len(records("ca-quebec-city-entraves-wzdx")[1])


# --- into the database -----------------------------------------------------------------------


def test_events_are_stored_once_and_every_value_fits_its_column(session):
    definitions = [make(scheduled=False) for _, make, _, _ in FEEDS.values()]
    SourceRepository(session).sync_registry(definitions)
    session.commit()
    city = get_city("canada")
    created = {}
    for definition in definitions:
        _, found = records(definition.source_id)

        def ingest(found=found, definition=definition):
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
