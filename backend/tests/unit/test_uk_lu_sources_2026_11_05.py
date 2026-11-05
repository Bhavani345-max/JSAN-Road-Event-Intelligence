"""The sources approved on 5 November 2026 for England and Luxembourg, and the
British National Grid conversion the first needs.

- National Highways' planned roadworks (connectors/official/national_highways.py),
  on a real excerpt of the weekly file of 2 November 2026 (20 of its 1,793 works
  phases, among them one event number listed twice, an embargo, an abnormal
  load and an off-network notice) and of the data.gov.uk dataset page that
  links the weekly files (read 5 November 2026);
- CITA's current and future works (connectors/official/cita_roadworks.py), on
  real excerpts of chantierActuelDatex.xml (12 of 150 situations) and
  chantierFuturDatex.xml (7 of 61), fetched 5 November 2026, 13:30 CET;
- OSGB36 to WGS 84 (connectors/official/osgb36.py), against the worked
  examples of the Ordnance Survey's "A Guide to Coordinate Systems in Great
  Britain" (v3.6, 2020), annexes B, C and D.

No test reaches the network.
"""

import copy
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy import String, select

from app.models import Event, Source
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from connectors.base import ConnectorError
from connectors.official import cita_roadworks as cita
from connectors.official import national_highways as nh
from connectors.official import osgb36
from packages.cities import get_city
from packages.event_schema import EventDirection, EventType
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass, TermsStatus
from services.extraction import KeywordClassifier
from services.ingestion import run_ingestion

FIXTURES = Path(__file__).parents[1] / "fixtures"
NH_PAGE = (FIXTURES / "national_highways_dataset_page_2026-11-05.html").read_text(encoding="utf-8")
NH_FILE = (FIXTURES / "national_highways_roadworks_2026-11-05.xml").read_bytes()
NH_NEWEST = nh.FILE_BASE + "nh_roadworks_2026_2_11.xml"
CITA_CURRENT = (FIXTURES / "cita_chantiers_actuels_datex22_2026-11-05.xml").read_bytes()
CITA_FUTURE = (FIXTURES / "cita_chantiers_futurs_datex22_2026-11-05.xml").read_bytes()
# Thursday 5 November 2026, 12:00 in London; 13:40 in Luxembourg.
NH_NOW = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
CITA_NOW = datetime(2026, 11, 5, 12, 40, tzinfo=timezone.utc)
GMT, BST = timedelta(0), timedelta(hours=1)
CET, CEST = timezone(timedelta(hours=1)), timezone(timedelta(hours=2))


def _dms(degrees: int, minutes: int, seconds: float) -> float:
    return degrees + minutes / 60 + seconds / 3600


def _metres_apart(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((phi2 - phi1) / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6_371_008.8 * math.asin(math.sqrt(h))


def _fits_the_sources_table(definition) -> bool:
    limits = {
        column.name: column.type.length
        for column in Source.__table__.columns
        if isinstance(column.type, String) and column.type.length
    }
    values = definition.model_dump(mode="json")
    return all(len(str(values[name])) <= limit for name, limit in limits.items() if values.get(name) is not None)


# --- OSGB36 to WGS 84: the Ordnance Survey's worked examples ----------------------------

# GRS 80, the ellipsoid of the guide's annex B examples (ETRS89).
GRS80_A = 6_378_137.0
GRS80_E2 = (1 / 298.257222101) * (2 - 1 / 298.257222101)
# Annex B.1/B.2 and D: one point in ETRS89, as latitude, longitude, height and as cartesian coordinates.
ETRS89_LAT, ETRS89_LON, ETRS89_HEIGHT = _dms(53, 36, 43.1653), -_dms(1, 39, 51.9920), 299.800
ETRS89_XYZ = (3790644.900, -110149.210, 5111482.970)
# Annex D: the same point in OSGB36, after the table 4 Helmert transformation.
OSGB36_XYZ = (3790269.549, -110038.064, 5111050.261)
OSGB36_LAT, OSGB36_LON, OSGB36_HEIGHT = _dms(53, 36, 42.2972), -_dms(1, 39, 46.5416), 249.950
OSGB36_GRID = (422297.792, 412878.741)


def test_the_inverse_projection_reproduces_annex_c_within_a_millimetre():
    latitude, longitude = osgb36.grid_to_osgb36(651409.903, 313177.270)
    found = (math.degrees(longitude), math.degrees(latitude))
    assert _metres_apart(*found, _dms(1, 43, 4.5177), _dms(52, 39, 27.2531)) < 0.001
    # Annex D's grid position: within its published values' rounding (0.0001″ is 3 mm).
    latitude, longitude = osgb36.grid_to_osgb36(*OSGB36_GRID)
    assert _metres_apart(math.degrees(longitude), math.degrees(latitude), OSGB36_LON, OSGB36_LAT) < 0.005


def test_the_cartesian_conversions_reproduce_annex_b_both_ways():
    xyz = osgb36.to_cartesian(
        math.radians(ETRS89_LAT), math.radians(ETRS89_LON), ETRS89_HEIGHT, a=GRS80_A, e2=GRS80_E2
    )
    assert all(abs(found - expected) < 0.001 for found, expected in zip(xyz, ETRS89_XYZ))
    latitude, longitude, height = osgb36.from_cartesian(*ETRS89_XYZ, a=GRS80_A, e2=GRS80_E2)
    assert _metres_apart(math.degrees(longitude), math.degrees(latitude), ETRS89_LON, ETRS89_LAT) < 0.001
    assert abs(height - ETRS89_HEIGHT) < 0.001


def test_the_helmert_transformation_reproduces_annex_d_and_reverses_within_two_centimetres():
    assert osgb36.HELMERT_FROM_WGS84 == {
        "tx": -446.448, "ty": 125.157, "tz": -542.060, "s_ppm": 20.4894,
        "rx": -0.1502, "ry": -0.2470, "rz": -0.8421,
    }  # fmt: skip
    assert osgb36.HELMERT_TO_WGS84 == {name: -value for name, value in osgb36.HELMERT_FROM_WGS84.items()}
    xyz = osgb36.helmert(*ETRS89_XYZ, osgb36.HELMERT_FROM_WGS84)
    assert all(abs(found - expected) < 0.001 for found, expected in zip(xyz, OSGB36_XYZ))
    latitude, longitude, height = osgb36.from_cartesian(*OSGB36_XYZ, a=osgb36._AIRY_A, e2=osgb36._AIRY_E2)
    # Within the published values' rounding (0.0001″ is 3 mm).
    assert _metres_apart(math.degrees(longitude), math.degrees(latitude), OSGB36_LON, OSGB36_LAT) < 0.005
    assert abs(height - OSGB36_HEIGHT) < 0.001
    # The other way, with the signs reversed (section 6.2): the reversal's own error is about a centimetre.
    back = osgb36.helmert(*OSGB36_XYZ, osgb36.HELMERT_TO_WGS84)
    assert math.dist(back, ETRS89_XYZ) < 0.02


def test_a_grid_position_comes_back_to_the_wgs84_position_it_was_projected_from():
    # Annex D's grid position, converted the whole way (projection, height 0, Helmert,
    # WGS 84): within 10 cm of the ETRS89 position it came from. What is left is the
    # Helmert's own error against the real OSGB36 (up to about 3 m, the guide says).
    longitude, latitude = osgb36.to_lon_lat(*OSGB36_GRID)
    assert _metres_apart(longitude, latitude, ETRS89_LON, ETRS89_LAT) < 0.10
    # The datum change moves a point about a hundred metres: it is applied, not skipped.
    assert _metres_apart(longitude, latitude, OSGB36_LON, OSGB36_LAT) > 50


def test_values_that_are_not_a_grid_position_give_no_point():
    for easting, northing in (("", ""), (None, None), ("abc", "172523"), (0, 0), (-5, 172523), (800_000, 172523), ("nan", "nan")):
        assert osgb36.point(easting, northing) is None
    assert osgb36.point("505838", "172523") == {"type": "Point", "coordinates": list(osgb36.to_lon_lat(505838, 172523))}


# --- National Highways ------------------------------------------------------------------


def _nh_items():
    return nh.once_each(nh.works_items(NH_FILE, NH_NEWEST))


def _nh_records():
    return {item["NEW_EVENT_NUMBER"]: nh.to_record(item, NH_NOW) for item in _nh_items()}


def _nh_connector(handler) -> nh.NationalHighwaysRoadworksConnector:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return nh.NationalHighwaysRoadworksConnector(
        nh.national_highways_source(scheduled=True), "ua", client=client, clock=lambda: NH_NOW
    )


def _nh_site(requested: list[str], *, page_status: int = 200, files: dict[str, bytes] | None = None):
    files = {NH_NEWEST: NH_FILE} if files is None else files

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        requested.append(url)
        if url == nh.DATASET_PAGE:
            return httpx.Response(page_status, text=NH_PAGE if page_status == 200 else "")
        if url in files:
            return httpx.Response(200, content=files[url])
        return httpx.Response(403, text="AccessDenied")

    return handler


def test_national_highways_is_an_official_located_feed_recorded_as_permitted_with_attribution():
    definition = nh.national_highways_source(scheduled=False)
    assert definition.source_id == nh.SOURCE_ID == "gb-national-highways-roadworks"
    assert (definition.city, definition.country, definition.region, definition.language) == ("united-kingdom", "GB", "England", "en")
    assert get_city(definition.city).timezone == "Europe/London" == str(nh.LONDON)
    assert definition.source_tier == 1 and definition.source_class is SourceClass.GOVERNMENT_OPEN_DATA
    assert definition.integration_status is IntegrationStatus.CONNECTED and definition.active is False
    assert nh.national_highways_source(scheduled=True).active is True
    assert definition.terms_status is TermsStatus.PERMITS_TESTING and definition.terms_reviewed is False
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    assert "Open Government Licence" in definition.licence and "Open Government Licence v3.0" in definition.attribution
    assert definition.polling_frequency_minutes == 24 * 60 and definition.provides_geometry
    assert "1,793" in definition.notes and "1,777" in definition.notes
    assert "ckan.publishing.service.gov.uk" not in (definition.endpoint + definition.source_url)
    assert _fits_the_sources_table(definition)


def test_the_newest_weekly_file_is_found_from_the_dataset_pages_links():
    assert nh.newest_file(NH_PAGE) == (NH_NEWEST, date(2026, 11, 2))
    # The file names give day then month, not zero-padded; the 2023 file named
    # nh_roadworks_2023_3_6.xml is the one its link calls "6 March 2023".
    assert nh.file_for(date(2026, 11, 2)) == NH_NEWEST
    assert nh.file_for(date(2026, 10, 26)).endswith("/nh_roadworks_2026_26_10.xml")
    older = NH_PAGE.replace(NH_NEWEST, "https://example.org/nh_roadworks_2026_2_11.xml")
    assert nh.newest_file(older) == (nh.FILE_BASE + "nh_roadworks_2026_26_10.xml", date(2026, 10, 26))
    with pytest.raises(ConnectorError):
        nh.newest_file("<html><a href='https://example.org/nh_roadworks_2026_2_11.xml'>x</a></html>")
    assert nh.recent_mondays(date(2026, 11, 5)) == [date(2026, 11, 2), date(2026, 10, 26), date(2026, 10, 19), date(2026, 10, 12)]
    assert nh.recent_mondays(date(2026, 11, 2))[0] == date(2026, 11, 2)


def test_when_the_page_cannot_be_read_the_last_mondays_files_are_tried_newest_first():
    requested: list[str] = []
    fallback = nh.file_for(date(2026, 10, 26))
    connector = _nh_connector(_nh_site(requested, page_status=404, files={fallback: NH_FILE}))
    assert connector.fetch() and connector.file_url == fallback
    assert requested == [nh.DATASET_PAGE, NH_NEWEST, fallback]
    nowhere: list[str] = []
    with pytest.raises(ConnectorError, match="No National Highways roadworks file"):
        _nh_connector(_nh_site(nowhere, page_status=404, files={})).fetch()
    assert len(nowhere) == 1 + nh.FALLBACK_MONDAYS


def test_each_phase_is_one_record_with_its_number_title_roads_and_point():
    records = _nh_records()
    assert len(records) == 19  # 20 listed, one event number twice
    lanes = records["00442700-001"]
    assert lanes.external_id == "00442700-001"
    assert lanes.title == "Programmed Routine Works: A30 Eastbound Staines Bypass to London Road (National Highways)"
    assert lanes.summary == (
        "A30 Eastbound Staines Bypass to London Road\nLane closure for routine maintenance works\n"
        "Expected delay: Slight (less than 10 mins)"
    )
    assert lanes.structured.affected_road == "A30" and lanes.structured.severity == "Slight (less than 10 mins)"
    assert lanes.structured.status == "Published" and lanes.structured.direction is None
    assert records["00389408-001"].structured.direction == EventDirection.BOTH_DIRECTIONS.value
    assert records["00527846-001"] is None  # its roads are kept only with a kept phase
    many = records["00530572-001"].structured
    assert many.affected_road == "A2; A20; A2070; A21; A23; A249; A259; A26; A27; M2; M20; M23"
    country = get_city("united-kingdom")
    for item in _nh_items():
        record = records[item["NEW_EVENT_NUMBER"]]
        if record is None:
            continue
        geometry = record.structured.geometry
        assert geometry == osgb36.point(item["CENTRE_EASTING"], item["CENTRE_NORTHING"])
        assert geometry["type"] == "Point" and country.covers(geometry["coordinates"][1], geometry["coordinates"][0])
        assert record.structured.locations[0].geometry == geometry and record.structured.covers_city


def test_times_are_uk_local_time_summer_and_winter():
    records = _nh_records()
    summer = records["00389408-001"].structured  # 24-JUL-2024 12:00 to 26-AUG-2027 05:00
    assert summer.start.utcoffset() == BST and summer.start.astimezone(timezone.utc) == datetime(2024, 7, 24, 11, 0, tzinfo=timezone.utc)
    assert summer.end.utcoffset() == BST and summer.end.astimezone(timezone.utc) == datetime(2027, 8, 26, 4, 0, tzinfo=timezone.utc)
    winter = records["00442700-001"].structured  # 13-NOV-2026 09:30 to 16:00
    assert winter.start.utcoffset() == GMT and winter.start.astimezone(timezone.utc) == datetime(2026, 11, 13, 9, 30, tzinfo=timezone.utc)
    across = records["00517735-001"].structured  # 17-AUG-2026 07:00 to 28-NOV-2026 05:00
    assert (across.start.utcoffset(), across.end.utcoffset()) == (BST, GMT)
    assert records["00389408-001"].published_at == datetime(2024, 7, 24, 10, 0, 45, tzinfo=timezone.utc)
    assert nh.stated_time("31-FEB-2026 10:00") is None and nh.stated_time("2026-11-02 10:00") is None


def test_the_type_comes_from_the_kind_of_works_and_the_descriptions_words():
    types = {number: record.structured.event_type for number, record in _nh_records().items() if record}
    assert types == {
        "00389408-001": EventType.LANE_RESTRICTION.value,  # narrow lanes (a layby closure closes no road)
        "00442700-001": EventType.LANE_RESTRICTION.value,  # lane closure
        "00458159-001": EventType.LANE_RESTRICTION.value,
        "00519831-001": EventType.TRAFFIC_DIVERSION.value,  # Diversion/Alternate Route
        "00507208-002": EventType.TRAFFIC_DIVERSION.value,
        "00517735-001": EventType.LANE_RESTRICTION.value,  # Traffic Incidents: lane closure
        "00497839-006": EventType.EMERGENCY_ROAD_CLOSURE.value,  # Emergency Routine Works, carriageway closures
        "00531105-001": EventType.PLANNED_ROAD_CLOSURE.value,  # road closure (for a bonfire pageant)
        "00530681-001": EventType.LANE_RESTRICTION.value,  # emergency works, lane closures only
        "00531140-001": EventType.LANE_RESTRICTION.value,  # traffic signals
        "00526685-001": EventType.TRAFFIC_DIVERSION.value,
        "00530572-001": EventType.LANE_RESTRICTION.value,
        "00531074-002": EventType.PLANNED_ROAD_CLOSURE.value,  # exit slip closed
        "00470409-002": EventType.PLANNED_ROAD_CLOSURE.value,  # carriageway closure
        "00517564-001": EventType.PLANNED_ROAD_CLOSURE.value,
        "00513807-004": EventType.PLANNED_ROAD_CLOSURE.value,  # slip road and lane closure
    }
    assert _nh_records()["00497839-006"].structured.category == "Emergency Routine Works / Carriageway and lane closures"


@pytest.mark.parametrize(
    "kind, description, expected",
    [
        # Wordings from the weekly file of 2 November 2026.
        ("Programmed Routine Works", "M20 Westbound Jct 2 to Jct 1\r\nLane and slip road closure for technology asset works", EventType.PLANNED_ROAD_CLOSURE),
        ("Area Schemes", "M20 both directions Jct 6 to Jct 5\r\nCarriageway, slip road and laneclosure for electrical works", EventType.PLANNED_ROAD_CLOSURE),
        ("Programmed Routine Works", "A20 eastbound Aycliff to Eastern Roundabout, Lane closure for maintenance works.", EventType.LANE_RESTRICTION),
        ("Emergency Routine Works", "A45 clockwise M42 Jct 6 roundabout (Bickenhill Interchange).\r\nPartial carriageway closure for maintenance works.", EventType.LANE_RESTRICTION),
        ("Regional Technology Schemes", "A36 both directions Plaitford. 2-way signals for traffic signal renewal.", EventType.LANE_RESTRICTION),
        ("Programmed Routine Works", "M5 Jct 28 to 29 hardshoulder closure in both directions for parapet works", EventType.LANE_RESTRICTION),
        ("Programmed Street/Road Works", "A500 Queensway A50 \r\nDiversion Route only for off network road closure on behalf of Network Rail. ", EventType.TRAFFIC_DIVERSION),
        ("Programmed Routine Works", "A34 both directions Botley to Islip\r\nSpeed reduction for maintenance", EventType.ROAD_WORKS),
        ("Programmed Routine Works", "A1 southbound Denwick to Alnwick\r\n24hr layby closure for drainage works", EventType.ROAD_WORKS),
        ("Emergency Routine Works", "A66 eastbound Little Burdon to Long Newton \r\nCarriageway closure for carriageway repair", EventType.EMERGENCY_ROAD_CLOSURE),
    ],
)
def test_closure_and_lane_words_are_read_as_the_source_writes_them(kind, description, expected):
    closures, lanes = nh.measures(description)
    text = " ".join(nh._lines(description))
    assert nh.event_type(kind, closures, lanes, text) == expected.value


def test_embargoes_abnormal_loads_and_off_network_notices_are_not_road_events():
    records = _nh_records()
    left_out = {number for number, record in records.items() if record is None}
    assert left_out == {"00507423-001", "00527846-001", "00490844-001"}
    kinds = {item["NEW_EVENT_NUMBER"]: item["CLOSURE_TYPE"] for item in _nh_items()}
    assert {kinds[number] for number in left_out} == {"Embargo", "Abnormal Load Movements", "Off Network"}
    no_position = {**_nh_items()[1], "CENTRE_EASTING": "", "CENTRE_NORTHING": None}
    assert nh.to_record(no_position, NH_NOW) is None


def test_an_event_number_listed_twice_is_kept_once_as_last_published():
    listed = nh.works_items(NH_FILE, NH_NEWEST)
    twice = [item for item in listed if item["NEW_EVENT_NUMBER"] == "00507208-002"]
    assert len(listed) == 20 and len(twice) == 2
    kept = [item for item in nh.once_each(listed) if item["NEW_EVENT_NUMBER"] == "00507208-002"]
    assert [item["PUBLISHED_DATE"] for item in kept] == ["2026-10-07T13:41:18"]


def test_fetch_reads_the_newest_file_and_keeps_phases_in_force_or_to_come():
    requested: list[str] = []
    connector = _nh_connector(_nh_site(requested))
    kept = connector.fetch()
    assert requested == [nh.DATASET_PAGE, NH_NEWEST] and connector.file_url == NH_NEWEST
    assert connector.counts == {"listed": 20, "listed_twice": 1, "not_road_events": 3, "kept": 16}
    assert len(connector.observed_ids) == 16
    # Ended by noon on 5 November: the night works of 2-3 and 3-4 November.
    assert {"00530681-001", "00513807-004"} <= connector.observed_ids
    assert {record.external_id for record in kept} == connector.observed_ids - {"00530681-001", "00513807-004"}
    assert all(record.structured.end >= NH_NOW for record in kept)
    with pytest.raises(ConnectorError):
        _nh_connector(_nh_site([], files={NH_NEWEST: b"<Report xmlns='WebTeam'/>"})).fetch()
    with pytest.raises(ConnectorError):
        _nh_connector(_nh_site([], files={NH_NEWEST: b"<html>not xml"})).fetch()


def test_a_republished_but_unchanged_phase_is_not_a_revision():
    item = _nh_items()[0]
    record = nh.to_record(item, NH_NOW)
    again = nh.to_record({**item, "PUBLISHED_DATE": "2026-11-01T09:00:00"}, NH_NOW)
    later = nh.to_record({**item, "EDATE": "27-AUG-2027 05:00"}, NH_NOW)
    key = nh.NationalHighwaysRoadworksConnector.revision_key
    assert key(record.raw) == key(again.raw) != key(later.raw)


def test_national_highways_phases_become_located_events_awaiting_validation(session):
    source = nh.national_highways_source(scheduled=True)
    SourceRepository(session).sync_registry([source])
    session.commit()
    connector = _nh_connector(_nh_site([]))
    result = run_ingestion(connector, KeywordClassifier.from_file(), SqlIngestionStore(session), None, get_city("united-kingdom"))
    session.commit()
    events = list(session.scalars(select(Event).where(Event.source_id == source.source_id)))
    assert result.events_created == len(events) > 0
    assert all(event.geometry and event.status == "VALIDATION_REQUIRED" for event in events)
    assert all(event.start_time and event.end_time for event in events)


# --- CITA current and future works ------------------------------------------------------


def _stages(body: bytes = CITA_CURRENT) -> list[dict]:
    return cita.read_works(body, cita.CURRENT_WORKS)[0]


def _cita_records() -> dict:
    items = _stages(CITA_CURRENT) + _stages(CITA_FUTURE)
    return {item["id"]: cita.to_record(item, CITA_NOW) for item in items}


def _cita_connector(current: bytes = CITA_CURRENT, future: bytes = CITA_FUTURE, requested: list | None = None):
    files = {cita.CURRENT_WORKS: current, cita.FUTURE_WORKS: future}

    def handler(request: httpx.Request) -> httpx.Response:
        if requested is not None:
            requested.append(str(request.url))
        return httpx.Response(200, content=files[str(request.url)], headers={"content-type": "text/xml"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return cita.CitaRoadworksConnector(cita.cita_roadworks_source(scheduled=True), "ua", client=client, clock=lambda: CITA_NOW)


def test_cita_works_is_an_official_located_feed_with_its_own_id():
    definition = cita.cita_roadworks_source(scheduled=False)
    assert definition.source_id == cita.SOURCE_ID == "lu-cita-roadworks-datex2" != "lu-cita-datex2-v36"
    assert (definition.city, definition.country, definition.language) == ("luxembourg", "LU", "fr")
    assert get_city(definition.city).timezone == "Europe/Luxembourg"
    assert definition.source_tier == 1 and definition.source_class is SourceClass.GOVERNMENT_OPEN_DATA
    assert definition.integration_status is IntegrationStatus.CONNECTED and definition.active is False
    assert cita.cita_roadworks_source(scheduled=True).active is True
    assert definition.terms_status is TermsStatus.PERMITS_TESTING
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    assert "CC0" in definition.licence and "CITA" in definition.attribution
    assert definition.polling_frequency_minutes == 60 and definition.provides_geometry
    assert cita.ENDPOINTS == (
        "https://www.cita.lu/info_trafic/datex/chantierActuelDatex.xml",
        "https://www.cita.lu/info_trafic/datex/chantierFuturDatex.xml",
    )
    assert "318 stages" in definition.notes
    assert _fits_the_sources_table(definition)


def test_records_with_one_id_are_one_stage_of_several_sections():
    items, counts = cita.read_works(CITA_CURRENT, cita.CURRENT_WORKS)
    assert counts == {"situations": 12, "records": 36, "not_real": 0} and len(items) == 29
    assert len(_stages(CITA_FUTURE)) == 15
    stage = next(item for item in items if item["id"] == "73515-105351")
    assert stage["situation"] == "73515" and [part["type"] for part in stage["parts"]] == [
        "GeneralNetworkManagement", "GeneralNetworkManagement", "MaintenanceWorks",
    ]  # fmt: skip
    record = _cita_records()["73515-105351"]
    assert record.external_id == "73515-105351"
    assert record.title == "Lanes partially obstructed (temporary traffic lights) – CR125 / CR119 (CITA)"
    assert record.structured.affected_road == "CR125; CR119"
    assert record.structured.event_type == EventType.LANE_RESTRICTION.value
    # Three sections: the lights on CR125 and CR119, the works on CR119 (its own two points).
    assert [location.name for location in record.structured.locations] == [
        "From: CR125", "To: CR125", "From: CR119", "To: CR119", "From: CR119", "To: CR119",
    ]  # fmt: skip
    assert len({tuple(location.geometry["coordinates"]) for location in record.structured.locations}) == 6
    assert record.summary.splitlines()[0] == "chausse rtrcie, feux tricolores lumineux"  # as published, without accents
    assert "GeneralNetworkManagement / temporaryTrafficLights" in record.categories


def test_times_keep_their_stated_offsets():
    records = _cita_records()
    long_closure = records["34246-39941"].structured
    assert long_closure.start == datetime(2020, 5, 29, 0, 0, tzinfo=CEST) and long_closure.start.utcoffset() == timedelta(hours=2)
    assert long_closure.end == datetime(2029, 5, 29, 18, 0, tzinfo=CEST)
    night = records["73641-105651"].structured  # future works, winter time
    assert night.start == datetime(2026, 11, 9, 21, 0, tzinfo=CET) and night.start.utcoffset() == timedelta(hours=1)
    assert night.end == datetime(2026, 11, 10, 4, 0, tzinfo=CET)
    assert records["34246-39941"].published_at == datetime(2024, 4, 26, 13, 49, 5, tzinfo=CEST)


def test_the_event_is_at_the_start_of_its_leading_measures_section():
    records = _cita_records()
    # The file lists the section's `to` point before its `from` point: the event is at `from`.
    closure = records["34246-39941"].structured
    assert closure.geometry == {"type": "Point", "coordinates": [6.291867835775066, 49.69184807503533]}
    assert [location.kind for location in closure.locations] == ["section start", "section end"]
    assert closure.locations[1].geometry["coordinates"] == [6.304287120879002, 49.714263979573154]
    # A speed limit section comes first in the file; the closure (on S1-L) leads.
    mixed = records["67292-93839"]
    assert mixed.structured.geometry["coordinates"] == [5.898642273227638, 49.55505882605114]
    assert mixed.title == "Road closed – S1-L / A13P-S / A13S-P: Construction OA1451 (CITA)"
    luxembourg = get_city("luxembourg")
    for record in records.values():
        longitude, latitude = record.structured.geometry["coordinates"]
        assert luxembourg.covers(latitude, longitude)


def test_the_type_comes_from_the_stages_codes():
    records = _cita_records()
    assert records["34246-39941"].structured.event_type == EventType.PLANNED_ROAD_CLOSURE.value  # roadBlocked
    assert records["73670-105713"].structured.event_type == EventType.LANE_RESTRICTION.value  # lanesBlocked
    assert records["66329-92190"].structured.event_type == EventType.ROAD_WORKS.value  # works, no constriction
    speed = records["66329-92192"]
    assert speed.structured.event_type is None and speed.title == "Speed limit 90 km/h – A1T-G: Phase 2+3 (CITA)"
    urgent = copy.deepcopy(next(item for item in _stages() if item["id"] == "34246-39941"))
    urgent["parts"][0]["urgent"] = "true"
    assert cita.to_record(urgent, CITA_NOW).structured.event_type == EventType.EMERGENCY_ROAD_CLOSURE.value
    assert records["73918-106119"].structured.direction == EventDirection.BOTH_DIRECTIONS.value  # every section bothWays
    assert records["73515-105351"].structured.direction is None  # one section's direction unknown


def test_a_default_stage_title_is_left_out_of_the_title_and_a_named_one_kept():
    records = _cita_records()
    assert records["34246-39941"].title == "Road closed – CR129 (CITA)"  # "Titre:Nouvelle tape"
    assert records["34246-39941"].raw["item"]["title"] == "Nouvelle tape"
    assert records["73670-105711"].title == "Road closed – CR364: Haupeschfest 2026 (CITA)"
    assert records["74015-106261"].title == "Road closed – N10: Barrage de la Place du March (CITA)"
    no_comment = records["73554-105452"]
    assert no_comment.title == "Lanes partially obstructed – N7 (CITA)" and "title" not in no_comment.raw["item"]


def test_a_comment_line_naming_a_contact_is_not_kept():
    body = CITA_CURRENT.replace(
        b"<value>C,2. Except bus scolaire.</value>",
        b"<value>C,2. Except bus scolaire.\nContact chantier: 621 123 456, chef@example.lu</value>",
    )
    assert body != CITA_CURRENT
    record = cita.to_record(next(item for item in _stages(body) if item["id"] == "34246-39941"), CITA_NOW)
    evidence = json.dumps(record.raw, ensure_ascii=False)
    assert "621 123 456" not in evidence and "chef@example.lu" not in evidence
    assert "C,2. Except bus scolaire." in record.summary


def test_situations_that_are_not_real_and_stages_without_a_position_are_not_taken():
    exercise = CITA_FUTURE.replace(b"<informationStatus>real</informationStatus>", b"<informationStatus>test</informationStatus>", 1)
    items, counts = cita.read_works(exercise, cita.FUTURE_WORKS)
    assert counts["not_real"] == 1 and len(items) == 15 - 3  # the Haupeschfest's three stages
    stage = copy.deepcopy(next(item for item in _stages() if item["id"] == "34246-39941"))
    for part in stage["parts"]:
        part.pop("from"), part.pop("to")
    assert cita.to_record(stage, CITA_NOW) is None
    with pytest.raises(ConnectorError):
        cita.read_works(b"<d2LogicalModel><situation", cita.CURRENT_WORKS)


def test_fetch_reads_both_files_and_keeps_stages_in_force_or_to_come():
    requested: list[str] = []
    connector = _cita_connector(requested=requested)
    kept = connector.fetch()
    assert requested == list(cita.ENDPOINTS)
    assert connector.counts == {"situations": 19, "records": 55, "not_real": 0, "stages": 44, "listed_twice": 0, "kept": 44}
    assert len(connector.observed_ids) == 44
    ended = {"69456-97573", "66329-92433", "74015-106260", "74015-106261", "72951-104273", "72951-104450", "73676-105730", "73676-105832"}
    assert ended <= connector.observed_ids
    assert {record.external_id for record in kept} == connector.observed_ids - ended
    assert all(record.structured.end >= CITA_NOW for record in kept)
    # A stage in both files is taken once, from the current works.
    twice = _cita_connector(future=CITA_CURRENT)
    twice.fetch()
    assert twice.counts["listed_twice"] == 29 and twice.counts["stages"] == 29


def test_a_new_version_of_an_unchanged_stage_is_not_a_revision_but_a_new_end_is():
    def key(body: bytes) -> str:
        record = cita.to_record(next(item for item in _stages(body) if item["id"] == "34246-39941"), CITA_NOW)
        return cita.CitaRoadworksConnector.revision_key(record.raw)

    first = key(CITA_CURRENT)
    touched = CITA_CURRENT.replace(b'<situation id="34246" version="645753">', b'<situation id="34246" version="645999">')
    touched = touched.replace(
        b"<situationRecordVersionTime>2024-04-26T13:49:05+02:00</situationRecordVersionTime>",
        b"<situationRecordVersionTime>2026-11-05T13:00:00+01:00</situationRecordVersionTime>",
    )
    assert touched != CITA_CURRENT and key(touched) == first
    later = CITA_CURRENT.replace(b"<overallEndTime>2029-05-29T18:00:00+02:00</overallEndTime>", b"<overallEndTime>2029-06-29T18:00:00+02:00</overallEndTime>")
    assert later != CITA_CURRENT and key(later) != first


def test_cita_works_become_located_events_awaiting_validation(session):
    source = cita.cita_roadworks_source(scheduled=True)
    SourceRepository(session).sync_registry([source])
    session.commit()
    result = run_ingestion(_cita_connector(), KeywordClassifier.from_file(), SqlIngestionStore(session), None, get_city("luxembourg"))
    session.commit()
    events = list(session.scalars(select(Event).where(Event.source_id == source.source_id)))
    assert result.events_created == len(events) > 0
    assert all(event.geometry and event.status == "VALIDATION_REQUIRED" for event in events)
    assert all(event.start_time and event.end_time for event in events)
