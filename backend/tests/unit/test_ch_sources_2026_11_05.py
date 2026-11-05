"""The Swiss works feeds approved on 5 November 2026, on real excerpts of what
each served that day:

- Kanton Zürich, works on cantonal roads: 14 of 55 works (GeoJSON);
- Stadt Zürich, civil-engineering projects on public ground: 20 of 133 (GeoJSON);
- Kanton Schwyz, works over five days: 14 of 27 lines (12 works sites; GML 3.2
  on the LV95 grid), and the same 14 asked for in WGS 84 (EPSG:4326, latitude
  first);
- État de Genève, major works affecting mobility: 20 of 64 points (GeoJSON).

Contact persons, e-mail addresses and telephone numbers are replaced by
placeholders ("[Ansprechperson]", "[E-Mail]", "[Kontakt Bauleitung]" …);
Geneva's layer has none. The LV95 conversion (connectors/official/lv95.py) is
checked against swisstopo's worked example in "Approximate formulas for the
transformation between Swiss projection coordinates and WGS84" (December 2016),
section 2, and against the Schwyz server's own WGS 84 output. No test reaches
a service."""

import copy
import json
import math
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy import String, select

from app.models import Event, Source
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from connectors.base import ConnectorError
from connectors.official import ch_ge_infomobilite_works as ge
from connectors.official import ch_sz_canton_roadworks as sz
from connectors.official import ch_zh_canton_roadworks as zh
from connectors.official import ch_zurich_city_works as city
from connectors.official import lv95
from packages.cities import get_city
from packages.event_schema import EventType
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass, TermsStatus
from services.extraction import KeywordClassifier
from services.ingestion import run_ingestion

FIXTURES = Path(__file__).parents[1] / "fixtures"
ZH_FEED = json.loads((FIXTURES / "ch_zh_canton_roadworks_2026-11-05.geojson").read_text(encoding="utf-8"))
CITY_FEED = json.loads((FIXTURES / "ch_zurich_city_works_2026-11-05.geojson").read_text(encoding="utf-8"))
SZ_LV95 = (FIXTURES / "ch_sz_roadworks_2026-11-05.xml").read_text(encoding="utf-8")
SZ_WGS84 = (FIXTURES / "ch_sz_roadworks_wgs84_2026-11-05.xml").read_text(encoding="utf-8")
GE_FEED = json.loads((FIXTURES / "ge_infomobilite_chantiers_2026-11-05.geojson").read_text(encoding="utf-8"))
NOW = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
CEST, CET = timezone(timedelta(hours=2)), timezone(timedelta(hours=1))
SWITZERLAND = get_city("switzerland")
GML = "{http://www.opengis.net/gml/3.2}"
MS = "{http://mapserver.gis.umn.edu/mapserver}"

SOURCES = {
    zh.SOURCE_ID: zh.zh_canton_roadworks_source,
    city.SOURCE_ID: city.zurich_city_works_source,
    sz.SOURCE_ID: sz.sz_canton_roadworks_source,
    ge.SOURCE_ID: ge.ge_infomobilite_source,
}


def _dms(degrees: int, minutes: int, seconds: float) -> float:
    return degrees + minutes / 60 + seconds / 3600


def _metres_apart(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((phi2 - phi1) / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6_371_008.8 * math.asin(math.sqrt(h))


def _positions(geometry: dict) -> list[list[float]]:
    found, stack = [], [geometry["coordinates"]]
    while stack:
        value = stack.pop()
        if value and isinstance(value[0], (int, float)):
            found.append(value)
        else:
            stack.extend(value)
    return found


def _client(body, content_type="application/json", seen=None) -> httpx.Client:
    def answer(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        if isinstance(body, str):
            return httpx.Response(200, text=body, headers={"content-type": content_type})
        return httpx.Response(200, json=body)

    return httpx.Client(transport=httpx.MockTransport(answer))


def _zh_records():
    return [zh.to_record(feature, NOW) for feature in ZH_FEED["features"]]


def _city_records():
    return {feature["properties"]["titel"]: city.to_record(feature, NOW) for feature in CITY_FEED["features"]}


def _sz_sites():
    return sz.sites(sz.parse_feed(SZ_LV95))


def _sz_records():
    return [sz.to_record(site, NOW) for site in _sz_sites()]


def _ge_records():
    return {feature["id"]: ge.to_record(feature, NOW) for feature in GE_FEED["features"]}


# --- the country and the definitions ---------------------------------------------------


def test_switzerland_is_a_country_entry_covering_every_fixture_position():
    assert (SWITZERLAND.country, SWITZERLAND.timezone, SWITZERLAND.level) == ("CH", "Europe/Zurich", "country")
    shapes = [f["geometry"] for f in ZH_FEED["features"] + CITY_FEED["features"] + GE_FEED["features"]]
    shapes += [record.structured.geometry for record in _sz_records()]
    for shape in shapes:
        assert all(SWITZERLAND.covers(latitude, longitude) for longitude, latitude in _positions(shape))


@pytest.mark.parametrize("source_id", SOURCES)
def test_each_source_is_an_official_located_feed_recorded_as_permitted_with_attribution(source_id):
    definition = SOURCES[source_id](scheduled=False)
    assert definition.source_id == source_id
    assert definition.city == "switzerland" and definition.country == "CH" and definition.region
    assert definition.source_tier == 1 and definition.source_class is SourceClass.GOVERNMENT_OPEN_DATA
    assert definition.integration_status is IntegrationStatus.CONNECTED and definition.active is False
    assert SOURCES[source_id](scheduled=True).active is True
    assert definition.terms_status is TermsStatus.PERMITS_TESTING and definition.terms_reviewed is False
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    assert "opendata.swiss" in definition.licence and definition.attribution
    assert definition.events_supported == (EventType.ROAD_WORKS.value,)
    assert definition.provides_geometry and definition.polling_frequency_minutes in (360, 720)
    assert "5 November 2026" in definition.notes and definition.evidence_retention
    limits = {
        column.name: column.type.length
        for column in Source.__table__.columns
        if isinstance(column.type, String) and column.type.length
    }
    values = definition.model_dump(mode="json")
    assert all(len(str(values[name])) <= limit for name, limit in limits.items() if values.get(name) is not None)


def test_the_licences_are_the_catalogue_terms_of_each_dataset():
    schwyz = sz.sz_canton_roadworks_source(scheduled=False)
    # terms_by: the credit is required and names author, title and link.
    assert "Quellenangabe ist Pflicht" in schwyz.licence and sz.SOURCE_URL in schwyz.attribution
    assert (schwyz.language, schwyz.region) == ("de", "Schwyz")
    geneva = ge.ge_infomobilite_source(scheduled=False)
    assert "terms_open" in geneva.licence and (geneva.language, geneva.region) == ("fr", "Genève")
    for definition in (zh.zh_canton_roadworks_source(scheduled=False), city.zurich_city_works_source(scheduled=False)):
        assert "terms_open" in definition.licence and definition.language == "de"


# --- Kanton Zürich ------------------------------------------------------------------------


def test_zurich_canton_every_works_is_one_record_named_by_its_road_and_kilometres():
    records = _zh_records()
    assert len(records) == 14 and all(record is not None for record in records)
    assert len({record.external_id for record in records}) == 14
    assert all(record.structured.event_type == EventType.ROAD_WORKS.value for record in records)
    first = records[0]
    assert first.external_id == "road:300:km:0.625-1.275"
    assert first.title == "Road works: Ostring (Regensdorf)"
    assert "Strasse 300, km 0.625 – 1.275" in first.summary and "Staatsstrasse" not in first.summary
    assert first.structured.status == "aktiv (Bauzeit)" and first.structured.affected_road == "Ostring"
    assert first.structured.geometry == ZH_FEED["features"][0]["geometry"]
    # The works' own page on zh.ch is the record's address; a video link is not.
    by_street = {record.structured.affected_road: record for record in records}
    assert by_street["Grütstrasse"].url.startswith("https://www.zh.ch/de/planen-bauen/tiefbau/baustellen/")
    assert by_street["Ferrachstrasse"].url == zh.SOURCE_URL


def test_zurich_canton_days_are_whole_days_whatever_clock_time_they_carry():
    by_street = {record.structured.affected_road: record.structured for record in _zh_records()}
    ostring = by_street["Ostring"]  # 2026-03-02T00:00:00 – 2027-08-27T00:00:00
    assert ostring.start == datetime(2026, 3, 2, 0, 0, tzinfo=CET)
    assert ostring.end == datetime(2027, 8, 27, 23, 59, 59, tzinfo=CEST)
    weiningen = by_street["Niederholzstrasse / Überlandstrasse"]  # 08:26:18 and 08:26:30: when entered
    assert weiningen.start == datetime(2026, 4, 20, 0, 0, tzinfo=CEST)
    assert weiningen.end == datetime(2028, 5, 31, 23, 59, 59, tzinfo=CEST)
    assert weiningen.stated_period == "2026-04-20 – 2028-05-31"
    assert by_street["Industriestrasse"].end == datetime(2026, 12, 18, 23, 59, 59, tzinfo=CET)  # '01:00'
    coming = [s.affected_road for s in by_street.values() if s.start > NOW]
    assert sorted(coming) == ["A52 Forchautostrasse", "Frauenfelderstrasse", "Zürcherstrasse (Adlergasse bis Zürcherstr. 15)"]


def test_zurich_canton_keeps_no_contact_person_or_telephone_and_a_new_edit_time_is_no_revision():
    records = _zh_records()
    evidence = json.dumps([record.raw for record in records], ensure_ascii=False)
    for word in ("ansprechperson", "telefonnummer", "[Ansprechperson]", "[Telefonnummer]"):
        assert word not in evidence
    feature = ZH_FEED["features"][0]
    key = zh.ZhCantonRoadworksConnector.revision_key
    touched = copy.deepcopy(feature)
    touched["properties"]["lmutdat"] = "2026-11-05T09:00:00"
    assert key(zh.to_record(touched, NOW).raw) == key(zh.to_record(feature, NOW).raw)
    later = copy.deepcopy(feature)
    later["properties"]["datum_bauende"] = "2027-09-30T00:00:00"
    assert zh.to_record(later, NOW).external_id == records[0].external_id
    assert key(zh.to_record(later, NOW).raw) != key(zh.to_record(feature, NOW).raw)


def test_zurich_canton_fetch_reads_the_layer_and_refuses_a_cut_or_swapped_one():
    seen: list[httpx.Request] = []
    connector = zh.ZhCantonRoadworksConnector(
        zh.zh_canton_roadworks_source(scheduled=True), "ua", client=_client(ZH_FEED, seen=seen), clock=lambda: NOW
    )
    kept = connector.fetch()
    assert len(kept) == 14 and len(connector.observed_ids) == 14
    assert seen[0].url.params["srsName"] == "EPSG:4326" and seen[0].url.params["outputFormat"] == "geojson"
    swapped = copy.deepcopy(ZH_FEED)
    ring = swapped["features"][0]["geometry"]["coordinates"][0]
    ring[:] = [position[::-1] for position in ring]
    for bad in ({"rows": []}, {**ZH_FEED, "numberMatched": 55}, swapped):
        with pytest.raises(ConnectorError):
            zh.ZhCantonRoadworksConnector(
                zh.zh_canton_roadworks_source(scheduled=True), "ua", client=_client(bad), clock=lambda: NOW
            ).fetch()


# --- Stadt Zürich -------------------------------------------------------------------------


def test_zurich_city_keeps_projects_on_roads_and_leaves_out_parks_pools_schools_and_rail():
    records = _city_records()
    left_out = sorted(title.strip() for title, record in records.items() if record is None)
    assert left_out == [
        "Fabrikkanal_Spinnerei_Manegg",
        "Freibad Letzigraben, Sportinfrastruktur",
        "Gartenareal Dunkelhölzli",
        "Messnetzerweiterung ERZ",
        "Quartierpark Süssleren - Instandsetzung",
        "Stadelhofen Tunnelausbau SBB",
        "Thurgauerstrasse Quartierpark",
        "Untere Zäune Spielplatz Leueplätzli",
        "Velostation Andreasstrasse",
    ]
    kept = [record for record in records.values() if record is not None]
    assert len(kept) == 11 and all(r.structured.event_type == EventType.ROAD_WORKS.value for r in kept)
    first = records["Scheideggstrasse, Steinhaldenstrasse"]
    assert first.external_id == "project:5704"
    assert first.title == "Road works: Scheideggstrasse, Steinhaldenstrasse (Zürich)"
    assert first.url.endswith("baustellen-info.html?id=5704")
    assert "Baubereich: Gabler- bis Brunaustrasse" in first.summary and "Kreis 2" in first.summary
    assert first.structured.geometry["type"] == "MultiPolygon"
    longitude, latitude = _positions(first.structured.geometry)[0]
    assert 8.4 < longitude < 8.7 and 47.3 < latitude < 47.5
    # A title that names no street gives no affected road.
    assert records["Elektrifizierung Buslinie 80"].structured.affected_road is None
    assert records["Bucheggplatz, Fussgängerspinne"].structured.affected_road == "Bucheggplatz, Fussgängerspinne"


def test_zurich_city_days_are_whole_days_and_no_project_leader_is_kept():
    records = _city_records()
    limmatquai = records["Limmatquai"].structured
    assert limmatquai.start == datetime(2026, 11, 10, 0, 0, tzinfo=CET)
    assert limmatquai.end == datetime(2029, 9, 3, 23, 59, 59, tzinfo=CEST)
    assert limmatquai.stated_period == "2026-11-10 – 2029-09-03"
    evidence = json.dumps([record.raw for record in records.values() if record], ensure_ascii=False)
    for word in ("projektleiter", "projektleiter_email", '"tel"', "[Projektleiter]", "[E-Mail]", "[Telefon]"):
        assert word not in evidence


def test_zurich_city_a_new_snapshot_is_no_revision_and_fetch_refuses_a_swapped_layer():
    feature = CITY_FEED["features"][0]
    key = city.ZurichCityWorksConnector.revision_key
    snapshot = copy.deepcopy(feature)
    snapshot["properties"].update(stand="20261105", objectid=99)
    snapshot["id"] = "aer_baustellen_a.99"
    assert key(city.to_record(snapshot, NOW).raw) == key(city.to_record(feature, NOW).raw)
    later = copy.deepcopy(feature)
    later["properties"]["bauende"] = "2027-09-30"
    assert key(city.to_record(later, NOW).raw) != key(city.to_record(feature, NOW).raw)
    connector = city.ZurichCityWorksConnector(
        city.zurich_city_works_source(scheduled=True), "ua", client=_client(CITY_FEED), clock=lambda: NOW
    )
    assert len(connector.fetch()) == 11 and len(connector.observed_ids) == 11
    swapped = copy.deepcopy(CITY_FEED)
    polygon = swapped["features"][0]["geometry"]["coordinates"][0][0]
    polygon[:] = [position[::-1] for position in polygon]
    with pytest.raises(ConnectorError, match="latitude-longitude"):
        city.ZurichCityWorksConnector(
            city.zurich_city_works_source(scheduled=True), "ua", client=_client(swapped), clock=lambda: NOW
        ).fetch()


# --- LV95 ---------------------------------------------------------------------------------


# swisstopo's worked examples (December 2016). Section 2, LV95 to WGS 84:
# E 2 700 000, N 1 100 000 -> λ 8° 43' 49.80", φ 46° 02' 38.86" by the formulas
# (λ' 3.14297976, φ' 16.57588564), the rigorous values being 8° 43' 49.79",
# 46° 02' 38.87". Section 1, the other way: φ 46° 02' 38.87", λ 8° 43' 49.79" ->
# E 2 699 999.76, N 1 099 999.97.
def test_lv95_gives_swisstopos_worked_example():
    longitude, latitude = lv95.to_lon_lat(2_700_000, 1_100_000)
    assert longitude * 36 / 100 == pytest.approx(3.14297976, abs=5e-7)
    assert latitude * 36 / 100 == pytest.approx(16.57588564, abs=5e-7)
    # The formulas' own result, to the hundredth of a second given.
    assert abs(longitude - _dms(8, 43, 49.80)) * 3600 < 0.006
    assert abs(latitude - _dms(46, 2, 38.86)) * 3600 < 0.006
    # The rigorous values, within the precision swisstopo states (0.12" in longitude, 0.08" in latitude).
    for easting, northing in ((2_700_000, 1_100_000), (2_699_999.76, 1_099_999.97)):
        longitude, latitude = lv95.to_lon_lat(easting, northing)
        assert abs(longitude - _dms(8, 43, 49.79)) * 3600 < 0.12
        assert abs(latitude - _dms(46, 2, 38.87)) * 3600 < 0.08
        assert _metres_apart(longitude, latitude, _dms(8, 43, 49.79), _dms(46, 2, 38.87)) < 1.0


def test_lv95_converts_a_shape_whole_or_not_at_all():
    assert lv95.grid_position("2689429.115252", "1209128.939141") == (2689429.115252, 1209128.939141)
    for easting, northing in ((None, 1_200_000), ("x", 1_200_000), (8.6, 47.0), (2_600_000, float("nan"))):
        assert lv95.grid_position(easting, northing) is None
    line = [[2_689_429.1, 1_209_128.9], [2_689_951.0, 1_209_339.9]]
    shape = lv95.geometry("LineString", line)
    assert shape["type"] == "LineString" and len(shape["coordinates"]) == 2
    assert lv95.geometry("LineString", [*line, [47.0, 8.6]]) is None
    assert lv95.geometry("GeometryCollection", line) is None


def test_lv95_agrees_with_the_schwyz_servers_own_wgs84_output_within_a_metre():
    """The same 14 lines asked for in EPSG:4326: written latitude first."""
    root = ET.fromstring(SZ_WGS84)
    wgs84 = []
    for feature in root.iter(f"{MS}ch.sz.a083a.baustellen.erweitert"):
        values = [float(v) for v in feature.find(f".//{GML}posList").text.split()]
        wgs84.append((feature.findtext(f"{MS}lokalname").strip(), list(zip(values[0::2], values[1::2]))))
    grid = sz.parse_feed(SZ_LV95)
    assert [name for name, _ in wgs84] == [feature["properties"]["lokalname"] for feature in grid]
    # Seewen, in Schwyz (about 47.03 N, 8.62 E): the first number is the latitude.
    latitude, longitude = wgs84[0][1][0]
    assert 46.9 < latitude < 47.3 and 8.4 < longitude < 9.0
    assert _metres_apart(longitude, latitude, 8.65, 47.02) < 4_000  # Schwyz town, ≈ 47.02 N, 8.65 E
    worst = 0.0
    for (name, positions), feature in zip(wgs84, grid):
        (line,) = feature["lines"]
        assert len(line) == len(positions), name
        for (easting, northing), (latitude, longitude) in zip(line, positions):
            worst = max(worst, _metres_apart(*lv95.to_lon_lat(easting, northing), longitude, latitude))
    assert worst < 1.0


# --- Kanton Schwyz ------------------------------------------------------------------------


def test_schwyz_lines_that_state_the_same_are_one_works_site():
    features = sz.parse_feed(SZ_LV95)
    assert len(features) == 14
    sites = _sz_sites()
    assert len(sites) == 12
    records = _sz_records()
    assert all(record is not None for record in records) and len({r.external_id for r in records}) == 12
    assert all(r.external_id.startswith("site:") and r.structured.event_type == EventType.ROAD_WORKS.value for r in records)
    by_title: dict[str, list] = {}
    for record in records:
        by_title.setdefault(record.title, []).append(record)
    brunnen = by_title["Road works: Bahnhofareal - ÖV - Drehscheibe (Kanton Schwyz)"]
    assert len(brunnen) == 1 and brunnen[0].structured.geometry["type"] == "MultiLineString"
    assert len(brunnen[0].structured.geometry["coordinates"]) == 2
    # Spelt differently: its own record.
    assert len(by_title["Road works: Bahnhofareal - ÖV - Drescheibe (Kanton Schwyz)"]) == 1
    # Two lines rated "gering" are one site; the line rated "mittel" is another.
    churer = sorted(by_title["Road works: 3 / Churerstrasse (Kanton Schwyz)"], key=lambda r: r.structured.severity)
    assert [r.structured.severity for r in churer] == ["gering", "mittel"]
    assert [r.structured.geometry["type"] for r in churer] == ["MultiLineString", "LineString"]


def test_schwyz_a_site_states_its_place_days_and_hindrance_in_the_sources_words():
    record = _sz_records()[0]
    assert record.title == "Road works: 2 / Lauerzerstrasse / Zingel in Seewen SZ (Kanton Schwyz)"
    structured = record.structured
    assert structured.start == datetime(2025, 8, 18, 0, 0, tzinfo=CEST)
    assert structured.end == datetime(2027, 10, 1, 23, 59, 59, tzinfo=CEST)
    assert structured.stated_period == "2025-08-18 – 2027-10-01" and structured.severity == "mittel"
    assert structured.affected_road == "2 / Lauerzerstrasse / Zingel in Seewen SZ"
    assert record.summary == (
        "Strasseninstandstellung, Errichtung einer neuen Stützmauer, Renaturierung. "
        "Behinderung mittel: Einspurig, mit LSA oder Drehkelle geregelt. Der Rad-Gehweg ist ständig geöffnet."
    )
    assert record.url == sz.SOURCE_URL and record.categories == ["Baustelle", "mittel"]
    # Longitude first, in Seewen.
    longitude, latitude = structured.geometry["coordinates"][0]
    assert 8.6 < longitude < 8.63 and 47.02 < latitude < 47.04
    assert structured.locations[0].kind == "street section"


def test_schwyz_keeps_no_contact_and_a_changed_end_is_a_revision_of_the_same_site():
    records = _sz_records()
    evidence = json.dumps([record.raw for record in records], ensure_ascii=False)
    for word in ("kontaktbauleitung", "kontakttba", "[Kontakt"):
        assert word not in evidence
    site = _sz_sites()[0]
    later = copy.deepcopy(site)
    later["properties"]["bauende"] = "2027-12-17"
    assert sz.site_id(later) == sz.site_id(site)
    assert sz.to_record(later, NOW).content_hash != sz.to_record(site, NOW).content_hash
    redrawn = copy.deepcopy(site)
    redrawn["lines"][0][0][0] += 5.0
    assert sz.site_id(redrawn) != sz.site_id(site)


def _sz_connector(body: str, seen=None) -> sz.SzCantonRoadworksConnector:
    return sz.SzCantonRoadworksConnector(
        sz.sz_canton_roadworks_source(scheduled=True), "ua", client=_client(body, "text/xml", seen), clock=lambda: NOW
    )


def test_schwyz_fetch_asks_for_lv95_keeps_sites_in_force_and_refuses_another_grid_or_a_cut_list():
    seen: list[httpx.Request] = []
    connector = _sz_connector(SZ_LV95, seen)
    kept = connector.fetch()
    params = seen[0].url.params
    assert params["SRSNAME"] == "urn:ogc:def:crs:EPSG::2056" and params["ogcserver"] == "source for image/png"
    assert params["TYPENAMES"] == "ms:ch.sz.a083a.baustellen.erweitert"
    assert len(connector.observed_ids) == 12
    # "386.1 / Zürichstrasse" ended on 31 October and is still listed: not kept by the run.
    assert len(kept) == 11 and all("Zürichstrasse" not in record.title for record in kept)
    # The same layer in WGS 84 is not what was asked for.
    with pytest.raises(ConnectorError, match="not LV95"):
        _sz_connector(SZ_WGS84).fetch()
    cut = SZ_LV95.replace('numberMatched="14"', 'numberMatched="27"')
    with pytest.raises(ConnectorError, match="more than it returned"):
        _sz_connector(cut).fetch()
    exception = (
        '<?xml version="1.0"?><ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1">'
        "<ows:Exception><ows:ExceptionText>msWFSGetFeature(): unknown layer</ows:ExceptionText></ows:Exception>"
        "</ows:ExceptionReport>"
    )
    for bad in (exception, "<html>not the layer</html>", "not xml"):
        with pytest.raises(ConnectorError):
            _sz_connector(bad).fetch()
    first_line = '<gml:posList srsDimension="2">2689429.115252 1209128.939141'
    assert SZ_LV95.count(first_line) == 1
    off_grid = SZ_LV95.replace(first_line, '<gml:posList srsDimension="2">47.027173 8.615094')
    with pytest.raises(ConnectorError, match="off the Swiss LV95 grid"):
        _sz_connector(off_grid).fetch()


# --- État de Genève -----------------------------------------------------------------------


def test_geneva_keeps_works_that_change_road_traffic_only():
    records = _ge_records()
    # Pedestrians, parking and replacement shuttles; the Voie Verte path; parking only.
    assert sorted(object_id for object_id, record in records.items() if record is None) == [7, 33, 38]
    kept = [record for record in records.values() if record is not None]
    assert len(kept) == 17 and all(r.structured.event_type == EventType.ROAD_WORKS.value for r in kept)
    assert ge.on_the_road("Suppression des places de stationnement.") is False
    assert ge.on_the_road("Fermeture de la bretelle d'accès à la Voie Verte aux piétons et vélos, déviations.") is False
    assert ge.on_the_road("Fermeture de la rue Chabrey, accès piétons garanti.") is True
    assert ge.on_the_road("Suppression de la voie bus, ralentissements.") is True
    assert ge.on_the_road("") is True  # nothing stated: not a reason to leave the works out


def test_geneva_a_works_states_its_address_days_and_disruption_in_the_sources_words():
    records = _ge_records()
    first = records[1]
    assert first.title == "Road works: Avenue Cardinal-Mermillod (Genève)"
    assert first.summary == "Fermeture de la route, déviations. Maître d'ouvrage : Commune."
    assert first.external_id.startswith("works:") and first.url == ge.SOURCE_URL
    structured = first.structured
    assert structured.start == datetime(2026, 6, 30, 0, 0, tzinfo=CEST)
    assert structured.end == datetime(2026, 12, 31, 23, 59, 59, tzinfo=CET)
    assert structured.stated_period == "du 30-06-2026 au 31-12-2026" and structured.status == "Ouvert"
    assert structured.affected_road == "Avenue Cardinal-Mermillod"
    feature = next(f for f in GE_FEED["features"] if f["id"] == 1)
    assert structured.geometry == feature["geometry"] == {"type": "Point", "coordinates": [6.143233709922999, 46.186442284576856]}
    # The Nations tunnel, nights of 9 to 11 November: coming, with its information sheet.
    nations = records[45]
    assert nations.structured.start == datetime(2026, 11, 9, 0, 0, tzinfo=CET) > NOW
    assert nations.url.startswith("https://ge.ch/sitg/geodata/SIMOBILITE/PCMOB/") and nations.url.endswith(".pdf")
    # "Termine" is not documented and the days run to 18 December: kept, not read as ended.
    dussaud = records[57].structured
    assert dussaud.status == "Termine" and dussaud.reported_ended is False
    assert dussaud.end == datetime(2026, 12, 18, 23, 59, 59, tzinfo=CET)
    assert records[39].structured.status == ">12 mois"


def test_geneva_ids_do_not_follow_the_row_numbers_but_a_changed_end_is_a_revision():
    key = ge.GeInfomobiliteWorksConnector.revision_key
    first = {object_id: (r.external_id, key(r.raw)) for object_id, r in _ge_records().items() if r}
    renumbered = copy.deepcopy(GE_FEED)
    for number, feature in enumerate(reversed(renumbered["features"]), start=101):
        feature["id"] = feature["properties"]["OBJECTID"] = number
    again = {(r.external_id, key(r.raw)) for f in renumbered["features"] if (r := ge.to_record(f, NOW))}
    assert again == set(first.values())
    later = copy.deepcopy(next(f for f in GE_FEED["features"] if f["id"] == 1))
    later["properties"]["DATE_FIN"] = "20270131"
    record = ge.to_record(later, NOW)
    assert record.external_id == first[1][0] and key(record.raw) != first[1][1]


def test_geneva_fetch_reads_the_layer_in_wgs84_and_refuses_an_error_or_swapped_points():
    seen: list[httpx.Request] = []
    connector = ge.GeInfomobiliteWorksConnector(
        ge.ge_infomobilite_source(scheduled=True), "ua", client=_client(GE_FEED, seen=seen), clock=lambda: NOW
    )
    kept = connector.fetch()
    assert len(kept) == 17 and len(connector.observed_ids) == 17
    params = seen[0].url.params
    assert str(seen[0].url).startswith(f"{ge.LAYER}/query") and (params["outSR"], params["f"]) == ("4326", "geojson")
    swapped = copy.deepcopy(GE_FEED)
    swapped["features"][0]["geometry"]["coordinates"].reverse()
    for bad, message in (({"error": {"code": 400, "message": "Invalid query"}}, "error"), (swapped, "latitude-longitude")):
        with pytest.raises(ConnectorError, match=message):
            ge.GeInfomobiliteWorksConnector(
                ge.ge_infomobilite_source(scheduled=True), "ua", client=_client(bad), clock=lambda: NOW
            ).fetch()


# --- through ingestion ----------------------------------------------------------------------


def _connector(source_id: str):
    source = SOURCES[source_id](scheduled=True)
    if source_id == zh.SOURCE_ID:
        return source, zh.ZhCantonRoadworksConnector(source, "ua", client=_client(ZH_FEED), clock=lambda: NOW)
    if source_id == city.SOURCE_ID:
        return source, city.ZurichCityWorksConnector(source, "ua", client=_client(CITY_FEED), clock=lambda: NOW)
    if source_id == sz.SOURCE_ID:
        return source, sz.SzCantonRoadworksConnector(source, "ua", client=_client(SZ_LV95, "text/xml"), clock=lambda: NOW)
    return source, ge.GeInfomobiliteWorksConnector(source, "ua", client=_client(GE_FEED), clock=lambda: NOW)


@pytest.mark.parametrize("source_id", SOURCES)
def test_works_become_located_events_awaiting_validation(session, source_id):
    source, connector = _connector(source_id)
    SourceRepository(session).sync_registry([source])
    session.commit()
    result = run_ingestion(connector, KeywordClassifier.from_file(), SqlIngestionStore(session), None, SWITZERLAND)
    session.commit()
    events = list(session.scalars(select(Event).where(Event.source_id == source.source_id)))
    assert result.events_created == len(events) > 0
    assert all(event.geometry and event.status == "VALIDATION_REQUIRED" for event in events)
    assert all(event.start_time and event.end_time for event in events)
