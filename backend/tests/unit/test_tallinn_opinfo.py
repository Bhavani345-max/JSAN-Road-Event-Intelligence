"""Tallinn's street closures and works on city land (opinfo.tallinn.ee), on real
excerpts of the two files served on 5 November 2026: 5 closures, and 8 works
objects of which one is a closure also in the closures file (12 objects). The
applicant, client, contractor and owner of every object read "[removed]" (they
can be private persons). No test reaches the service."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

import httpx
import pytest
from sqlalchemy import String, select

from app.models import Event, Source
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from connectors.base import ConnectorError
from connectors.official import tallinn_opinfo as tallinn
from connectors.registry import OFFICIAL_SOURCE_IDS, registered_sources
from packages.cities import area_of, country_entry, get_city
from packages.event_schema import EventType
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass, TermsStatus
from services.extraction import KeywordClassifier
from services.ingestion import run_ingestion

FIXTURES = Path(__file__).parents[1] / "fixtures"
CLOSURES = (FIXTURES / "tallinn_opinfo_closures_2026-11-05.xml").read_text(encoding="utf-8")
WORKS = (FIXTURES / "tallinn_opinfo_works_2026-11-05.xml").read_text(encoding="utf-8")
NOW = datetime(2026, 11, 5, 9, 0, tzinfo=timezone.utc)
SUMMER, WINTER = timezone(timedelta(hours=3)), timezone(timedelta(hours=2))
CITY = get_city("tallinn")


def _items() -> dict[str, dict]:
    items: dict[str, dict] = {}
    for url, text in ((tallinn.CLOSURES_FEED, CLOSURES), (tallinn.WORKS_FEED, WORKS)):
        for item in tallinn.parse_feed(text, url):
            items.setdefault(item["id"], item)
    return items


def _records():
    return {object_id: tallinn.to_record(item, NOW) for object_id, item in _items().items()}


def _connector(closures=CLOSURES, works=WORKS) -> tallinn.TallinnStreetClosuresConnector:
    bodies = {tallinn.CLOSURES_FEED: closures, tallinn.WORKS_FEED: works}
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text=bodies[str(request.url)]))
    )
    return tallinn.TallinnStreetClosuresConnector(
        tallinn.tallinn_source(scheduled=True), "ua", client=client, clock=lambda: NOW
    )


def test_tallinn_is_an_estonian_city_within_estonia_covering_every_object():
    assert (CITY.country, CITY.timezone, CITY.level, CITY.language) == ("EE", "Europe/Tallinn", "city", "et")
    assert country_entry(CITY) == get_city("estonia")
    assert "tallinn" in {city.id for city in area_of(get_city("estonia"))}
    assert CITY.official_sources == (tallinn.SOURCE_ID,)
    for item in _items().values():
        shape = tallinn.geometry(item)
        if shape:
            position = shape["coordinates"]
            while isinstance(position[0], list):
                position = position[0]
            assert CITY.covers(position[1], position[0])
    assert not CITY.covers(58.3780, 26.7290)  # Tartu


def test_the_source_is_an_official_located_feed_recorded_as_permitted_with_attribution():
    definition = tallinn.tallinn_source(scheduled=False)
    assert definition.city == "tallinn" and definition.country == "EE"
    assert definition.source_tier == 1 and definition.source_class is SourceClass.GOVERNMENT_OPEN_DATA
    assert definition.integration_status is IntegrationStatus.CONNECTED and definition.active is False
    assert tallinn.tallinn_source(scheduled=True).active is True
    assert definition.terms_status is TermsStatus.PERMITS_TESTING and definition.terms_reviewed is False
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    assert "CC BY 3.0" in definition.licence and "Tallinna Linnavalitsus" in definition.attribution
    limits = {
        column.name: column.type.length
        for column in Source.__table__.columns
        if isinstance(column.type, String) and column.type.length
    }
    values = definition.model_dump(mode="json")
    assert all(len(str(values[name])) <= limit for name, limit in limits.items() if values.get(name) is not None)


def test_it_is_an_official_feed_registered_to_run_only_when_chosen():
    assert tallinn.SOURCE_ID in OFFICIAL_SOURCE_IDS
    by_id = {source.definition.source_id: source for source in registered_sources()}
    assert by_id[tallinn.SOURCE_ID].definition.active is False
    chosen = {
        source.definition.source_id: source
        for source in registered_sources(official_feeds_scheduled_sources={tallinn.SOURCE_ID})
    }
    assert chosen[tallinn.SOURCE_ID].definition.active is True


def test_only_events_on_the_carriageway_are_kept():
    records = _records()
    assert len(records) == 12
    kept = {object_id: record for object_id, record in records.items() if record is not None}
    assert {object_id: record.structured.event_type for object_id, record in kept.items()} == {
        "275767": EventType.PLANNED_ROAD_CLOSURE.value,  # carriageway 7 m, 7 m closed
        "307040": EventType.LANE_RESTRICTION.value,  # 10 m, 3 m closed
        "324335": EventType.LANE_RESTRICTION.value,  # 7.5 m, 3.8 m closed
        "266577": EventType.ROAD_WORKS.value,  # excavation in the carriageway
        "266579": EventType.ROAD_WORKS.value,
        "354030": EventType.ROAD_WORKS.value,  # emergency excavation
    }
    # 256937 closes 0 m of the carriageway, 273410 only the pavement, 266582 digs
    # a green area; 344256 is road works with no place on the street; the haulage
    # (278191) and weight-limit (309501) permits are not events on the road.
    assert {object_id for object_id, record in records.items() if record is None} == {
        "256937", "273410", "266582", "344256", "278191", "309501",
    }  # fmt: skip
    closed = kept["275767"]
    assert closed.external_id == "objekt:275767" and closed.title == "Road closed: Visase tänav T4 (Tallinn)"
    assert closed.url == "https://opinfo.tallinn.ee/menetlus/113106"
    assert closed.structured.locations[0].closure == "Sõidutee: kogulaius 7 m, suletav laius 7 m"
    assert kept["354030"].title == "Emergency excavation: Supluse pst (Tallinn)"
    assert ".." not in " ".join(record.summary for record in kept.values())


def test_times_are_tallinn_time_and_the_daily_hours_are_kept_in_words():
    lanes = _records()["307040"].structured
    assert lanes.start == datetime(2025, 10, 23, 0, 0, tzinfo=SUMMER)
    assert lanes.end == datetime(2026, 12, 31, 23, 59, tzinfo=WINTER)
    assert lanes.stated_period == (
        "2025-10-23 00:00 – 2026-12-31 23:59 (iga päev: 00:00–05:00, 09:00–15:30, 20:00–23:59)"
    )
    assert lanes.affected_road == "Sõpruse pst"
    assert _records()["275767"].structured.stated_period == "2024-10-17 08:00 – 2026-11-30 18:00 (pidev)"


def test_the_shape_is_read_from_the_kml_in_longitude_latitude_order():
    records = _records()
    assert records["307040"].structured.geometry["type"] == "LineString"
    polygon = records["275767"].structured.geometry
    assert polygon["type"] == "Polygon" and polygon["coordinates"][0][0] == polygon["coordinates"][0][-1]
    assert records["307040"].structured.locations[0].kind == "street section"
    assert tallinn.geometry({"ruumiobjekt_kml": "<Point><coordinates>24.87,59.41</coordinates></Point>"}) == {
        "type": "Point",
        "coordinates": [24.87, 59.41],
    }
    assert tallinn.geometry({"ruumiobjekt_kml": ""}) is None


def test_no_applicant_client_contractor_owner_phone_or_e_mail_is_kept():
    evidence = json.dumps([record.raw for record in _records().values() if record], ensure_ascii=False)
    for word in ("taotleja", "tellija\"", "teostaja", "valdaja", "[removed]"):
        assert word not in evidence
    element = ET.fromstring(
        "<objekt><id>1</id><taotleja>A Person</taotleja><teostaja>Firm</teostaja>"
        "<kirjeldus>Info: Mari, tel +372 5123 4567 või 6404404, mari@example.ee. Kestus 2026-11-05.</kirjeldus>"
        "</objekt>"
    )
    item = tallinn.object_item(element)
    assert "taotleja" not in item and "teostaja" not in item
    assert item["kirjeldus"] == "Info: Mari, tel [removed] või [removed], [removed]. Kestus 2026-11-05."


def test_fetch_reads_both_files_once_each_and_refuses_a_cut_or_swapped_list():
    connector = _connector()
    kept = connector.fetch()
    assert len(connector.observed_ids) == 6 and len(kept) == 6
    cut = CLOSURES.replace("<lehekylgi_kokku>\n      1    </lehekylgi_kokku>", "<lehekylgi_kokku>3</lehekylgi_kokku>")
    assert cut != CLOSURES
    miscounted = WORKS.replace("<kirjeid>\n      8    </kirjeid>", "<kirjeid>9</kirjeid>")
    assert miscounted != WORKS
    for closures, works in ((cut, WORKS), (CLOSURES, miscounted), ("<html>", WORKS)):
        with pytest.raises(ConnectorError):
            _connector(closures, works).fetch()
    swapped = CLOSURES.replace("24.870292998667818,59.41586683604354", "59.41586683604354,24.870292998667818")
    assert swapped != CLOSURES
    with pytest.raises(ConnectorError, match="latitude-longitude"):
        _connector(swapped, WORKS).fetch()


def test_objects_become_located_events_awaiting_validation(session):
    source = tallinn.tallinn_source(scheduled=True)
    SourceRepository(session).sync_registry([source])
    session.commit()
    result = run_ingestion(_connector(), KeywordClassifier.from_file(), SqlIngestionStore(session), None, CITY)
    session.commit()
    events = list(session.scalars(select(Event).where(Event.source_id == source.source_id)))
    assert result.events_created == len(events) == 6
    assert all(event.geometry and event.status == "VALIDATION_REQUIRED" for event in events)
    assert all(event.start_time and event.end_time for event in events)
