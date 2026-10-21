"""GIPOD planned hindrance (Flanders), Hamburg roadworks (Bauweiser) and Vienna
roadworks, on real responses saved 21 October 2026 (trimmed; contact people
removed). No test reaches any of the three services."""

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import String, select

from app.models import Event, EventVersion, Source, SourceArtifact
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from connectors.base import ConnectorError
from connectors.official import gipod, hamburg_roadworks, vienna
from packages.cities import cities_within, country_entry, get_city
from packages.event_schema import EventType, LocationClass
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass, TermsStatus
from services.extraction import KeywordClassifier, build_event_from_source, classify_source_record
from services.ingestion import run_ingestion

FIXTURES = Path(__file__).parents[1] / "fixtures"
GIPOD = json.loads((FIXTURES / "gipod_hindrance_2026-10-21.geojson").read_text(encoding="utf-8"))
HAMBURG = json.loads((FIXTURES / "hamburg_roadworks_2026-10-21.geojson").read_text(encoding="utf-8"))
VIENNA = json.loads((FIXTURES / "vienna_roadworks_2026-10-21.json").read_text(encoding="utf-8"))
NOW = datetime(2026, 10, 21, 11, 0, tzinfo=timezone.utc)
BERLIN, WIEN = ZoneInfo("Europe/Berlin"), ZoneInfo("Europe/Vienna")


def by_id(document, feature_id):
    return next(f for f in document["features"] if str(f["id"]).endswith(feature_id))


def vienna_features():
    return [f for body in VIENNA.values() for f in body["features"]]


# --- the definitions and the configuration -------------------------------------------


@pytest.mark.parametrize(
    "make, city_id, country",
    [
        (gipod.gipod_source, "belgium", "BE"),
        (hamburg_roadworks.hamburg_roadworks_source, "hamburg", "DE"),
        (vienna.vienna_source, "vienna", "AT"),
    ],
)
def test_each_source_is_official_connected_run_by_hand_and_fits_its_columns(make, city_id, country):
    definition = make(scheduled=False)
    assert (definition.city, definition.country) == (city_id, country)
    assert definition.source_tier == 1 and definition.source_class is SourceClass.GOVERNMENT_OPEN_DATA
    assert definition.integration_status is IntegrationStatus.CONNECTED and definition.active is False
    assert make(scheduled=True).active is True
    assert definition.provides_geometry and definition.discovery_only is False
    # The licence was read; it is recorded, not taken as a legal review.
    assert definition.terms_status is TermsStatus.PERMITS_TESTING and definition.terms_reviewed is False
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    assert definition.licence and definition.attribution
    values = definition.model_dump(mode="json")
    too_long = {
        column.name
        for column in Source.__table__.columns
        if isinstance(column.type, String) and column.type.length
        and values.get(column.name) and len(str(values[column.name])) > column.type.length
    }
    assert not too_long


def test_vienna_lies_within_a_new_austria_entry():
    austria, wien = get_city("austria"), get_city("vienna")
    assert (austria.level, austria.country, wien.level, wien.country) == ("country", "AT", "city", "AT")
    assert country_entry(wien) == austria and cities_within(austria) == (wien,)
    assert wien.official_sources == ("vienna-roadworks",) and austria.official_sources == ()
    assert wien.timezone == austria.timezone == "Europe/Vienna"


# --- GIPOD -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "consequence, effect",
    [
        ("Geen doorgang voor gemotoriseerd verkeer", gipod.CLOSURE),
        ("Geen doorgang voor gemotoriseerd verkeer uitgezonderd plaatselijk verkeer", gipod.CLOSURE),
        ("Afgesloten in 1 rijrichting", gipod.CLOSURE),
        ("Vermindering van rijstroken", gipod.LANES),
        ("Versmalde rijstroken", gipod.LANES),
        ("Wisselend verkeer via verkeerslichten", gipod.LANES),
        ("Snelheidsbeperking", gipod.OTHER),
        ("Rijrichting omgekeerd", gipod.OTHER),
        ("Tijdelijk tweerichtingsverkeer", gipod.OTHER),
        ("Parkeerverbod", None),
        ("Beperkte doorgang voor voetgangers", None),
        ("Geen doorgang voor fietsers", None),
        ("Handelaars moeilijk bereikbaar", None),
    ],
)
def test_gipod_reads_what_each_stated_consequence_does_to_motor_traffic(consequence, effect):
    assert gipod.traffic_effect(consequence) == effect
    # Every consequence taken is one the server filter asks for.
    assert (effect is not None) == any(words in consequence for words in gipod.TRAFFIC_WORDS)


def test_gipod_types_come_from_the_consequences_and_parking_or_footway_zones_are_not_taken():
    taken = {}
    for feature in GIPOD["features"]:
        record = gipod.to_record(feature, NOW)
        stated = (feature["properties"]["Consequences"] or "").split(";")
        effects = {gipod.traffic_effect(consequence) for consequence in stated} - {None}
        taken[feature["id"]] = (effects, record.structured.event_type if record else "not taken")
    for effects, event_type in taken.values():
        if gipod.CLOSURE in effects:
            assert event_type == EventType.PLANNED_ROAD_CLOSURE.value
        elif gipod.LANES in effects:
            assert event_type == EventType.LANE_RESTRICTION.value
        elif effects:
            assert event_type is None  # a speed limit: its words kept, no type
        else:
            assert event_type == "not taken"
    assert sum(1 for _, t in taken.values() if t == "not taken") == 4


def test_gipod_keeps_the_zone_its_utc_times_and_severity_as_stated():
    feature = by_id(GIPOD, "-2610260500")
    record = gipod.to_record(feature, NOW)
    properties = feature["properties"]
    assert properties["HindranceStart"] == "2026-10-26T05:00:00Z" and properties["SevereHindrance"] is True
    assert record.structured.start == datetime(2026, 10, 26, 5, 0, tzinfo=timezone.utc)
    assert record.structured.end == datetime(2026, 10, 26, 16, 0, tzinfo=timezone.utc)
    assert record.structured.geometry == feature["geometry"] and feature["geometry"]["type"] == "MultiPolygon"
    assert record.structured.severity == "Severe hindrance" and record.structured.status == "Gevalideerd"
    # "9790 Wortegem-Petegem, Kleistraat: Werfzone": the place its description begins with.
    assert record.title == "Road closed: Kleistraat, 9790 Wortegem-Petegem (Gemeente Wortegem-Petegem)"
    assert record.structured.affected_road == "Kleistraat"
    assert record.structured.locations[0].closure == "Geen doorgang voor gemotoriseerd verkeer"
    assert record.external_id == feature["id"] and record.url.endswith(feature["id"])
    # A zone whose description names no place keeps no invented one.
    quiet = gipod.to_record(by_id(GIPOD, "-2411062300"), NOW)
    assert quiet.structured.locations == [] and quiet.structured.affected_road is None
    assert gipod.to_record(by_id(GIPOD, "-2610120500"), NOW).structured.severity is None


def test_gipod_does_not_keep_the_contact_people():
    feature = copy.deepcopy(by_id(GIPOD, "-2610260500"))
    feature["properties"]["HindranceContactOrganisations"] = '[{"ContactName":"x","Email":"x","Telephone":"x"}]'
    record = gipod.to_record(feature, NOW)
    assert "HindranceContactOrganisations" not in record.raw["item"]["properties"]
    assert "ContactName" not in json.dumps(record.raw)


def gipod_pages(features, size):
    """The fixture served as the API pages it: a `next` link while more remain."""
    requests = []

    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        start = int(parse_qs(urlsplit(str(request.url)).query).get("startIndex", ["0"])[0])
        page = features[start : start + size]
        links = []
        if start + size < len(features):
            href = f"{gipod.ENDPOINT}?f=application%2Fgeo%2Bjson&startIndex={start + size}"
            links.append({"rel": "next", "href": href})
        return httpx.Response(200, json={"type": "FeatureCollection", "features": page, "links": links})

    return httpx.Client(transport=httpx.MockTransport(answer)), requests


def test_gipod_follows_the_next_links_asking_only_for_motor_traffic_zones():
    client, requests = gipod_pages(GIPOD["features"], 8)
    zones = gipod.fetch_zones("ua", client=client)
    assert len(requests) == 3 and len(zones) == len(GIPOD["features"])
    first = parse_qs(urlsplit(str(requests[0].url)).query)
    assert first["filter"] == [gipod.TRAFFIC_FILTER] and first["filter-lang"] == ["cql-text"]
    assert first["crs"] == [gipod.CRS84] and first["limit"] == ["1000"]
    assert all(r.headers["User-Agent"] == "ua" for r in requests)


def test_gipod_stops_at_its_page_limit_and_never_follows_another_host(monkeypatch):
    monkeypatch.setattr(gipod, "MAX_PAGES", 2)
    client, _ = gipod_pages(GIPOD["features"], 5)
    with pytest.raises(ConnectorError, match="more than 2 pages"):
        gipod.fetch_zones("ua", client=client)
    away = [{"rel": "next", "href": "https://example.org/x"}]
    elsewhere = {"type": "FeatureCollection", "features": [], "links": away}
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=elsewhere)))
    with pytest.raises(ConnectorError, match="another host"):
        gipod.fetch_zones("ua", client=client)


def test_gipod_refuses_coordinates_written_latitude_first():
    feature = copy.deepcopy(GIPOD["features"][0])
    feature["geometry"]["coordinates"] = [
        [[[lat, lon] for lon, lat in ring] for ring in polygon]
        for polygon in feature["geometry"]["coordinates"]
    ]
    body = {"type": "FeatureCollection", "features": [feature], "links": []}
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body)))
    with pytest.raises(ConnectorError, match="latitude-longitude"):
        gipod.fetch_zones("ua", client=client)


def test_gipod_run_keeps_zones_not_ended_and_a_new_modification_time_is_no_revision():
    client, _ = gipod_pages(GIPOD["features"], 1000)
    source = gipod.gipod_source(scheduled=True)
    connector = gipod.GipodHindranceConnector(source, "ua", client=client, clock=lambda: NOW)
    kept = connector.fetch()
    ended = gipod.to_record(by_id(GIPOD, "-2610200500"), NOW)  # ended 21 Oct 05:00 UTC
    assert ended.external_id in connector.observed_ids and ended.external_id not in {r.external_id for r in kept}
    assert len(connector.observed_ids) == 18 and len(kept) == 17
    record = kept[0]
    touched = copy.deepcopy(record.raw)
    touched["item"]["properties"]["HindranceLastModifiedOn"] = "2026-10-22T08:00:00Z"
    assert connector.revision_key(touched) == connector.revision_key(record.raw)
    touched["item"]["properties"]["HindranceEnd"] = "2026-12-31T23:00:00Z"
    assert connector.revision_key(touched) != connector.revision_key(record.raw)


# --- Hamburg roadworks ------------------------------------------------------------------


def test_hamburg_works_are_road_works_over_whole_hamburg_days():
    records = [hamburg_roadworks.to_record(f, NOW) for f in HAMBURG["features"]]
    assert all(r.structured.event_type == EventType.ROAD_WORKS.value for r in records)
    feature = by_id(HAMBURG, "8193")
    record = hamburg_roadworks.to_record(feature, NOW)
    assert (feature["properties"]["baubeginn"], feature["properties"]["bauende"]) == ("02.03.2020", "31.12.2028")
    assert record.structured.start == datetime(2020, 3, 2, tzinfo=BERLIN)
    assert record.structured.end == datetime(2028, 12, 31, 23, 59, 59, tzinfo=BERLIN)
    assert record.structured.stated_period == "02.03.2020 – 31.12.2028"
    assert record.structured.geometry == feature["geometry"] and record.raw["item"] == feature
    assert record.structured.category == "Baustelle / Hotspot" and feature["properties"]["isthotspot"] is True
    assert record.title == "Road works: A 7 / Neubau Tunnel Altona (Hamburg)"
    assert record.external_id == "8193" and record.url.endswith("/items/8193")
    assert "govdata.de/dl-de/by-2-0" in record.structured.attribution


def test_hamburg_a_cut_list_or_a_new_update_time_is_handled():
    body = {**HAMBURG, "numberMatched": len(HAMBURG["features"]) + 1}
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body)))
    with pytest.raises(ConnectorError, match="more than one page"):
        hamburg_roadworks.fetch_works("ua", client=client)
    record = hamburg_roadworks.to_record(HAMBURG["features"][0], NOW)
    touched = copy.deepcopy(record.raw)
    touched["item"]["properties"]["letzteaktualisierung"] = "2026-10-22 08:00:00"
    key = hamburg_roadworks.HamburgRoadworksConnector.revision_key
    assert key(touched) == key(record.raw)
    touched["item"]["properties"]["bauende"] = "31.12.2030"
    assert key(touched) != key(record.raw)


# --- Vienna ------------------------------------------------------------------------------


def test_vienna_records_keep_their_id_when_the_source_renumbers_them():
    feature = VIENNA["BAUSTELLENLINOGD"]["features"][0]
    record = vienna.to_record(feature, NOW)
    renumbered = copy.deepcopy(feature)
    renumbered["id"] = "BAUSTELLENLINOGD.1"
    renumbered["properties"]["OBJECTID"] = 1
    again = vienna.to_record(renumbered, NOW)
    assert again.external_id == record.external_id
    key = vienna.ViennaRoadworksConnector.revision_key
    assert key(again.raw) == key(record.raw)
    renumbered["properties"]["OBJEKT_ENDE"] = "2027-12-31Z"
    extended = vienna.to_record(renumbered, NOW)
    assert extended.external_id == record.external_id and key(extended.raw) != key(record.raw)


def test_vienna_sections_of_one_works_are_separate_records():
    records = [vienna.to_record(f, NOW) for f in vienna_features()]
    assert len({r.external_id for r in records}) == len(records)
    albert = [r for r in records if r.structured.affected_road.startswith("Albertgasse")]
    assert len(albert) == 2 and albert[0].structured.geometry != albert[1].structured.geometry


def test_vienna_whole_vienna_days_and_works_kinds():
    feature = by_id(VIENNA["BAUSTELLENPKTOGD"], "1725059207")
    record = vienna.to_record(feature, NOW)
    stated = feature["properties"]
    assert (stated["OBJEKT_BEGINN"], stated["OBJEKT_ENDE"]) == ("2026-07-27Z", "2026-10-30Z")
    assert record.structured.start == datetime(2026, 7, 27, tzinfo=WIEN)
    assert record.structured.end == datetime(2026, 10, 30, 23, 59, 59, tzinfo=WIEN)
    assert record.structured.geometry == feature["geometry"]
    assert record.title == "Road works: Burggasse 25 bis 45 (Vienna, district 7)"
    assert record.url == vienna.DATASETS["BAUSTELLENPKTOGD"]
    assert all(vienna.to_record(f, NOW).structured.event_type == EventType.ROAD_WORKS.value for f in vienna_features())
    other = copy.deepcopy(feature)
    other["properties"]["BEHINDERUNGSART"] = "Veranstaltung"
    assert vienna.to_record(other, NOW).structured.event_type is None


def vienna_client(bodies):
    requests = []

    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        layer = parse_qs(urlsplit(str(request.url)).query)["typeName"][0].split(":")[1]
        return httpx.Response(200, json=bodies[layer])

    return httpx.Client(transport=httpx.MockTransport(answer)), requests


def test_vienna_reads_both_layers_in_wgs84_and_drops_the_contact_person():
    bodies = copy.deepcopy(VIENNA)
    bodies["BAUSTELLENLINOGD"]["features"][0]["properties"].update(ANSPRECHPERSON="x", ANSPRECHPERSON_TEL="x")
    client, requests = vienna_client(bodies)
    works = vienna.fetch_works("ua", client=client)
    assert len(works) == len(vienna_features()) and len(requests) == 2
    assert all(parse_qs(urlsplit(str(r.url)).query)["srsName"] == ["EPSG:4326"] for r in requests)
    assert not any("ANSPRECHPERSON" in f["properties"] or "ANSPRECHPERSON_TEL" in f["properties"] for f in works)


def test_vienna_refuses_a_cut_list_and_latitude_first_coordinates():
    cut = copy.deepcopy(VIENNA)
    cut["BAUSTELLENPKTOGD"]["numberMatched"] += 1
    with pytest.raises(ConnectorError, match="more than it returned"):
        vienna.fetch_works("ua", client=vienna_client(cut)[0])
    swapped = copy.deepcopy(VIENNA)
    point = swapped["BAUSTELLENPKTOGD"]["features"][0]["geometry"]
    point["coordinates"] = point["coordinates"][::-1]
    with pytest.raises(ConnectorError, match="latitude-longitude"):
        vienna.fetch_works("ua", client=vienna_client(swapped)[0])


# --- through the pipeline ------------------------------------------------------------------


def _client_for(source_id):
    if source_id == gipod.SOURCE_ID:
        return gipod_pages(GIPOD["features"], 1000)[0]
    if source_id == vienna.SOURCE_ID:
        return vienna_client(VIENNA)[0]
    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=HAMBURG)))


@pytest.mark.parametrize(
    "make, connector_class, city_id",
    [
        (gipod.gipod_source, gipod.GipodHindranceConnector, "belgium"),
        (hamburg_roadworks.hamburg_roadworks_source, hamburg_roadworks.HamburgRoadworksConnector, "hamburg"),
        (vienna.vienna_source, vienna.ViennaRoadworksConnector, "vienna"),
    ],
)
def test_events_through_the_pipeline_located_by_the_source_and_fitting_their_columns(
    session, make, connector_class, city_id
):
    source = make(scheduled=True)
    connector = connector_class(source, "ua", client=_client_for(source.source_id), clock=lambda: NOW)
    SourceRepository(session).sync_registry([source])
    session.commit()
    city = get_city(city_id)
    result = run_ingestion(connector, KeywordClassifier.for_city(city), SqlIngestionStore(session), None, city)
    session.commit()
    events = list(session.scalars(select(Event).where(Event.source_id == source.source_id)))
    assert result.events_created == len(events) > 0
    assert all(e.geometry and e.start_time and e.end_time for e in events)
    for record in connector_class(source, "ua", client=_client_for(source.source_id), clock=lambda: NOW).fetch():
        event = build_event_from_source(record, classify_source_record(record, city), now=NOW)
        assert event is not None and event.detection.location_class is LocationClass.SOURCE_PROVIDED
        assert event.status.value == "VALIDATION_REQUIRED" and event.severity is None
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
                    too_long.append((model.__tablename__, name))
    assert not too_long


def test_a_second_run_of_the_same_responses_adds_nothing(session):
    source = vienna.vienna_source(scheduled=True)
    SourceRepository(session).sync_registry([source])
    session.commit()
    city = get_city("vienna")
    for expected in (len(vienna_features()), 0):
        connector = vienna.ViennaRoadworksConnector(source, "ua", client=vienna_client(VIENNA)[0], clock=lambda: NOW)
        result = run_ingestion(connector, KeywordClassifier.for_city(city), SqlIngestionStore(session), None, city)
        session.commit()
        assert result.events_created == expected and result.revised == 0
    # The next day the source renumbers every record: still nothing new, nothing revised.
    renumbered = copy.deepcopy(VIENNA)
    for body in renumbered.values():
        for index, feature in enumerate(body["features"]):
            feature["id"] = f"{feature['id'].split('.')[0]}.{900000 + index}"
            feature["properties"]["OBJECTID"] = 900000 + index
    connector = vienna.ViennaRoadworksConnector(
        source, "ua", client=vienna_client(renumbered)[0], clock=lambda: NOW + timedelta(days=1)
    )
    result = run_ingestion(connector, KeywordClassifier.for_city(city), SqlIngestionStore(session), None, city)
    assert result.events_created == 0 and result.revised == 0
