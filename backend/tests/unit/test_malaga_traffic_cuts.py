"""Málaga's traffic cuts (cortes de tráfico), on the real file served on
22 October 2026. No test reaches the service."""

import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import String, select

from app.models import Event, Source
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from connectors.base import ConnectorError
from connectors.official import malaga
from connectors.registry import registered_sources
from packages.cities import area_of, country_entry, get_city
from packages.event_schema import EventType
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass, TermsStatus
from services.extraction import KeywordClassifier
from services.ingestion import run_ingestion

FEED = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "malaga_cortes_trafico_2026-10-22.geojson").read_text(encoding="utf-8")
)
NOW = datetime(2026, 10, 22, 11, 0, tzinfo=timezone.utc)
MALAGA_TIME = ZoneInfo("Europe/Madrid")
CITY = get_city("malaga")


def _records():
    return [record for item in FEED["features"] if (record := malaga.to_record(item, NOW)) is not None]


def _connector() -> malaga.MalagaTrafficCutsConnector:
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=FEED)))
    return malaga.MalagaTrafficCutsConnector(malaga.malaga_source(scheduled=True), "ua", client=client, clock=lambda: NOW)


def test_malaga_is_a_spanish_city_covering_every_cut():
    assert (CITY.country, CITY.timezone, CITY.level) == ("ES", "Europe/Madrid", "city")
    assert country_entry(CITY) == get_city("spain")
    assert "malaga" in {city.id for city in area_of(get_city("spain"))}
    for feature in FEED["features"]:
        longitude, latitude = feature["geometry"]["coordinates"][:2]
        assert CITY.covers(latitude, longitude)
    assert not CITY.covers(40.4168, -3.7038)  # Madrid


def test_the_source_is_an_official_located_feed_with_its_licence_caveat():
    definition = malaga.malaga_source(scheduled=False)
    assert definition.city == "malaga" and definition.source_id in CITY.official_sources
    assert definition.source_tier == 1 and definition.source_class is SourceClass.GOVERNMENT_OPEN_DATA
    assert definition.integration_status is IntegrationStatus.CONNECTED and definition.active is False
    assert malaga.malaga_source(scheduled=True).active is True
    assert definition.terms_status is TermsStatus.PERMITS_TESTING and definition.terms_reviewed is False
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    assert "BY-SA" in definition.licence and "Ayuntamiento de Málaga" in definition.attribution
    limits = {
        column.name: column.type.length
        for column in Source.__table__.columns
        if isinstance(column.type, String) and column.type.length
    }
    values = definition.model_dump(mode="json")
    assert all(len(str(values[name])) <= limit for name, limit in limits.items() if values.get(name) is not None)


def test_it_is_registered_and_runs_only_when_chosen():
    by_id = {source.definition.source_id: source for source in registered_sources()}
    assert by_id["malaga-traffic-cuts"].definition.active is False
    chosen = {
        source.definition.source_id: source
        for source in registered_sources(official_feeds_scheduled_sources={"malaga-traffic-cuts"})
    }
    assert chosen["malaga-traffic-cuts"].definition.active is True


def test_types_come_from_what_is_cut_and_parking_only_is_not_a_road_event():
    records = _records()
    # 110 features, 9 of which take parking spaces only.
    assert len(records) == 101
    types = [record.structured.event_type for record in records]
    assert types.count(EventType.PLANNED_ROAD_CLOSURE.value) == 34
    assert types.count(EventType.LANE_RESTRICTION.value) == 60
    assert types.count(None) == 7  # blank in the source: no type invented
    assert all("estacionamiento" not in (record.structured.category or "").lower() for record in records)


def test_times_are_malaga_time_as_written_and_no_time_is_invented():
    records = {record.external_id: record for record in _records()}
    first = records["AFECTACION_0000576_313322"]
    assert first.structured.start == datetime(2025, 10, 29, 9, 30, tzinfo=MALAGA_TIME)
    assert first.structured.end == datetime(2027, 3, 29, 18, 0, tzinfo=MALAGA_TIME)
    assert first.structured.stated_period == "29/10/2025 9:30 – 29/03/2027 18:00 (Málaga time)"
    blank = [record for record in records.values() if record.structured.event_type is None]
    assert blank and all(r.structured.start is None and r.structured.end is None for r in blank)
    assert all(r.structured.stated_period is None for r in blank)
    # A one-digit day is read too.
    assert any(r.structured.start and r.structured.start.day == 1 and r.structured.start.month == 11 for r in records.values())


def test_points_drop_the_stray_third_value_and_titles_name_the_street():
    records = _records()
    assert all(len(record.structured.geometry["coordinates"]) == 2 for record in records)
    closure = next(r for r in records if r.external_id == "AFECTACION_0000631_476672")
    assert closure.title == "Road closed (obras): CALLE FRAILES, 36"
    assert closure.structured.event_type == EventType.PLANNED_ROAD_CLOSURE.value
    assert closure.url == malaga.SOURCE_URL and closure.raw["item"]["properties"]["ID"] == 79341


def test_fetch_keeps_cuts_in_force_or_coming_and_refuses_what_is_not_geojson():
    connector = _connector()
    kept = connector.fetch()
    assert len(connector.observed_ids) == 101
    assert kept and all(record.structured.end is None or record.structured.end >= NOW for record in kept)
    bad = malaga.MalagaTrafficCutsConnector(
        malaga.malaga_source(scheduled=True), "ua",
        client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"rows": []}))),
        clock=lambda: NOW,
    )  # fmt: skip
    with pytest.raises(ConnectorError):
        bad.fetch()


def test_cuts_become_located_events_awaiting_validation(session):
    source = malaga.malaga_source(scheduled=True)
    SourceRepository(session).sync_registry([source])
    session.commit()
    result = run_ingestion(_connector(), KeywordClassifier.from_file(), SqlIngestionStore(session), None, CITY)
    session.commit()
    events = list(session.scalars(select(Event).where(Event.source_id == source.source_id)))
    assert result.events_created == len(events) > 0
    assert all(event.geometry and event.status == "VALIDATION_REQUIRED" for event in events)
    assert all(event.start_time for event in events if event.event_type)
