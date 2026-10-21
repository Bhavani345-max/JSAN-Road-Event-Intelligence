"""Spain's official feeds (decision 0034): DGT's national DATEX II 3.7 incidents,
Barcelona's works in public space, Madrid's Informo incidents and the Basque
Country's traffic incidences, on real responses saved 21 October 2026.
No test reaches any of the services."""

import json
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest
from pydantic import TypeAdapter
from sqlalchemy import String, select

from app.models import Event, Source
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from connectors.official import barcelona, euskadi, madrid, spain_dgt
from connectors.official.bison_fute import same_situation_key
from packages.cities import area_of, country_entry, get_city
from packages.event_schema import EventDirection, EventType
from packages.geo_models import Geometry, positions_of
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass, TermsStatus
from services.extraction import KeywordClassifier
from services.extraction.source_event import build_event_from_source, classify_source_record
from services.ingestion import run_ingestion

FIXTURES = Path(__file__).parents[1] / "fixtures"
DGT_XML = (FIXTURES / "spain_dgt_datex2_v37_2026-10-21.xml").read_text(encoding="utf-8")
BARCELONA = json.loads((FIXTURES / "barcelona_obres_2026-10-21.json").read_text(encoding="utf-8"))
MADRID_XML = (FIXTURES / "madrid_informo_incidents_2026-10-21.xml").read_bytes()
EUSKADI = json.loads((FIXTURES / "euskadi_traffic_incidences_2026-10-21.json").read_text(encoding="utf-8"))
NOW = datetime(2026, 10, 21, 11, 21, tzinfo=timezone.utc)
MADRID_TIME = ZoneInfo("Europe/Madrid")
SPAIN, BCN, MAD = get_city("spain"), get_city("barcelona"), get_city("madrid")


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _dgt_records():
    records, observed = spain_dgt.read_situations(DGT_XML, NOW)
    return {record.external_id: record for record in records}, observed


# --- the area ---------------------------------------------------------------------------


def test_spain_is_a_country_entry_holding_barcelona_and_madrid_without_the_canaries():
    assert (SPAIN.level, SPAIN.country, SPAIN.timezone) == ("country", "ES", "Europe/Madrid")
    assert country_entry(BCN) == SPAIN and country_entry(MAD) == SPAIN
    assert {city.id for city in area_of(SPAIN)} >= {"spain", "barcelona", "madrid"}
    # Mainland, the Balearic Islands, Ceuta and Melilla are in; the Canary Islands
    # (another time zone) are left out on purpose.
    for latitude, longitude in ((43.36, -8.41), (36.01, -5.61), (39.57, 2.65), (39.89, 4.27), (35.89, -5.32), (35.29, -2.94)):
        assert SPAIN.covers(latitude, longitude)
    assert not SPAIN.covers(28.12, -15.43) and not SPAIN.covers(28.46, -16.25)
    assert BCN.covers(41.3851, 2.1734) and not BCN.covers(40.4168, -3.7038)
    assert MAD.covers(40.4168, -3.7038) and not MAD.covers(41.3851, 2.1734)


@pytest.mark.parametrize(
    "make, city_id",
    [
        (spain_dgt.dgt_source, "spain"),
        (barcelona.barcelona_source, "barcelona"),
        (madrid.madrid_source, "madrid"),
        (euskadi.euskadi_source, "spain"),
    ],
)
def test_each_source_is_an_official_located_feed_run_by_hand(make, city_id):
    definition = make(scheduled=False)
    assert definition.city == city_id and definition.country == "ES"
    assert definition.source_tier == 1 and definition.source_class is SourceClass.GOVERNMENT_OPEN_DATA
    assert definition.integration_status is IntegrationStatus.CONNECTED and definition.active is False
    assert make(scheduled=True).active is True
    assert definition.provides_geometry and definition.licence and definition.attribution
    assert definition.terms_status is TermsStatus.PERMITS_TESTING and definition.terms_reviewed is False
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    assert definition.source_id in get_city(city_id).official_sources
    # PostgreSQL enforces the sources table's column lengths (SQLite does not).
    limits = {
        column.name: column.type.length
        for column in Source.__table__.columns
        if isinstance(column.type, String) and column.type.length
    }
    values = definition.model_dump(mode="json")
    assert all(len(str(values[name])) <= limit for name, limit in limits.items() if values.get(name) is not None)


# --- DGT --------------------------------------------------------------------------------


def test_dgt_types_come_from_the_datex_record_and_its_cause():
    records, _ = _dgt_records()
    assert records["3343801:5684393"].structured.event_type == EventType.PLANNED_ROAD_CLOSURE.value
    assert "roadClosed / roadMaintenance" in records["3343801:5684393"].structured.category
    # A closure for anything but road maintenance is not planned.
    assert records["13054089:16676270"].structured.event_type == EventType.EMERGENCY_ROAD_CLOSURE.value
    assert records["24889776:29251933"].structured.event_type == EventType.EMERGENCY_ROAD_CLOSURE.value
    assert records["2816645:18811074"].structured.event_type == EventType.LANE_RESTRICTION.value
    assert records["24767997:29125538"].structured.event_type == EventType.LANE_RESTRICTION.value
    assert records["15975858:21845258"].structured.event_type == EventType.ROAD_WORKS.value
    assert records["17513389:21451455"].structured.event_type == EventType.ROAD_WORKS.value  # works speed limit
    assert records["24872009:29233572"].structured.event_type == EventType.ACCIDENT.value
    assert records["24810583:29168878"].structured.event_type == EventType.FLOODING.value
    assert records["24891836:29254330"].structured.event_type == EventType.ROAD_HAZARD.value
    assert records["24825603:29184859"].structured.event_type == EventType.ROAD_HAZARD.value  # rain
    # "other / other" keeps its codes with no type.
    assert records["18367717:24713337"].structured.event_type is None
    assert records["18367717:24713337"].title.startswith("Weight restriction in operation: A-372")
    # Traffic-flow records (AbnormalTraffic: slow traffic) are not taken.
    assert all("AbnormalTraffic" not in record.structured.category for record in records.values())
    assert "AbnormalTraffic" in DGT_XML


def test_dgt_section_is_placed_at_its_from_point_with_both_points_kept():
    records, _ = _dgt_records()
    record = records["2816645:18811074"]
    # <loc:from> 39.993732, -3.6074991 (km 37.1); <loc:to> 39.994446, -3.6054852 (km 37.3).
    assert record.structured.geometry == {"type": "Point", "coordinates": [-3.6074991, 39.993732]}
    assert [location.name for location in record.structured.locations] == [
        "From: N-400 km 37.1, Ontígola (Toledo)",
        "To: N-400 km 37.3, Ontígola (Toledo)",
    ]
    assert record.structured.locations[1].geometry == {"type": "Point", "coordinates": [-3.6054852, 39.994446]}
    assert record.title == "Narrow lanes (roadworks): N-400 km 37.1–37.3, Ontígola (Toledo)"
    assert record.structured.affected_road == "N-400"
    assert record.structured.direction == EventDirection.BOTH_DIRECTIONS.value  # tpegDirectionRoad both
    # Nothing is drawn between the two points.
    assert all(location.geometry["type"] == "Point" for location in record.structured.locations)
    # A point location gives one point.
    point = records["13054089:16676270"]
    assert len(point.structured.locations) == 1 and point.structured.locations[0].kind == "point"


def test_dgt_times_keep_their_offsets_and_directions_are_only_stated_ones():
    records, _ = _dgt_records()
    works = records["15975858:21845258"].structured
    # 07:00 and 18:00 at +02:00.
    assert works.start == datetime(2026, 10, 21, 5, 0, tzinfo=timezone.utc)
    assert works.end == datetime(2026, 10, 21, 16, 0, tzinfo=timezone.utc)
    assert records["2816645:18811074"].structured.end is None  # no overallEndTime
    assert records["13514422:21045344"].structured.direction == EventDirection.WESTBOUND.value
    # An intercardinal direction is not a compass statement REI has: kept as words only.
    intercardinal = records["15975858:21845258"].structured
    assert intercardinal.direction is None and "north east bound" in intercardinal.locations[0].direction
    assert records["3343801:5684393"].structured.severity is None
    assert records["13054089:16676270"].structured.severity == "highest"
    # The speed limit is quoted as stated, without a unit.
    assert "Temporary speed limit stated:" in records["17513389:21451455"].summary


def test_dgt_canary_records_are_kept_as_evidence_but_outside_spains_area():
    records, _ = _dgt_records()
    canary = records["15945609:19767518"]  # GC-606, Tejeda (Las Palmas)
    assert canary.structured.geometry["coordinates"][1] < 29
    assert not classify_source_record(canary, SPAIN).is_relevant
    mainland = records["24890837:29253456"]  # AP-9, Ordes (A Coruña)
    assert classify_source_record(mainland, SPAIN).is_relevant


def test_dgt_fetch_keeps_records_in_force_and_reports_what_it_lists():
    body = DGT_XML
    connector = spain_dgt.SpainDgtIncidentsConnector(
        spain_dgt.dgt_source(scheduled=False),
        "ua",
        client=_client(lambda request: httpx.Response(200, text=body)),
        clock=lambda: NOW,
    )
    kept = connector.fetch()
    listed, _ = _dgt_records()
    assert connector.observed_ids == set(listed)
    ended = {"23736303:28029007", "23736303:28029008"}  # 21 September, 15:43-19:00
    assert ended <= set(listed) and not ended & {record.external_id for record in kept}
    assert all(record.structured.start for record in kept)
    assert all(record.structured.end is None or record.structured.end >= NOW for record in kept)


def test_dgt_ids_are_situation_and_record_so_records_of_a_situation_can_be_grouped():
    records, _ = _dgt_records()
    north, south = records["18284064:22276757"], records["18284064:22276758"]
    events = [
        build_event_from_source(record, classify_source_record(record, SPAIN), now=NOW, city=SPAIN)
        for record in (north, south)
    ]
    keys = [same_situation_key(event, record.external_id) for event, record in zip(events, (north, south))]
    assert all(keys) and keys[0] != keys[1]  # same situation, different spots


def test_dgt_refuses_what_is_not_a_datex_payload():
    from connectors.base import ConnectorError

    with pytest.raises(ConnectorError):
        spain_dgt.read_situations("<html>maintenance</html>", NOW)
    with pytest.raises(ConnectorError):
        spain_dgt.read_situations("not xml", NOW)


# --- Barcelona ------------------------------------------------------------------------------


def test_wkt_shapes_are_read_as_written():
    assert barcelona.wkt_geometry("POINT (2.17 41.38)") == {"type": "Point", "coordinates": [2.17, 41.38]}
    assert barcelona.wkt_geometry("POLYGON ((2.1 41.3, 2.2 41.3, 2.2 41.4, 2.1 41.3))") == {
        "type": "Polygon",
        "coordinates": [[[2.1, 41.3], [2.2, 41.3], [2.2, 41.4], [2.1, 41.3]]],
    }
    multi = barcelona.wkt_geometry(
        "MULTIPOLYGON (((2.1 41.3, 2.2 41.3, 2.2 41.4, 2.1 41.3)), ((2.0 41.0, 2.01 41.0, 2.01 41.01, 2.0 41.0)))"
    )
    assert multi["type"] == "MultiPolygon" and len(multi["coordinates"]) == 2
    assert barcelona.wkt_geometry("LINESTRING Z (2.1 41.3 5, 2.2 41.4 6)") == {
        "type": "LineString",
        "coordinates": [[2.1, 41.3], [2.2, 41.4]],
    }
    # Nothing is repaired or guessed.
    assert barcelona.wkt_geometry("POLYGON ((2.1 41.3, 2.2 41.3, 2.2 41.4, 2.15 41.35))") is None  # not closed
    assert barcelona.wkt_geometry("POLYGON EMPTY") is None
    assert barcelona.wkt_geometry("GEOMETRYCOLLECTION (POINT (2 41))") is None
    assert barcelona.wkt_geometry("") is None and barcelona.wkt_geometry(None) is None


def _barcelona_records():
    works = barcelona.group_works(BARCELONA["result"]["records"])
    return works, {record.external_id: record for work in works if (record := barcelona.to_record(work, NOW))}


def test_barcelona_rows_of_one_work_are_one_record_with_its_neighbourhoods():
    works, records = _barcelona_records()
    rows = BARCELONA["result"]["records"]
    several = next(work for work in works if len(work["rows"]) >= 3 and work["codi"] in records)
    record = records[several["codi"]]
    assert sum(1 for row in rows if row["codi"] == several["codi"]) == len(several["rows"])
    for row in several["rows"]:
        assert barcelona.clean(row["nom_barri"]) in record.summary
    assert record.structured.geometry == barcelona.wkt_geometry(several["rows"][0]["geometria_wgs84"])
    assert len({work["codi"] for work in works}) == len(works) < len(rows)


def test_barcelona_days_are_whole_days_in_madrid_time_and_finished_works_say_so():
    works, records = _barcelona_records()
    for work in works:
        record = records.get(work["codi"])
        if record is None:
            continue
        row = work["rows"][0]
        first, last = date.fromisoformat(row["data_inici"][:10]), date.fromisoformat(row["data_fi"][:10])
        assert record.structured.start == datetime(first.year, first.month, first.day, tzinfo=MADRID_TIME)
        assert record.structured.end == datetime(last.year, last.month, last.day, 23, 59, 59, tzinfo=MADRID_TIME)
        assert record.structured.reported_ended is (row["estat"] == "Finalitzada")
        assert record.structured.status == row["estat"]
        kind = row["tipusobra"]
        expected = EventType.ROAD_WORKS.value if kind in barcelona.ROAD_WORKS else None
        assert record.structured.event_type == expected
        shape = TypeAdapter(Geometry).validate_python(record.structured.geometry)
        assert all(BCN.covers(latitude, longitude) for longitude, latitude in positions_of(shape))
    # A work with no site is not taken.
    unlocated = [work for work in works if not work["rows"][0]["geometria_wgs84"]]
    assert unlocated and all(work["codi"] not in records for work in unlocated)
    assert {"Edificació", "Serveis"} <= {work["rows"][0]["tipusobra"] for work in works}


def test_barcelona_reads_every_page_and_a_reload_is_not_a_revision():
    rows = BARCELONA["result"]["records"]
    seen_offsets = []

    def handler(request):
        offset = int(request.url.params["offset"])
        seen_offsets.append(offset)
        assert request.url.params["resource_id"] == barcelona.RESOURCE_ID
        assert "geometria_etrs89" not in request.url.params["fields"]
        page = rows[offset : offset + 20]
        return httpx.Response(200, json={"success": True, "result": {"records": page, "total": len(rows)}})

    original = barcelona.PAGE_SIZE
    barcelona.PAGE_SIZE = 20
    try:
        connector = barcelona.BarcelonaWorksConnector(
            barcelona.barcelona_source(scheduled=False), "ua", client=_client(handler), clock=lambda: NOW
        )
        kept = connector.fetch()
    finally:
        barcelona.PAGE_SIZE = original
    assert seen_offsets == [0, 20]
    _, records = _barcelona_records()
    assert connector.observed_ids == set(records)
    assert kept and all(record.structured.end >= NOW for record in kept)
    # The datastore renumbers its rows on a reload: not a change of the work.
    raw = kept[0].raw
    renumbered = json.loads(json.dumps(raw))
    for row in renumbered["item"]["rows"]:
        row["_id"] = int(row["_id"]) + 5000
    assert barcelona.BarcelonaWorksConnector.revision_key(raw) == barcelona.BarcelonaWorksConnector.revision_key(renumbered)
    renumbered["item"]["rows"][0]["data_fi"] = "2030-01-01T00:00:00"
    assert barcelona.BarcelonaWorksConnector.revision_key(raw) != barcelona.BarcelonaWorksConnector.revision_key(renumbered)


# --- Madrid -----------------------------------------------------------------------------------


def _madrid_connector():
    body = MADRID_XML
    return madrid.MadridInformoConnector(
        madrid.madrid_source(scheduled=False),
        "ua",
        client=_client(lambda request: httpx.Response(200, content=body, headers={"content-type": "application/xml"})),
        clock=lambda: NOW,
    )


def test_madrid_reads_the_file_with_its_byte_order_mark_and_madrid_times():
    assert MADRID_XML.startswith(b"\xef\xbb\xbf")
    connector = _madrid_connector()
    kept = connector.fetch()
    assert len(connector.observed_ids) == MADRID_XML.count(b"<Incidencia>") and kept
    record = next(record for record in kept if record.external_id == "45659")
    # fh_inicio 2026-09-28T08:30:00.0000000, fh_final 2026-11-28T18:30:00.0000000 (Madrid).
    assert record.structured.start == datetime(2026, 9, 28, 6, 30, tzinfo=timezone.utc)
    assert record.structured.end == datetime(2026, 11, 28, 17, 30, tzinfo=timezone.utc)
    assert record.structured.event_type == EventType.ROAD_WORKS.value
    assert record.structured.geometry["type"] == "Point" and MAD.covers(*reversed(record.structured.geometry["coordinates"]))
    assert record.title.startswith("Road works (Obras en la vía): Obras en Calle Jardín de la Duquesa")
    # Ended incidents (most of the file) are not kept.
    assert all(record.structured.end >= NOW for record in kept)
    assert len(kept) < len(connector.observed_ids)


def test_madrid_type_comes_from_the_code_and_flags_not_the_description():
    kept = {record.external_id: record for record in _madrid_connector().fetch()}
    lanes = kept["44873"]  # LCS, Carriles cortados
    assert lanes.structured.event_type == EventType.LANE_RESTRICTION.value
    assert lanes.structured.category == "LCS / Carriles cortados"
    # A description saying "corte de la circulación" does not make a closure type.
    works = kept["45192"]
    assert "corte de la circulación" in works.summary
    assert works.structured.event_type == EventType.ROAD_WORKS.value
    item = {"id_incidencia": "1", "cod_tipo_incidencia": "XYZ", "nom_tipo_incidencia": "Otro", "es_obras": "N",
            "es_accidente": "N", "latitud": "40.42", "longitud": "-3.70", "fh_inicio": "2026-10-21T10:00:00.0000000",
            "fh_final": "2026-10-21T12:00:00.0000000"}  # fmt: skip
    assert madrid.to_record(item, NOW).structured.event_type is None
    assert madrid.to_record({**item, "es_accidente": "S"}, NOW).structured.event_type == EventType.ACCIDENT.value
    assert madrid.to_record({**item, "latitud": ""}, NOW) is None


# --- Euskadi ----------------------------------------------------------------------------------


def _euskadi_connector(clock=lambda: NOW, requests=None):
    items = EUSKADI["incidences"]
    half = (len(items) + 1) // 2
    pages = {"1": items[:half], "2": items[half:]}

    def handler(request):
        if requests is not None:
            requests.append(request.url)
        page = request.url.params["_page"]
        return httpx.Response(
            200,
            json={"totalItems": len(items), "totalPages": 2, "currentPage": int(page), "incidences": pages[page]},
        )

    return euskadi.EuskadiTrafficIncidencesConnector(
        euskadi.euskadi_source(scheduled=False), "ua", client=_client(handler), clock=clock
    )


def test_euskadi_reads_todays_list_in_madrid_time_page_by_page():
    requests = []
    _euskadi_connector(requests=requests).fetch()
    assert [url.path for url in requests] == ["/traffic/v1.0/incidences/byDate/2026/10/21"] * 2
    assert [url.params["_page"] for url in requests] == ["1", "2"]
    # 22:30 UTC on 21 October is already 22 October in Madrid.
    requests.clear()
    _euskadi_connector(clock=lambda: datetime(2026, 10, 21, 22, 30, tzinfo=timezone.utc), requests=requests).fetch()
    assert requests[0].path.endswith("/byDate/2026/10/22")


def test_euskadi_ids_are_per_administration_and_types_read_whatever_the_spelling():
    connector = _euskadi_connector()
    kept = {record.external_id: record for record in connector.fetch()}
    # Incidence 1683 is a Bilbao record and a Donostia record.
    assert {"5-1683", "7-1683"} <= set(kept)
    assert not hasattr(connector, "observed_ids")  # absence from the day's list is not an end
    by_type = {}
    for item in EUSKADI["incidences"]:
        record = euskadi.to_record(item, NOW)
        by_type.setdefault(item.get("incidenceType"), set()).add(record.structured.event_type if record else "not taken")
    assert by_type["Obras"] == by_type["Obra"] == by_type["Mantenimiento"] == {EventType.ROAD_WORKS.value}
    assert by_type["Accidente"] == {EventType.ACCIDENT.value}
    assert by_type["Seguridad vial"] == {EventType.ROAD_HAZARD.value}
    assert by_type[None] == {None} and by_type["Otros"] == {None}
    # A closure to pedestrians only is not taken.
    pedestrian = next(item for item in EUSKADI["incidences"] if item.get("incidenceName") == "CORTE DE TRAFICO PEATONAL")
    assert euskadi.to_record(pedestrian, NOW) is None
    assert euskadi.to_record({**EUSKADI["incidences"][0], "incidenceType": "Retención"}, NOW) is None


def test_euskadi_times_are_madrid_time_as_written_and_no_end_is_invented():
    records = {
        record.external_id: record
        for item in EUSKADI["incidences"]
        if (record := euskadi.to_record(item, NOW)) is not None
    }
    region_wide = [record for key, record in records.items() if key.startswith("1-")]  # sourceId 1
    assert region_wide and all(record.structured.end is None for record in region_wide)
    assert all("no end stated" in record.structured.stated_period for record in region_wide)
    vitoria = records["6-2849"]  # 09:30-18:30 on 21 October
    assert vitoria.structured.start == datetime(2026, 10, 21, 7, 30, tzinfo=timezone.utc)
    assert vitoria.structured.end == datetime(2026, 10, 21, 16, 30, tzinfo=timezone.utc)
    assert vitoria.structured.event_type is None  # no incidenceType given
    # An end written at 00:00 is read as 00:00: such a work has ended for REI today.
    midnight = next(record for record in records.values() if record.raw["item"].get("endDate") == "2026-10-21T00:00")
    assert midnight.structured.end == datetime(2026, 10, 21, 0, 0, tzinfo=MADRID_TIME)
    kept = {record.external_id for record in _euskadi_connector().fetch()}
    assert midnight.external_id not in kept
    # HTML character references are read, kilometre points only with a road.
    bilbao = records["5-2024"]
    assert "VÍA PÚBLICA DURANTE EL AÑO 2026" in bilbao.title and "km" not in bilbao.title
    assert records["1-376747"].title == "Road safety (Avería): AP-68 km 36.0, Urkabustaiz (ARABA)"
    assert records["1-376740"].title == "Road works: AP-1 km 128.0–129.0, Arrasate/Mondragón (GIPUZKOA)"


# --- through the pipeline ----------------------------------------------------------------------


@pytest.mark.parametrize("name", ["dgt", "barcelona", "madrid", "euskadi"])
def test_events_through_the_pipeline(session, name):
    if name == "dgt":
        source, city = spain_dgt.dgt_source(scheduled=True), SPAIN
        connector = spain_dgt.SpainDgtIncidentsConnector(
            source, "ua", client=_client(lambda request: httpx.Response(200, text=DGT_XML)), clock=lambda: NOW
        )
    elif name == "barcelona":
        source, city = barcelona.barcelona_source(scheduled=True), BCN
        connector = barcelona.BarcelonaWorksConnector(
            source, "ua", client=_client(lambda request: httpx.Response(200, json=BARCELONA)), clock=lambda: NOW
        )
    elif name == "madrid":
        source, city, connector = madrid.madrid_source(scheduled=True), MAD, _madrid_connector()
    else:
        source, city, connector = euskadi.euskadi_source(scheduled=True), SPAIN, _euskadi_connector()
    SourceRepository(session).sync_registry([source])
    session.commit()
    result = run_ingestion(connector, KeywordClassifier.from_file(), SqlIngestionStore(session), None, city)
    session.commit()
    events = list(session.scalars(select(Event).where(Event.source_id == source.source_id)))
    assert result.events_created == len(events) > 0
    assert all(event.geometry and event.start_time for event in events)
    assert all(event.status == "VALIDATION_REQUIRED" for event in events)
