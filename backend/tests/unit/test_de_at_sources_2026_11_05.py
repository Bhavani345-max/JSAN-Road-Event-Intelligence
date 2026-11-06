"""MobiData BW roadworks, TechnologieRegion Karlsruhe roadworks, München roadworks
and Stadt Salzburg roadworks, on real excerpts of the responses served on
5 November 2026 at 12:33 UTC (the collections' counts are the excerpts' own).
München's public contact is replaced by a placeholder; nothing else is changed.
No test reaches any of the four services."""

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from sqlalchemy import String, select

from app.models import Event, EventVersion, Source, SourceArtifact
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from connectors.base import ConnectorError
from connectors.official import common, mobidata_bw, muenchen, salzburg, trk_karlsruhe
from packages.cities import get_city
from packages.event_schema import EventDirection, EventType
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass, TermsStatus
from services.extraction import KeywordClassifier, build_event_from_source, classify_source_record
from services.ingestion import run_ingestion

FIXTURES = Path(__file__).parents[1] / "fixtures"


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


MBW = _load("mobidata_bw_roadworks_2026-11-05.geojson")
TRK = _load("trk_karlsruhe_roadworks_2026-11-05.json")
MUC = _load("muenchen_baustellen_2026-11-05.geojson")
SBG = _load("salzburg_baustellen_2026-11-05.geojson")
NOW = datetime(2026, 11, 5, 12, 30, tzinfo=timezone.utc)
# The first minute of 7 November in Germany and Austria: works ending on 6 November have ended.
SATURDAY = datetime(2026, 11, 6, 23, 0, tzinfo=timezone.utc)
CEST, CET = timezone(timedelta(hours=2)), timezone(timedelta(hours=1))
UTC = timezone.utc


def _client(answer):
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return answer(request)

    return httpx.Client(transport=httpx.MockTransport(handler)), requests


def _serving(body):
    return _client(lambda request: httpx.Response(200, json=body))[0]


def _trk_serving(bodies):
    def answer(request):
        layer = parse_qs(urlsplit(str(request.url)).query)["typeName"][0].split(":")[1]
        return httpx.Response(200, json=bodies[layer])

    return _client(answer)


def _swap_first_feature(body):
    """The same response with its first feature's coordinates written latitude first."""
    swapped = copy.deepcopy(body)

    def flip(coordinates):
        if coordinates and isinstance(coordinates[0], (int, float)):
            return coordinates[::-1]
        return [flip(part) for part in coordinates]

    geometry = swapped["features"][0]["geometry"]
    geometry["coordinates"] = flip(geometry["coordinates"])
    return swapped


# --- the definitions ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "make, source_id, city_id, country, region, minutes",
    [
        (mobidata_bw.mobidata_bw_source, "de-mobidata-bw-roadworks", "germany", "DE", "Baden-Württemberg", 60),
        (trk_karlsruhe.trk_source, "de-trk-karlsruhe-roadworks", "germany", "DE", "Baden-Württemberg (Karlsruhe region)", 180),
        (muenchen.muenchen_source, "de-muenchen-roadworks", "germany", "DE", "Bayern (München)", 180),
        (salzburg.salzburg_source, "at-salzburg-roadworks", "austria", "AT", "Salzburg", 180),
    ],
)
def test_each_source_is_official_connected_run_by_hand_and_fits_its_columns(
    make, source_id, city_id, country, region, minutes
):
    definition = make(scheduled=False)
    assert definition.source_id == source_id
    assert (definition.city, definition.country, definition.region) == (city_id, country, region)
    assert definition.language == "de" and definition.polling_frequency_minutes == minutes
    assert definition.source_tier == 1 and definition.source_class is SourceClass.GOVERNMENT_OPEN_DATA
    assert definition.integration_status is IntegrationStatus.CONNECTED and definition.active is False
    assert make(scheduled=True).active is True
    assert definition.provides_geometry and definition.discovery_only is False
    # The licence was read; it is recorded, not taken as a legal review.
    assert definition.terms_status is TermsStatus.PERMITS_TESTING and definition.terms_reviewed is False
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    assert definition.licence and definition.attribution and definition.evidence_retention
    assert "5 November 2026" in definition.notes
    values = definition.model_dump(mode="json")
    too_long = {
        column.name
        for column in Source.__table__.columns
        if isinstance(column.type, String) and column.type.length
        and values.get(column.name) and len(str(values[column.name])) > column.type.length
    }
    assert not too_long


def test_the_licences_and_credits_are_the_ones_each_source_states():
    assert "dl-de/by-2-0" in mobidata_bw.mobidata_bw_source(scheduled=False).licence
    assert "Ministerium für Verkehr Baden-Württemberg" in mobidata_bw.ATTRIBUTION
    assert "CC BY 4.0" in trk_karlsruhe.trk_source(scheduled=False).licence
    assert "dl-de/by-2-0" in muenchen.muenchen_source(scheduled=False).licence
    assert "Landeshauptstadt München" in muenchen.ATTRIBUTION
    assert "CC BY 3.0 AT" in salzburg.salzburg_source(scheduled=False).licence
    assert salzburg.ATTRIBUTION.startswith("Datenquelle: Stadt Salzburg – data.stadt-salzburg.at")


# --- MobiData BW -------------------------------------------------------------------------


def _mbw(feature_id):
    return next(f for f in MBW["features"] if f["properties"]["id"] == feature_id)


def _mbw_record(feature_id):
    return mobidata_bw.to_record(_mbw(feature_id), NOW)


def test_mobidata_bw_keeps_each_works_with_its_stated_times_road_and_line():
    feature = _mbw("52738326-52738328-52738331-52741904.001")
    record = mobidata_bw.to_record(feature, NOW)
    event = record.structured
    assert record.external_id == "52738326-52738328-52738331-52741904.001"
    assert record.title == (
        "Road works: L153 L151/L153 (Rich.Segeten)-L154/L153 Tiefensteiner Brücke – Bauphase (Baden-Württemberg)"
    )
    assert event.event_type == EventType.ROAD_WORKS.value and event.category == "CONSTRUCTION"
    # Written with their offsets: winter time at the start, summer time at the end.
    assert event.start == datetime(2025, 2, 19, 0, 0, tzinfo=CET)
    assert event.end == datetime(2030, 8, 31, 23, 59, tzinfo=CEST)
    assert event.geometry == feature["geometry"] and event.geometry["type"] == "LineString"
    # One direction, not named: on the location only.
    assert event.direction is None and event.locations[0].direction == "one direction"
    assert event.affected_road == "L153 L151/L153 (Rich.Segeten)-L154/L153 Tiefensteiner Brücke"
    assert record.raw["item"] == feature  # nothing personal in the feed: kept as received


def test_mobidata_bw_closures_and_each_phase_of_a_tunnel_maintenance_are_their_own_records():
    first = _mbw_record("81904979-81904981-81904993-81904994-sperrung.001")
    second = _mbw_record("81904979-81904981-81904993-81904994-sperrung.002")
    assert first.external_id != second.external_id
    for record in (first, second):
        assert record.structured.event_type == EventType.PLANNED_ROAD_CLOSURE.value
        assert record.structured.direction == EventDirection.BOTH_DIRECTIONS.value
        assert record.structured.locations[0].closure == "ROAD_CLOSED"
    assert first.title == "Road closed: B38 Kreuz Weinheim-Reichelsheim – B38 Tunnelwartung Saukopftunnel (Baden-Württemberg)"
    assert (first.structured.start, first.structured.end) == (
        datetime(2026, 12, 7, 20, 0, tzinfo=CET),
        datetime(2026, 12, 8, 5, 0, tzinfo=CET),
    )
    # A motorway section is kept like any other.
    motorway = _mbw_record("84983081-84983083-84983086-84983087-sperrung.001")
    assert motorway.structured.affected_road == "A98 Weil am Rhein-Schaffhausen"


def test_mobidata_bw_a_municipal_road_written_as_its_class_names_no_road():
    record = _mbw_record("136181886-137793825-137793826-137794350.001")
    assert record.title == "Road works: Gemeindestraße – Bauphase 4 (Baden-Württemberg)"
    assert record.structured.affected_road is None and record.structured.locations == []
    assert "Gemeindestraße" in record.categories and record.structured.geometry["type"] == "LineString"
    # Its description may name the place, kept in words.
    altbach = _mbw_record("145847971-145852618-145852619-145852641-sperrung.001")
    assert altbach.summary.startswith("Altbach, Teckstraße auf Höhe von Hausnummer 23")


def test_mobidata_bw_an_unknown_type_keeps_its_words_and_no_event_type():
    feature = copy.deepcopy(_mbw("136181886-137793825-137793826-137794350.001"))
    feature["properties"]["type"] = "LANE_RESTRICTION_PLANNED"
    record = mobidata_bw.to_record(feature, NOW)
    assert record.structured.event_type is None
    assert record.title.startswith("Lane restriction planned: Gemeindestraße")


def test_mobidata_bw_leaves_out_points_written_latitude_first():
    points = [f for f in MBW["features"] if f["geometry"]["type"] == "Point"]
    assert len(points) == 2 and all(f["geometry"]["coordinates"][0] > 49 for f in points)
    assert all(mobidata_bw.to_record(f, NOW) is None for f in points)
    kept = [mobidata_bw.to_record(f, NOW) for f in MBW["features"] if f["geometry"]["type"] == "LineString"]
    assert len(kept) == 14 and all(kept)


def test_mobidata_bw_fetch_keeps_works_in_force_or_coming_within_a_year():
    connector = mobidata_bw.MobiDataBwRoadworksConnector(
        mobidata_bw.mobidata_bw_source(scheduled=True), "ua", client=_serving(MBW), clock=lambda: NOW
    )
    kept = {record.external_id for record in connector.fetch()}
    assert len(connector.observed_ids) == 14 and len(kept) == 13
    # The K4948 closure starts on 1 April 2031, beyond REI's run window of a year.
    assert "11680992-11681645-11681646-11681651-sperrung.001" not in kept
    later = mobidata_bw.MobiDataBwRoadworksConnector(
        mobidata_bw.mobidata_bw_source(scheduled=True), "ua", client=_serving(MBW), clock=lambda: SATURDAY
    )
    after = {record.external_id for record in later.fetch()}
    ended_on_friday = {
        "68774490-68774492-68774495-68774804-sperrung.001",
        "68774490-68774492-68774911-68774917.001",
        "135063786-154921760-154921761-154921766.001",
    }
    assert after == kept - ended_on_friday


def test_mobidata_bw_refuses_what_is_not_the_collection_and_a_response_written_latitude_first():
    client, requests = _client(lambda request: httpx.Response(200, json=MBW))
    assert len(mobidata_bw.fetch_roadworks("ua", client=client)) == len(MBW["features"])
    assert str(requests[0].url) == mobidata_bw.ENDPOINT and requests[0].headers["User-Agent"] == "ua"
    with pytest.raises(ConnectorError, match="feature collection"):
        mobidata_bw.fetch_roadworks("ua", client=_serving({"rows": []}))
    swapped = copy.deepcopy(MBW)
    for feature in swapped["features"]:
        if feature["geometry"]["type"] == "LineString":
            feature["geometry"]["coordinates"] = [position[::-1] for position in feature["geometry"]["coordinates"]]
    with pytest.raises(ConnectorError, match="latitude-longitude"):
        mobidata_bw.fetch_roadworks("ua", client=_serving(swapped))


# --- TechnologieRegion Karlsruhe ---------------------------------------------------------


def _trk_items(bodies=TRK):
    return trk_karlsruhe.works({layer: body["features"] for layer, body in bodies.items()})


def _trk_records():
    return {f"{i['datenquelle']}:{i['vorgangsnummer']}": trk_karlsruhe.to_record(i, NOW) for i in _trk_items()}


def test_trk_one_record_per_works_and_only_works_that_hinder_traffic():
    items = _trk_items()
    # 47 shapes: 44 of 16 works, 3 of Alsace (no works number, in France).
    assert sum(len(body["features"]) for body in TRK.values()) == 47
    assert len(items) == 16 and sum(len(item["features"]) for item in items) == 44
    assert not any(item["datenquelle"].startswith(trk_karlsruhe.FRANCE) for item in items)
    records = _trk_records()
    assert sorted(key for key, record in records.items() if record is None) == [
        "Stadt Karlsruhe:2021V4565",  # keine Verkehrsbehinderung
        "Stadt Stutensee:40180",  # keine Verkehrsbehinderung
    ]
    kinds = {key: record.structured.event_type for key, record in records.items() if record}
    assert kinds["Stadt Karlsruhe:2025V6087"] == EventType.PLANNED_ROAD_CLOSURE.value  # mit Vollsperrung
    assert kinds["Stadt Karlsruhe:2025V6088"] == EventType.PLANNED_ROAD_CLOSURE.value  # eine Fahrtrichtung
    assert kinds["Stadt Karlsruhe:2025V6773"] == EventType.ROAD_WORKS.value  # mit Verkehrsbehinderung
    assert records["Stadt Karlsruhe:2025V6088"].title == (
        "Road closed in one direction: Sophienstraße zw. Yorckstraße und Uhlandstraße (Karlsruhe)"
    )
    works = records["Stadt Karlsruhe:2025V6773"]
    assert works.title == "Road works: Gleistrasse entlang Steinkreuzstraße (Karlsruhe)"
    assert works.structured.category == "Gleisbau / mit Verkehrsbehinderung / Wanderbaustelle"
    assert "Works by: Verkehrsbetriebe Karlsruhe" in works.summary
    assert "coming" in records["Stadt Karlsruhe:2026V6757"].categories


def test_trk_keeps_the_stated_instants_in_utc():
    records = _trk_records()
    # A day stated as its local bounds: 22 October to 14 November, Karlsruhe time.
    uhland = records["Stadt Karlsruhe:2025V6087"].structured
    assert (uhland.start, uhland.end) == (
        datetime(2026, 10, 21, 22, 0, tzinfo=UTC),
        datetime(2026, 11, 14, 22, 59, 59, tzinfo=UTC),
    )
    # Hours: the Michaelstunnel's night closure from 22:00 to 04:00:59, Baden-Baden time.
    tunnel = records["Stadt Baden-Baden:40146"].structured
    assert (tunnel.start, tunnel.end) == (
        datetime(2026, 11, 4, 21, 0, tzinfo=UTC),
        datetime(2026, 11, 5, 3, 0, 59, tzinfo=UTC),
    )
    # An end a minute past midnight is kept as written.
    assert records["Stadt Rheinstetten:30070"].structured.end == datetime(2026, 11, 10, 23, 0, 59, tzinfo=UTC)
    assert records["Stadt Karlsruhe:2025V6087"].published_at is not None  # the date of the information


def test_trk_the_works_area_is_its_polygons_else_its_lines_else_its_point():
    records = _trk_records()
    two_areas = records["Stadt Karlsruhe:2025V6087"].structured.geometry
    assert two_areas["type"] == "MultiPolygon" and len(two_areas["coordinates"]) == 2
    assert records["Stadt Karlsruhe:2025V6088"].structured.geometry["type"] == "Polygon"
    assert records["Stadt Karlsruhe:2026V6684"].structured.geometry["type"] == "LineString"
    assert records["Stadt Stutensee:40166"].structured.geometry["type"] == "Point"  # a point only
    place = records["Stadt Stutensee:40113"]
    assert place.structured.affected_road == "76297 Stutensee, Krokusweg & Narzissenweg"
    assert place.structured.locations[0].kind == "street section"


def test_trk_a_new_stand_a_new_layer_or_renumbered_rows_are_not_a_revision_but_a_new_end_is():
    def key(bodies, number="2025V6087"):
        item = next(item for item in _trk_items(bodies) if item["vorgangsnummer"] == number)
        record = trk_karlsruhe.to_record(item, NOW)
        return trk_karlsruhe.TrkRoadworksConnector.revision_key(record.raw)

    first = key(TRK)
    touched = copy.deepcopy(TRK)
    for body in touched.values():
        for index, feature in enumerate(body["features"]):
            feature["id"] = f"renumbered.{index}"
            feature["properties"]["id"] = 90000 + index
            feature["properties"]["stand"] = "2026-11-06T23:00:00Z"
    assert key(touched) == first
    # A coming works that starts is listed in the current layer: the same works.
    coming = key(TRK, "2026V6757")
    moved = {
        "baustellen_aktuell": {"features": TRK["baustellen_aktuell"]["features"] + TRK["baustellen_vorschau"]["features"]},
        "baustellen_vorschau": {"features": []},
    }
    assert key(moved, "2026V6757") == coming
    extended = copy.deepcopy(TRK)
    for feature in extended["baustellen_aktuell"]["features"]:
        if feature["properties"].get("vorgangsnummer") == "2025V6087":
            feature["properties"]["vorgangszeitraum_bis"] = "2026-11-21T22:59:59Z"
    assert key(extended) != first


def test_trk_reads_both_layers_in_wgs84_and_drops_the_ended_night_closure():
    client, requests = _trk_serving(TRK)
    connector = trk_karlsruhe.TrkRoadworksConnector(
        trk_karlsruhe.trk_source(scheduled=True), "ua", client=client, clock=lambda: NOW
    )
    kept = {record.external_id for record in connector.fetch()}
    assert len(requests) == 2
    queries = [parse_qs(urlsplit(str(request.url)).query) for request in requests]
    assert [q["typeName"] for q in queries] == [["TBA:baustellen_aktuell"], ["TBA:baustellen_vorschau"]]
    assert all(q["srsName"] == ["EPSG:4326"] for q in queries)
    assert len(connector.observed_ids) == 14 and len(kept) == 13
    assert "Stadt Baden-Baden:40146" not in kept  # ended at 04:00:59 that morning


def test_trk_refuses_a_cut_list_and_latitude_first_coordinates():
    cut = copy.deepcopy(TRK)
    cut["baustellen_vorschau"]["numberMatched"] += 1
    with pytest.raises(ConnectorError, match="more than it returned"):
        trk_karlsruhe.fetch_works("ua", client=_trk_serving(cut)[0])
    swapped = {**TRK, "baustellen_aktuell": _swap_first_feature(TRK["baustellen_aktuell"])}
    with pytest.raises(ConnectorError, match="latitude-longitude"):
        trk_karlsruhe.fetch_works("ua", client=_trk_serving(swapped)[0])


# --- München -----------------------------------------------------------------------------


def _muc(feature_id):
    return next(f for f in MUC["features"] if f["id"] == f"baustellen_opendata.{feature_id}")


def _muc_record(feature_id):
    return muenchen.to_record(_muc(feature_id), NOW)


def test_muenchen_keeps_only_works_on_the_carriageway():
    records = {f["id"].split(".")[1]: muenchen.to_record(f, NOW) for f in MUC["features"]}
    left_out = sorted((key for key, record in records.items() if record is None), key=int)
    # Parking bays only ("Vollsperre"), no surface, pedestrian zone, pavement only, SWM pavement
    # works, a no-parking zone, a no-parking zone on the carriageway.
    assert left_out == ["1", "5", "8", "20", "31", "821", "4658"]
    kept = [record for record in records.values() if record]
    assert len(kept) == 14 and all(r.structured.event_type == EventType.ROAD_WORKS.value for r in kept)
    assert all(muenchen.CARRIAGEWAY in r.structured.category for r in kept)
    # However the surfaces are written.
    assert _muc_record(2).structured.category == "Baumaßnahme / GehwegFahrbahn"
    record = _muc_record(9)
    assert record.title == "Road works: Bezoldstraße 2 - 14 (München)"
    assert record.structured.locations[0].closure == "Vollsperre"  # the city's words, not a type
    assert record.categories == ["Baumaßnahme", "Parkbucht", "Fahrbahn"]


def test_muenchen_days_are_whole_munich_days_and_a_written_time_is_kept():
    karlsfelder = _muc_record(2).structured
    assert karlsfelder.start == datetime(2026, 5, 1, 0, 0, tzinfo=CEST)
    assert karlsfelder.end == datetime(2026, 12, 31, 23, 59, 59, tzinfo=CET)
    assert karlsfelder.stated_period == "01.05.2026 – 31.12.2026"
    brienner = _muc_record(319).structured
    assert brienner.end == datetime(2027, 3, 31, 23, 59, tzinfo=CEST)  # "31.03.2027 23:59"
    assert brienner.geometry == _muc(319)["geometry"] and brienner.geometry["type"] == "MultiPolygon"


def test_muenchen_a_start_stated_in_words_or_with_an_impossible_year_stays_unstated():
    old = _muc_record(339).structured
    assert old.start is None and old.end == datetime(2026, 12, 31, 23, 59, tzinfo=CET)
    assert old.stated_period == "Beginn vor mehr als einem Jahr – 31.12.2026 23:59"
    typo = _muc_record(12).structured
    assert _muc(12)["properties"]["beginn_datum_kombiniert"] == "07.11.0226"
    assert typo.start is None and typo.end == datetime(2026, 11, 13, 23, 59, 59, tzinfo=CET)
    assert typo.stated_period == "07.11.0226 – 13.11.2026"


def test_muenchen_ids_come_from_what_is_stated_and_no_contact_is_kept():
    feature = _muc(22)
    assert feature["properties"]["kontakt_oeffentlich"] == "[public contact]"
    record = muenchen.to_record(feature, NOW)
    assert "kontakt_oeffentlich" not in record.raw["item"]["properties"]
    assert "[public contact]" not in json.dumps(record.raw, ensure_ascii=False)
    key = muenchen.MuenchenRoadworksConnector.revision_key
    renumbered = copy.deepcopy(feature)
    renumbered["id"] = "baustellen_opendata.99999"
    again = muenchen.to_record(renumbered, NOW)
    assert again.external_id == record.external_id and key(again.raw) == key(record.raw)
    renumbered["properties"]["ende_datum_kombiniert"] = "20.11.2026"
    extended = muenchen.to_record(renumbered, NOW)
    assert extended.external_id == record.external_id and key(extended.raw) != key(record.raw)
    redrawn = copy.deepcopy(feature)
    redrawn["geometry"]["coordinates"][0][0][0][0] += 0.0001
    assert muenchen.to_record(redrawn, NOW).external_id != record.external_id
    # A works naming no street keeps no place.
    unnamed = _muc_record(18)
    assert unnamed.title == "Road works (München)" and unnamed.structured.affected_road is None
    assert unnamed.structured.locations == []


def test_muenchen_fetch_merges_works_listed_twice_and_drops_ended_ones():
    client, requests = _client(lambda request: httpx.Response(200, json=MUC))
    features = muenchen.fetch_works("ua", client=client)
    assert len(features) == len(MUC["features"]) - 1  # baustellen_opendata.1306 repeats .1305
    assert parse_qs(urlsplit(str(requests[0].url)).query)["typeName"] == [muenchen.LAYER]
    assert not any("kontakt_oeffentlich" in f["properties"] for f in features)
    source = muenchen.muenchen_source(scheduled=True)
    connector = muenchen.MuenchenRoadworksConnector(source, "ua", client=_serving(MUC), clock=lambda: NOW)
    kept = connector.fetch()
    assert len(connector.observed_ids) == 13 and len(kept) == 13
    later = muenchen.MuenchenRoadworksConnector(source, "ua", client=_serving(MUC), clock=lambda: SATURDAY)
    ended = {_muc_record(7).external_id, _muc_record(22).external_id}  # both end on 6 November
    assert {r.external_id for r in later.fetch()} == {r.external_id for r in kept} - ended


def test_muenchen_refuses_a_cut_list_and_latitude_first_coordinates():
    cut = {**MUC, "numberMatched": MUC["numberMatched"] + 1}
    with pytest.raises(ConnectorError, match="more than it returned"):
        muenchen.fetch_works("ua", client=_serving(cut))
    with pytest.raises(ConnectorError, match="latitude-longitude"):
        muenchen.fetch_works("ua", client=_serving(_swap_first_feature(MUC)))


def _answers(*responses):
    """A client answering each request with the next response in turn."""
    queue = list(responses)
    return _client(lambda request: queue.pop(0))


def test_muenchen_waits_out_the_layer_being_republished(monkeypatch):
    pauses = []
    monkeypatch.setattr(common, "_sleep", pauses.append)
    # As on 6 November 2026 at 08:20 and 11:20 UTC: an empty 200, then a 404; then the layer.
    client, requests = _answers(httpx.Response(200, content=b""), httpx.Response(404), httpx.Response(200, json=MUC))
    features = muenchen.fetch_works("ua", client=client)
    assert len(features) == len(MUC["features"]) - 1
    assert len(requests) == 3 and pauses == list(muenchen.REPUBLISH_PAUSES_SECONDS)


def test_muenchen_still_fails_when_the_layer_stays_away_or_the_server_refuses(monkeypatch):
    pauses = []
    monkeypatch.setattr(common, "_sleep", pauses.append)
    client, requests = _answers(*[httpx.Response(404) for _ in range(3)])
    with pytest.raises(ConnectorError, match="HTTP 404"):
        muenchen.fetch_works("ua", client=client)
    assert len(requests) == 3 and pauses == list(muenchen.REPUBLISH_PAUSES_SECONDS)
    # A refusal is not a republish: REI does not ask again sooner (decision 0041).
    for status in (403, 429, 503):
        pauses.clear()
        client, requests = _answers(httpx.Response(status))
        with pytest.raises(ConnectorError):
            muenchen.fetch_works("ua", client=client)
        assert len(requests) == 1 and pauses == [], status


# --- Salzburg ----------------------------------------------------------------------------


def _sbg_records(features=None):
    return {i["nummer"]: salzburg.to_record(i, NOW) for i in salzburg.works(features or SBG["features"])}


def test_salzburg_one_record_per_works_number_drawn_as_its_lines():
    records = _sbg_records()
    assert len(SBG["features"]) == 18 and len(records) == 17 and all(records.values())
    assert all(r.structured.event_type == EventType.ROAD_WORKS.value for r in records.values())
    # 195606 is drawn as a line and a multi-point: its line is the works.
    lastenstrasse = records["195606"]
    line = next(f for f in SBG["features"] if f["properties"]["NUMMER"] == 195606 and f["geometry"]["type"] == "LineString")
    assert lastenstrasse.external_id == "works:195606" and lastenstrasse.structured.geometry == line["geometry"]
    assert lastenstrasse.title == "Road works: Lastenstraße zwischen Weiserhofstraße und Gnigler Straße (Salzburg)"
    assert lastenstrasse.structured.locations[0].closure == "Einengung auf einen Fahrstreifen, teilweise Gesamtsperre"
    assert records["198593"].structured.geometry["type"] == "MultiLineString"
    assert records["198469"].structured.geometry["type"] == "Point"


def test_salzburg_days_are_whole_salzburg_days_and_no_time_is_supplied():
    records = _sbg_records()
    active = records["198435"].structured
    assert (active.start, active.end) == (
        datetime(2026, 10, 19, 0, 0, tzinfo=CEST),
        datetime(2026, 11, 27, 23, 59, 59, tzinfo=CET),
    )
    assert active.status == "Baustelle aktiv" and active.stated_period == "19.10.2026 – 27.11.2026"
    # Planned and stating no day: no time.
    planned = records["196325"].structured
    assert planned.start is None and planned.end is None and planned.stated_period is None
    assert planned.status == "Baustelle geplant"
    # Active since 2008, stated only to begin: kept as stated, without an end.
    old = records["66187"].structured
    assert old.start == datetime(2008, 1, 28, 0, 0, tzinfo=CET) and old.end is None
    assert old.stated_period == "28.01.2008 –"


def test_salzburg_titles_say_what_is_done_when_no_street_is_named():
    records = _sbg_records()
    assert records["198435"].title == "Road works: MA 6/04 Straßenbau (Salzburg)"
    assert records["198435"].structured.affected_road is None and records["198435"].structured.locations == []
    assert records["62947"].title == "Road works: 12 - Sonstige (Salzburg)"
    assert "wurde bis aufweiteres zurückgestellt" in records["62947"].summary
    assert records["81269"].structured.affected_road == "Fischbachstraße 45"


def test_salzburg_does_not_keep_the_case_officer_and_shape_numbers_are_not_content():
    features = copy.deepcopy(SBG["features"])
    for feature in features:
        feature["properties"].update(SACHBEARBEITER="[case officer]", SACHBEARBEITER_TELEFON="[telephone]")
    records = _sbg_records(features)
    evidence = json.dumps([r.raw for r in records.values()], ensure_ascii=False)
    for word in ("SACHBEARBEITER", "[case officer]", "[telephone]"):
        assert word not in evidence
    key = salzburg.SalzburgRoadworksConnector.revision_key
    renumbered = copy.deepcopy(SBG["features"])
    for index, feature in enumerate(renumbered):
        feature["id"] = f"baustelle.{index}"
        feature["properties"]["ID"] = index
    assert key(_sbg_records(renumbered)["195606"].raw) == key(_sbg_records()["195606"].raw)
    later = copy.deepcopy(SBG["features"])
    for feature in later:
        if feature["properties"]["NUMMER"] == 195606:
            feature["properties"]["ENDE"] = "31.01.2027"
    assert key(_sbg_records(later)["195606"].raw) != key(_sbg_records()["195606"].raw)


def test_salzburg_fetch_drops_the_ended_works_and_keeps_those_stating_no_day():
    source = salzburg.salzburg_source(scheduled=True)
    connector = salzburg.SalzburgRoadworksConnector(source, "ua", client=_serving(SBG), clock=lambda: NOW)
    kept = connector.fetch()
    assert len(connector.observed_ids) == 17 and len(kept) == 16
    assert "works:196097" not in {r.external_id for r in kept}  # planned, ended 4 September 2026
    undated = {r.external_id for r in kept if r.structured.start is None and r.structured.end is None}
    assert undated == {f"works:{n}" for n in ("196325", "166166", "166236", "62947", "198312", "81269")}
    cut = {**SBG, "numberMatched": SBG["numberMatched"] + 1}
    with pytest.raises(ConnectorError, match="more than it returned"):
        salzburg.fetch_works("ua", client=_serving(cut))
    with pytest.raises(ConnectorError, match="latitude-longitude"):
        salzburg.fetch_works("ua", client=_serving(_swap_first_feature(SBG)))


# --- through the pipeline ----------------------------------------------------------------


def _pipeline_client(source_id):
    if source_id == trk_karlsruhe.SOURCE_ID:
        return _trk_serving(TRK)[0]
    body = {mobidata_bw.SOURCE_ID: MBW, muenchen.SOURCE_ID: MUC, salzburg.SOURCE_ID: SBG}[source_id]
    return _serving(body)


@pytest.mark.parametrize(
    "make, connector_class",
    [
        (mobidata_bw.mobidata_bw_source, mobidata_bw.MobiDataBwRoadworksConnector),
        (trk_karlsruhe.trk_source, trk_karlsruhe.TrkRoadworksConnector),
        (muenchen.muenchen_source, muenchen.MuenchenRoadworksConnector),
        (salzburg.salzburg_source, salzburg.SalzburgRoadworksConnector),
    ],
)
def test_events_through_the_pipeline_located_by_the_source_and_fitting_their_columns(
    session, make, connector_class
):
    source = make(scheduled=True)
    city = get_city(source.city)
    SourceRepository(session).sync_registry([source])
    session.commit()
    connector = connector_class(source, "ua", client=_pipeline_client(source.source_id), clock=lambda: NOW)
    result = run_ingestion(connector, KeywordClassifier.for_city(city), SqlIngestionStore(session), None, city)
    session.commit()
    events = list(session.scalars(select(Event).where(Event.source_id == source.source_id)))
    assert result.events_created == len(events) > 0
    assert all(event.geometry and event.status == "VALIDATION_REQUIRED" for event in events)
    for record in connector_class(source, "ua", client=_pipeline_client(source.source_id), clock=lambda: NOW).fetch():
        event = build_event_from_source(record, classify_source_record(record, city), now=NOW, city=city)
        assert event is not None and event.severity is None
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
