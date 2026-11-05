"""The Taiwanese, New Zealand and Italian feeds approved on 5 November 2026, on
real excerpts of what each served that day:

- Taichung same-day road excavation information: 18 rows of 12 permits (JSON);
- New Plymouth District Council corridor access requests: 29 features of 18
  CARs from the point, line and area layers (GeoJSON). Long CARs are cut:
  E1177045 keeps 4 of its 369 points, E1204084 2 of 76, E1204695 3 of 16;
  2663452 and 2479666 are in their warranty period, which the live query
  leaves out;
- South Tyrol traffic reports: 14 of 111 RoadWorksAndLocks reports and 10 of
  28 CurrentSituation reports (GeoJSON), four of them copies of works messages.

Taichung's officers, phone numbers and the people named as customers,
applicants or contractor are replaced by placeholders ("[承辦人]", "[電話]",
"[姓名]"). New Plymouth's and South Tyrol's layers name no person (their
"Creator"/"Editor" is the council's GIS account). No test reaches a service."""

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy import String, select

from app.models import Event, Source
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from connectors.base import ConnectorError
from connectors.official import new_plymouth_car as np_car
from connectors.official import south_tyrol_traffic as bz
from connectors.official import taichung_excavation as tc
from packages.cities import get_city
from packages.event_schema import EventType
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass, SourceType, TermsStatus
from services.extraction import KeywordClassifier
from services.ingestion import run_ingestion

FIXTURES = Path(__file__).parents[1] / "fixtures"
TAICHUNG_ROWS = json.loads((FIXTURES / "taichung_road_excavation_2026-11-05.json").read_text(encoding="utf-8"))
NEW_PLYMOUTH = json.loads((FIXTURES / "new_plymouth_car_2026-11-05.json").read_text(encoding="utf-8"))["layers"]
SOUTH_TYROL = json.loads((FIXTURES / "south_tyrol_traffic_2026-11-05.json").read_text(encoding="utf-8"))
# 12:00 in Taipei, 17:00 in New Plymouth, 05:00 in Bolzano.
NOW = datetime(2026, 11, 5, 4, 0, tzinfo=timezone.utc)
TAIPEI = timezone(timedelta(hours=8))
NZDT, NZST = timezone(timedelta(hours=13)), timezone(timedelta(hours=12))
CET, CEST = timezone(timedelta(hours=1)), timezone(timedelta(hours=2))

DEFINITIONS = [
    (tc.taichung_excavation_source, "taichung", "TW", "zh", 60),
    (np_car.new_plymouth_source, "new-zealand", "NZ", "en", 360),
    (bz.south_tyrol_source, "italy", "IT", "it", 60),
]


# --- the three definitions ---------------------------------------------------------------


@pytest.mark.parametrize(("make", "city", "country", "language", "minutes"), DEFINITIONS)
def test_each_source_is_an_official_located_feed_recorded_as_permitted_with_attribution(
    make, city, country, language, minutes
):
    definition = make(scheduled=False)
    assert (definition.city, definition.country, definition.language) == (city, country, language)
    assert get_city(city).country == country
    assert definition.source_tier == 1 and definition.source_type is SourceType.API
    assert definition.source_class is SourceClass.GOVERNMENT_OPEN_DATA
    assert definition.integration_status is IntegrationStatus.CONNECTED and definition.active is False
    assert make(scheduled=True).active is True
    assert definition.terms_status is TermsStatus.PERMITS_TESTING and definition.terms_reviewed is False
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    assert definition.polling_frequency_minutes == minutes
    assert definition.provides_geometry and definition.licence and definition.attribution
    assert definition.evidence_retention and "5 November 2026" in definition.notes
    assert EventType.ROAD_WORKS.value in definition.events_supported
    limits = {
        column.name: column.type.length
        for column in Source.__table__.columns
        if isinstance(column.type, String) and column.type.length
    }
    values = definition.model_dump(mode="json")
    assert all(len(str(values[name])) <= limit for name, limit in limits.items() if values.get(name) is not None)


def test_the_licences_and_credits_are_the_sources_own():
    taichung = tc.taichung_excavation_source(scheduled=False)
    assert taichung.source_id == "taichung-road-excavation-today"
    assert "Open Government Data License" in taichung.licence and "臺中市政府建設局" in taichung.attribution
    assert "rid=d5adb71a-00bb-4573-b67e-ffdccfc7cd27" in taichung.endpoint
    new_plymouth = np_car.new_plymouth_source(scheduled=False)
    assert new_plymouth.source_id == "nz-new-plymouth-corridor-access"
    assert "CC BY 4.0" in new_plymouth.licence and "New Plymouth District Council (NPDC)" in new_plymouth.attribution
    south_tyrol = bz.south_tyrol_source(scheduled=False)
    assert south_tyrol.source_id == "it-south-tyrol-traffic-reports"
    assert "CC0 1.0" in south_tyrol.licence and "Protezione civile" in south_tyrol.attribution


# --- Taichung ------------------------------------------------------------------------------


def _taichung():
    return {item["application"]: tc.to_record(item, NOW) for item in tc.permits(TAICHUNG_ROWS)}


def _taichung_connector(body=None) -> tc.TaichungRoadExcavationConnector:
    payload = TAICHUNG_ROWS if body is None else body

    def answer(request):
        assert request.url.params["rid"] == "d5adb71a-00bb-4573-b67e-ffdccfc7cd27"
        return httpx.Response(200, json=payload)

    client = httpx.Client(transport=httpx.MockTransport(answer))
    return tc.TaichungRoadExcavationConnector(
        tc.taichung_excavation_source(scheduled=True), "ua", client=client, clock=lambda: NOW
    )


def test_taichung_keeps_one_record_per_permit_and_leaves_out_pavement_only_and_unlocated_permits():
    records = _taichung()
    assert len(records) == 12
    # Every site on the pavement (人行道); and one site with neither a point nor an area.
    assert sorted(number for number, record in records.items() if record is None) == ["115A10629", "115I14543"]
    kept = [record for record in records.values() if record is not None]
    assert len(kept) == 10 and all(record.structured.event_type == EventType.ROAD_WORKS.value for record in kept)
    # Two of its four sites are on the pavement, two are not: the permit is kept.
    gas = records["113A19728"]
    assert gas.external_id == "113A19728"
    assert gas.title == "Road excavation (新增建築用戶申裝 / 瓦斯): 北屯區榮德一路距敦和路19m處(B點) and 3 more sites (Taichung)"
    assert gas.structured.category == "道路挖掘 / 新增建築用戶申裝 / 瓦斯"


def test_taichung_permits_are_whole_days_in_taipei_time_and_say_whether_works_have_started():
    records = _taichung()
    planned = records["115H12811"].structured
    assert planned.start == datetime(2026, 9, 18, 0, 0, tzinfo=TAIPEI)
    assert planned.end == datetime(2026, 12, 17, 23, 59, 59, tzinfo=TAIPEI)
    assert planned.stated_period == "核准施工 1150918 – 1151217（民國紀年）"
    # A connection permit approved from June 2023 to August 2027 (ROC 112 to 116).
    assert records["112B09217"].structured.start == datetime(2023, 6, 8, 0, 0, tzinfo=TAIPEI)
    assert records["112B09217"].structured.end == datetime(2027, 8, 1, 23, 59, 59, tzinfo=TAIPEI)
    started = {number for number, record in records.items() if record and record.structured.status == "已開工"}
    assert started == {"115A15103", "115D15782"}
    assert records["115H12811"].structured.status == "尚未開工"


def test_taichung_works_area_is_every_sites_area_longitude_first():
    records = _taichung()
    gas = records["113A19728"].structured
    assert gas.geometry["type"] == "MultiPolygon" and len(gas.geometry["coordinates"]) == 4
    assert [location.name for location in gas.locations][:2] == [
        "北屯區榮德一路距敦和路19m處(B點)",
        "北屯區榮德一路距敦和路19m處(人行道)(B點)",
    ]
    assert all(location.geometry["type"] == "Polygon" for location in gas.locations)
    single = records["115D15782"].structured
    assert single.geometry["type"] == "Polygon" and len(single.locations) == 1
    for record in filter(None, records.values()):
        position = record.structured.geometry["coordinates"][0][0]
        position = position[0] if isinstance(position[0], list) else position
        longitude, latitude = position
        assert 120.4 < longitude < 121.5 and 23.9 < latitude < 24.5
        assert get_city("taichung").covers(latitude, longitude)


def test_taichung_drops_officers_phones_people_and_customers_names():
    records = _taichung()
    evidence = json.dumps([record.raw for record in records.values() if record], ensure_ascii=False)
    for word in ("承辦人", "承辦人電話", "廠商電話", "[承辦人]", "[電話]", "[姓名]"):
        assert word not in evidence
    rows = {item["application"]: item["rows"][0] for item in tc.permits(TAICHUNG_ROWS)}
    # A person as applicant, and as applicant and contractor: not kept.
    assert "申請單位" not in rows["115F09789"] and "申請單位" not in rows["115F13928"]
    assert "廠商名稱" not in rows["115F13928"]
    # A company's two-character short name cannot be told from a person's: not kept either.
    assert "廠商名稱" not in rows["113A19728"]
    assert rows["115H12811"]["廠商名稱"] == "高明營造股份有限公司"
    # Customers' orders are masked; public works programmes keep their names.
    for number in ("112B09217", "113A19728", "115A04378", "115F12708", "115F09789", "115A15103"):
        assert rows[number]["工程名稱"] == tc.MASKED
    assert rows["115H12811"]["工程名稱"] == "南屯區萬和路一段等汰換管線工程"
    assert rows["114F21782"]["工程名稱"] == "114年度臺中市共同管道維修及維護工程"  # a city office's case
    assert records["115H12811"].summary.startswith("南屯區萬和路一段等汰換管線工程。")
    assert records["112B09217"].title == "Road excavation (一般用戶申裝 / 電信): 西區美村路一段69號旁 (Taichung)"


def test_taichung_a_works_name_that_carries_a_person_is_masked_even_in_a_public_works_case():
    row = next(row for row in TAICHUNG_ROWS if row["申請書編號"] == "115H12811")
    assert tc.keeps_works_name(row)
    for name in ("南屯區萬和路一段等汰換管線工程 王O明", "汰換管線工程（負責人：某甲）", "陳先生用戶管線"):
        assert not tc.keeps_works_name({**row, "工程名稱": name})
    customer = {**row, "案件類別": "一般用戶申裝", "申請單位": "台灣電力股份有限公司台中區營業處"}
    assert not tc.keeps_works_name(customer)
    assert tc.keeps_works_name({**customer, "申請單位": "臺中市政府交通局(運輸設施科)"})


def test_taichung_fetch_keeps_permits_in_force_and_refuses_what_is_not_the_dataset():
    connector = _taichung_connector()
    kept = connector.fetch()
    assert len(connector.observed_ids) == 10 and len(kept) == 10
    assert {record.external_id for record in kept} >= {"113A19728", "115H12811", "112B09217"}
    for bad in ({"rows": []}, [{"id": 1, "name": "not this dataset"}]):
        with pytest.raises(ConnectorError):
            _taichung_connector(bad).fetch()


# --- New Plymouth ----------------------------------------------------------------------


def _layers(layers=NEW_PLYMOUTH):
    return {int(layer): collection["features"] for layer, collection in layers.items()}


def _new_plymouth():
    return {item["car"]: np_car.to_record(item, NOW) for item in np_car.cars(_layers())}


def _new_plymouth_connector(layers=NEW_PLYMOUTH, asked=None) -> np_car.NewPlymouthCorridorAccessConnector:
    def answer(request):
        layer = request.url.path.split("/")[-2]
        if asked is not None:
            asked.append((layer, request.url.params["where"], request.url.params["outSR"]))
        return httpx.Response(200, json=layers[layer])

    client = httpx.Client(transport=httpx.MockTransport(answer))
    return np_car.NewPlymouthCorridorAccessConnector(
        np_car.new_plymouth_source(scheduled=True), "ua", client=client, clock=lambda: NOW
    )


def test_new_plymouth_keeps_one_record_per_car_across_its_layers_and_parts():
    items = {item["car"]: item for item in np_car.cars(_layers())}
    assert len(items) == 18
    # A line and an area in two layers: one CAR, drawn by its area.
    two_layers = items["2663452"]
    assert sorted(part["layer"] for part in two_layers["parts"]) == [np_car.LINES, np_car.AREAS]
    record = np_car.to_record(two_layers, NOW)
    area = next(f["geometry"] for f in NEW_PLYMOUTH["4"]["features"] if f["properties"]["CAR_ID"] == "2663452")
    assert record.structured.geometry == area
    # Four point features, three of them the same point: two parts, shown at one point.
    points = items["E1177045"]
    assert len(points["parts"]) == 2
    many = np_car.to_record(points, NOW)
    assert many.structured.geometry["type"] == "Point"
    assert many.structured.geometry in [part["geometry"] for part in points["parts"]]
    assert "Mapped at 2 points; shown at one of them" in many.summary
    # Five points, four the same: shown at the first in coordinate order (New Plymouth, not the
    # KiwiRail site near Palmerston North).
    assert _new_plymouth()["E1184479"].structured.geometry["coordinates"] == [174.169435999505, -39.0423949992488]


def test_new_plymouth_leaves_out_cars_off_the_carriageway_or_declined():
    records = _new_plymouth()
    assert sorted(car for car, record in records.items() if record is None) == ["E1196737", "E1204084"]
    assert not np_car.on_carriageway({"LocationInRoad": "Berm, Footpath, Nature Strip"})
    assert np_car.on_carriageway({"LocationInRoad": "Footpath, Carriageway"})
    assert np_car.on_carriageway({"LocationInRoad": None})  # events state none: kept


def test_new_plymouth_event_types_follow_the_request_and_the_road_closure():
    records = _new_plymouth()
    types = {car: record.structured.event_type for car, record in records.items() if record}
    assert types["E1202802"] == EventType.PUBLIC_PROCESSION.value
    assert types["E1204695"] == EventType.SPORTING_EVENT.value
    assert types["E1192550"] == types["E1192608"] == EventType.SPECIAL_EVENT.value
    assert types["R1199652"] == types["R1205803"] == EventType.PLANNED_ROAD_CLOSURE.value
    assert types["R1155350"] == types["2876568"] == EventType.ROAD_WORKS.value
    parade = records["E1202802"]
    assert parade.external_id == "CAR:E1202802"
    assert parade.title == "Parade: Ariki Street, New Plymouth (New Plymouth District)"
    assert parade.structured.geometry["type"] == "MultiLineString"
    assert parade.structured.locations[0].closure == "Road closure required"
    closure = records["R1199652"]
    assert closure.title == "Road works with road closure: Blagdon Road, New Plymouth (New Plymouth District)"
    assert closure.structured.status == "CAR Approval / On-hold"


def test_new_plymouth_dates_are_whole_days_in_new_zealand_time_from_the_work_dates():
    records = _new_plymouth()
    # Completion not yet known: the period ends with the estimated completion.
    closure = records["R1199652"].structured
    assert closure.start == datetime(2026, 11, 8, 0, 0, tzinfo=NZDT)
    assert closure.end == datetime(2026, 11, 19, 23, 59, 59, tzinfo=NZDT)
    assert closure.stated_period == (
        "work start 2026-11-08 (proposed); work completion not stated (unknown); estimated 2026-11-15 – 2026-11-19"
    )
    # A revised completion wins over the estimate; winter start (NZST), summer end (NZDT).
    works = records["R1155350"].structured
    assert works.start == datetime(2026, 3, 1, 0, 0, tzinfo=NZDT)
    assert works.end == datetime(2027, 1, 30, 23, 59, 59, tzinfo=NZDT)
    assert records["E1184479"].structured.start == datetime(2026, 7, 31, 0, 0, tzinfo=NZST)
    # Completed work is reported ended by the source.
    assert records["R1205849"].structured.reported_ended and records["2663452"].structured.reported_ended
    assert not works.reported_ended


def test_new_plymouth_keeps_no_account_bookkeeping_or_possible_persons_name():
    records = _new_plymouth()
    evidence = json.dumps([record.raw for record in records.values() if record])
    for word in ("Creator", "Editor", "NPDC.GeoHUB", "OBJECTID", "CreationDate", "EditDate", "Shape__Length"):
        assert word not in evidence
    for word in ("Private Party", '"private"', "Waitara Alive", "omexom"):
        assert word not in evidence
    items = {item["car"]: item["properties"] for item in np_car.cars(_layers())}
    assert items["E1167524"]["PrincipalOrganisation"] is None  # "Private Party"
    assert items["R1206182"]["PrincipalOrganisation"] is None  # "private"
    assert items["2479666"]["UtilityOperatorOrganisation"] == "POWERCO LIMITED"  # "omexom, POWERCO LIMITED"
    assert items["R1195126"]["PrincipalOrganisation"] == "NZ Transport Agency"
    assert np_car.stored_properties({"WorkDescription": "Call 027 123 4567"})["WorkDescription"] is None


def test_new_plymouth_fetch_asks_for_open_cars_of_the_three_layers_and_keeps_those_in_force_or_coming():
    asked: list = []
    connector = _new_plymouth_connector(asked=asked)
    kept = connector.fetch()
    assert sorted(layer for layer, _, _ in asked) == ["2", "3", "4"]
    assert all(where == np_car.WHERE and srs == "4326" for _, where, srs in asked)
    assert len(connector.observed_ids) == 16
    # Ended: the completed work of 29 October and the two CARs in warranty.
    assert {"CAR:R1205849", "CAR:2663452", "CAR:2479666"}.isdisjoint(record.external_id for record in kept)
    assert len(kept) == 13
    broken = {**NEW_PLYMOUTH, "3": {"error": {"code": 400, "message": "Invalid query"}}}
    with pytest.raises(ConnectorError):
        _new_plymouth_connector(broken).fetch()


# --- South Tyrol -----------------------------------------------------------------------


def _south_tyrol_client(feed=SOUTH_TYROL) -> httpx.Client:
    def answer(request):
        assert request.url.params["srsName"] == "EPSG:4326" and request.url.params["version"] == "2.0.0"
        return httpx.Response(200, json=feed[request.url.params["typeNames"].split("TrafficReport-")[1]])

    return httpx.Client(transport=httpx.MockTransport(answer))


def _south_tyrol_connector(feed=SOUTH_TYROL) -> bz.SouthTyrolTrafficReportsConnector:
    return bz.SouthTyrolTrafficReportsConnector(
        bz.south_tyrol_source(scheduled=True), "ua", client=_south_tyrol_client(feed), clock=lambda: NOW
    )


def _south_tyrol():
    reports = bz.fetch_reports("ua", client=_south_tyrol_client())
    return reports, {bz.message_number(report["properties"]): bz.to_record(report, NOW) for report in reports}


def test_south_tyrol_two_layers_are_one_source_one_record_per_message():
    reports, _ = _south_tyrol()
    assert len(reports) == 20  # 14 works + 10 current, 4 of them copies of works messages
    layers = [report["layer"] for report in reports]
    assert layers.count(bz.WORKS_LAYER) == 14 and layers.count(bz.CURRENT_LAYER) == 6
    merano = next(r for r in reports if bz.message_number(r["properties"]) == "31558")
    assert merano["layer"] == bz.WORKS_LAYER and merano["properties"]["MESSAGE_ID"] == 3155812
    assert bz.message_number({"MESSAGE_ID": 3155801, "TYPE_ID": 1}) == "31558"
    assert bz.message_number({"MESSAGE_ID": 3155801, "TYPE_ID": 7}) == "3155801"  # not the pattern: kept whole


def test_south_tyrol_keeps_works_closures_and_events_and_leaves_out_queues_and_other_notices():
    reports, records = _south_tyrol()
    left_out = {
        report["properties"]["TIPO_SUBCODE"]
        for report in reports
        if records[bz.message_number(report["properties"])] is None
    }
    assert left_out == {"STAU", "ÖFFENTLICHE VERKEHRSMITTEL", "VORSICHT"}
    kept = {number: record for number, record in records.items() if record}
    assert len(kept) == 16
    assert kept["31558"].structured.event_type == EventType.PLANNED_ROAD_CLOSURE.value
    assert kept["27849"].structured.event_type == EventType.ROAD_WORKS.value
    assert kept["27096"].structured.event_type == EventType.SPECIAL_EVENT.value  # only in CurrentSituation
    assert kept["31558"].external_id == "message:31558"
    assert kept["31558"].title == "Road closure: Variante di Merano (LS/SP185), Burgraviato (South Tyrol)"
    assert "CHIUSURA" in kept["31558"].summary and "SPERRE" in kept["31558"].summary


def test_south_tyrol_days_are_whole_days_in_italian_time_and_a_missing_end_stays_empty():
    _, records = _south_tyrol()
    merano = records["31558"].structured
    assert merano.start == datetime(2026, 11, 2, 0, 0, tzinfo=CET)
    assert merano.end == datetime(2026, 11, 6, 23, 59, 59, tzinfo=CET)
    assert merano.stated_period == "2026-11-02 – 2026-11-06"
    weather = records["31385"].structured
    assert weather.start == datetime(2026, 9, 2, 0, 0, tzinfo=CEST) and weather.end is None
    assert weather.stated_period == "2026-09-02 – no end stated"
    assert sorted(n for n, r in records.items() if r and r.structured.end is None) == ["27209", "31119", "31385"]


def test_south_tyrol_points_are_longitude_first_and_a_swapped_feed_is_refused():
    _, records = _south_tyrol()
    for record in filter(None, records.values()):
        longitude, latitude = record.structured.geometry["coordinates"]
        assert 10.3 < longitude < 12.6 and 45.8 < latitude < 47.1
    assert records["31558"].structured.geometry == {"type": "Point", "coordinates": [11.1437, 46.6719]}
    swapped = copy.deepcopy(SOUTH_TYROL)
    point = swapped["RoadWorksAndLocks"]["features"][0]["geometry"]
    point["coordinates"] = point["coordinates"][::-1]
    with pytest.raises(ConnectorError, match="latitude-longitude"):
        _south_tyrol_connector(swapped).fetch()
    cut = copy.deepcopy(SOUTH_TYROL)
    cut["CurrentSituation"]["numberMatched"] = 99
    with pytest.raises(ConnectorError):
        _south_tyrol_connector(cut).fetch()


def test_south_tyrol_the_servers_date_and_row_ids_are_not_content():
    reports, _ = _south_tyrol()
    assert all("CURRENT_DATE" not in r["properties"] and "ID" not in r["properties"] and "id" not in r for r in reports)
    tomorrow = copy.deepcopy(SOUTH_TYROL)
    for layer in tomorrow.values():
        for number, feature in enumerate(layer["features"]):
            feature["properties"]["CURRENT_DATE"] = "2026-11-06Z"
            feature["properties"]["ID"] = 9000 + number
            feature["id"] = f"TrafficReport.{9000 + number}"
    first = {record.external_id: record.content_hash for record in _south_tyrol_connector().fetch()}
    again = {record.external_id: record.content_hash for record in _south_tyrol_connector(tomorrow).fetch()}
    assert first == again


def test_south_tyrol_fetch_keeps_reports_in_force_or_coming():
    connector = _south_tyrol_connector()
    kept = connector.fetch()
    assert len(connector.observed_ids) == 16 and len(kept) == 16
    coming = [record for record in kept if record.structured.start > NOW]
    assert len(coming) == 8


# --- ingestion -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("make", "connect", "city"),
    [
        (tc.taichung_excavation_source, _taichung_connector, "taichung"),
        (np_car.new_plymouth_source, _new_plymouth_connector, "new-zealand"),
        (bz.south_tyrol_source, _south_tyrol_connector, "italy"),
    ],
)
def test_records_become_located_events_awaiting_validation(session, make, connect, city):
    source = make(scheduled=True)
    SourceRepository(session).sync_registry([source])
    session.commit()
    result = run_ingestion(connect(), KeywordClassifier.from_file(), SqlIngestionStore(session), None, get_city(city))
    session.commit()
    events = list(session.scalars(select(Event).where(Event.source_id == source.source_id)))
    assert result.events_created == len(events) > 0
    assert all(event.geometry and event.status == "VALIDATION_REQUIRED" for event in events)
    assert all(event.start_time for event in events)
