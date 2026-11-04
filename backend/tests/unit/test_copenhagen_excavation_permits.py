"""Copenhagen's excavation permits (gravetilladelser), on a real excerpt of the
layer served on 4 November 2026 (11 permits, 16 shapes; the collection's counts
are the excerpt's own). The developer and contractor of every shape are
replaced by placeholders: they can be private persons. No test reaches the
service."""

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
from connectors.official import copenhagen_excavation as copenhagen
from connectors.registry import registered_sources
from packages.cities import area_of, country_entry, get_city
from packages.event_schema import EventType
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass, TermsStatus
from services.extraction import KeywordClassifier
from services.ingestion import run_ingestion

FEED = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "copenhagen_gravetilladelser_2026-11-04.geojson").read_text(
        encoding="utf-8"
    )
)
NOW = datetime(2026, 11, 4, 11, 0, tzinfo=timezone.utc)
CEST, CET = timezone(timedelta(hours=2)), timezone(timedelta(hours=1))
CITY = get_city("copenhagen")
REGISTERED = {source.definition.source_id for source in registered_sources()}


def _records():
    return {item["sagsnr"]: copenhagen.to_record(item, NOW) for item in copenhagen.permits(FEED["features"])}


def _connector(feed=FEED) -> copenhagen.CopenhagenExcavationPermitsConnector:
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=feed)))
    return copenhagen.CopenhagenExcavationPermitsConnector(
        copenhagen.copenhagen_source(scheduled=True), "ua", client=client, clock=lambda: NOW
    )


def test_copenhagen_is_a_danish_city_within_denmark_covering_every_permit():
    assert (CITY.country, CITY.timezone, CITY.level, CITY.language) == ("DK", "Europe/Copenhagen", "city", "da")
    assert country_entry(CITY) == get_city("denmark")
    assert "copenhagen" in {city.id for city in area_of(get_city("denmark"))}
    assert CITY.official_sources == (copenhagen.SOURCE_ID,) and "København" in CITY.scope_terms
    for feature in FEED["features"]:
        position = feature["geometry"]["coordinates"]
        while isinstance(position[0], list):
            position = position[0]
        assert CITY.covers(position[1], position[0])
    assert not CITY.covers(56.1629, 10.2039)  # Aarhus


def test_the_source_is_an_official_located_feed_recorded_as_permitted_with_attribution():
    definition = copenhagen.copenhagen_source(scheduled=False)
    assert definition.city == "copenhagen" and definition.country == "DK"
    assert definition.source_tier == 1 and definition.source_class is SourceClass.GOVERNMENT_OPEN_DATA
    assert definition.integration_status is IntegrationStatus.CONNECTED and definition.active is False
    assert copenhagen.copenhagen_source(scheduled=True).active is True
    assert definition.terms_status is TermsStatus.PERMITS_TESTING and definition.terms_reviewed is False
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    assert "CC BY 4.0" in definition.licence and "Københavns Kommune" in definition.attribution
    limits = {
        column.name: column.type.length
        for column in Source.__table__.columns
        if isinstance(column.type, String) and column.type.length
    }
    values = definition.model_dump(mode="json")
    assert all(len(str(values[name])) <= limit for name, limit in limits.items() if values.get(name) is not None)


@pytest.mark.skipif(
    copenhagen.SOURCE_ID not in REGISTERED,
    reason="registered by adding it to connectors/registry.py (feature_feeds); see the notes of 4 November 2026",
)
def test_it_is_registered_and_runs_only_when_chosen():
    by_id = {source.definition.source_id: source for source in registered_sources()}
    assert by_id[copenhagen.SOURCE_ID].definition.active is False
    chosen = {
        source.definition.source_id: source
        for source in registered_sources(official_feeds_scheduled_sources={copenhagen.SOURCE_ID})
    }
    assert chosen[copenhagen.SOURCE_ID].definition.active is True


def test_one_record_per_permit_and_only_works_in_the_carriageway_or_a_cycle_path():
    records = _records()
    assert len(records) == 11
    # Pavement only, parking and pavement only, and a private developer's pavement dig.
    assert [number for number, record in records.items() if record is None] == ["813056", "812009", "821082"]
    kept = [record for record in records.values() if record is not None]
    assert len(kept) == 8 and all(record.structured.event_type == EventType.ROAD_WORKS.value for record in kept)
    assert all({"Kørebane", "Cykelsti"} & set(record.raw["categories"]) for record in kept)
    cycle_path = records["815779"]
    assert cycle_path.external_id == "permit:815779" and cycle_path.title == "Road works: Nørre Søgade 9A - 17 (Copenhagen)"
    assert cycle_path.structured.category == "Andet / Cykelsti"


def test_days_are_whole_days_in_copenhagen_time_and_the_daily_hours_are_kept_in_words():
    paving = _records()["816988"].structured
    # From the start of 21 October (summer time) to the end of 6 November (winter time).
    assert paving.start == datetime(2026, 10, 21, 0, 0, tzinfo=CEST)
    assert paving.end == datetime(2026, 11, 6, 23, 59, 59, tzinfo=CET)
    assert paving.stated_period == "21-10-26 – 06-11-26, tidspunkt 07:00–17:00"
    assert paving.affected_road == "Lyshøjgårdsvej 80 - 25"


def test_the_works_area_is_the_permits_polygons_else_its_lines_else_its_point():
    records = _records()
    shapes = {}
    for feature in FEED["features"]:
        shapes.setdefault(feature["properties"]["sagsnr"], []).append(feature["geometry"])
    line_and_polygon = records["816988"].structured.geometry
    assert line_and_polygon == next(shape for shape in shapes[816988] if shape["type"] == "Polygon")
    assert records["816923"].structured.geometry["type"] == "MultiPolygon"
    assert len(records["816923"].structured.geometry["coordinates"]) == 2
    two_lines = records["817094"].structured.geometry
    assert two_lines["type"] == "MultiLineString" and len(two_lines["coordinates"]) == 2
    assert records["813187"].structured.geometry == shapes[813187][0]  # a point only
    assert records["815779"].structured.locations[0].kind == "street section"


def test_no_developer_contractor_or_row_number_is_kept():
    records = _records()
    evidence = json.dumps([record.raw for record in records.values() if record], ensure_ascii=False)
    for word in ("bygherre", "entreprenoer", "[developer]", "[contractor]", "ogc_fid", "gravetilladelser_aktiv_aabne.fid"):
        assert word not in evidence


def test_a_reload_that_renumbers_the_rows_is_not_a_revision_but_a_new_end_is():
    def key(feed):
        item = next(item for item in copenhagen.permits(feed["features"]) if item["sagsnr"] == "816988")
        record = copenhagen.to_record(item, NOW)
        return copenhagen.CopenhagenExcavationPermitsConnector.revision_key(record.raw), record.content_hash

    first = key(FEED)
    renumbered = copy.deepcopy(FEED)
    for number, feature in enumerate(reversed(renumbered["features"])):
        feature["id"] = f"gravetilladelser_aktiv_aabne.fid-{number}"
        feature["properties"]["ogc_fid"] = 90000 + number
    renumbered["features"].reverse()
    assert key(renumbered) == first
    later = copy.deepcopy(FEED)
    for feature in later["features"]:
        if feature["properties"]["sagsnr"] == 816988:
            feature["properties"]["projekt_slut"] = "13-11-26"
    assert key(later) != first


def test_fetch_keeps_permits_in_force_or_coming_and_refuses_what_is_not_the_layer():
    connector = _connector()
    kept = connector.fetch()
    assert len(connector.observed_ids) == 8
    # 782980 starts on 1 July 2028, beyond REI's run window of a year.
    assert "permit:782980" not in {record.external_id for record in kept} and len(kept) == 7
    for bad in ({"rows": []}, {**FEED, "numberMatched": 999}):
        with pytest.raises(ConnectorError):
            _connector(bad).fetch()
    swapped = copy.deepcopy(FEED)
    point = next(f for f in swapped["features"] if f["geometry"]["type"] == "Point")
    point["geometry"]["coordinates"] = point["geometry"]["coordinates"][::-1]
    with pytest.raises(ConnectorError, match="latitude-longitude"):
        _connector(swapped).fetch()


def test_permits_become_located_events_awaiting_validation(session):
    source = copenhagen.copenhagen_source(scheduled=True)
    SourceRepository(session).sync_registry([source])
    session.commit()
    result = run_ingestion(_connector(), KeywordClassifier.from_file(), SqlIngestionStore(session), None, CITY)
    session.commit()
    events = list(session.scalars(select(Event).where(Event.source_id == source.source_id)))
    assert result.events_created == len(events) > 0
    assert all(event.geometry and event.status == "VALIDATION_REQUIRED" for event in events)
    assert all(event.start_time and event.end_time for event in events)
