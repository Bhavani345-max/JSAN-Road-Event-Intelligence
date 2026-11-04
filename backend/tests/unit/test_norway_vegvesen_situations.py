"""Statens vegvesen's road traffic situations (DATEX II WFS), Norway, on a real
excerpt of the layer served on 4 November 2026 (14 situations, 28 records; the
collection's counts are the excerpt's own). No test reaches the service."""

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
from connectors.official import norway_vegvesen as vegvesen
from connectors.registry import registered_sources
from packages.cities import area_of, get_city, load_cities
from packages.event_schema import EventType
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass, TermsStatus
from services.extraction import KeywordClassifier
from services.ingestion import run_ingestion

FEED = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "norway_vegvesen_situations_2026-11-04.geojson").read_text(
        encoding="utf-8"
    )
)
NOW = datetime(2026, 11, 4, 11, 0, tzinfo=timezone.utc)
CET = timezone(timedelta(hours=1))
NORWAY = get_city("norway")
REGISTERED = {source.definition.source_id for source in registered_sources()}


def _records():
    items = vegvesen.situation_items(FEED["features"])
    return {item["id"]: vegvesen.to_record(item, NOW) for item in items}


def _connector(feed=FEED) -> vegvesen.VegvesenSituationsConnector:
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=feed)))
    return vegvesen.VegvesenSituationsConnector(
        vegvesen.vegvesen_source(scheduled=True), "ua", client=client, clock=lambda: NOW
    )


def test_norway_sweden_and_denmark_are_country_entries_and_norway_covers_every_situation():
    cities = load_cities()
    assert {(cities[c].country, cities[c].level, cities[c].timezone) for c in ("norway", "sweden", "denmark")} == {
        ("NO", "country", "Europe/Oslo"),
        ("SE", "country", "Europe/Stockholm"),
        ("DK", "country", "Europe/Copenhagen"),
    }
    assert {"Norge", "Sverige", "Danmark"} <= {term for c in ("norway", "sweden", "denmark") for term in cities[c].scope_terms}
    assert cities["sweden"].official_sources == () and cities["denmark"].official_sources == ()
    assert NORWAY.official_sources == (vegvesen.SOURCE_ID,) and NORWAY in area_of(NORWAY)
    for feature in FEED["features"]:
        position = feature["geometry"]["coordinates"]
        while isinstance(position[0], list):
            position = position[0]
        assert NORWAY.covers(position[1], position[0])
    assert not NORWAY.covers(55.6761, 12.5683)  # Copenhagen (a box around Norway holds Stockholm)


def test_the_source_is_an_official_open_feed_recorded_as_permitted_with_attribution():
    definition = vegvesen.vegvesen_source(scheduled=False)
    assert definition.city == "norway" and definition.country == "NO" and definition.region == "National"
    assert definition.source_tier == 1 and definition.source_class is SourceClass.GOVERNMENT_OPEN_DATA
    assert definition.integration_status is IntegrationStatus.CONNECTED and definition.active is False
    assert vegvesen.vegvesen_source(scheduled=True).active is True
    assert definition.terms_status is TermsStatus.PERMITS_TESTING and definition.terms_reviewed is False
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    assert "NLOD" in definition.licence and "translate" in definition.licence
    assert "Statens vegvesen" in definition.attribution and "never translated" in definition.notes
    limits = {
        column.name: column.type.length
        for column in Source.__table__.columns
        if isinstance(column.type, String) and column.type.length
    }
    values = definition.model_dump(mode="json")
    assert all(len(str(values[name])) <= limit for name, limit in limits.items() if values.get(name) is not None)


@pytest.mark.skipif(
    vegvesen.SOURCE_ID not in REGISTERED,
    reason="registered by adding it to connectors/registry.py (feature_feeds); see the notes of 4 November 2026",
)
def test_it_is_registered_and_runs_only_when_chosen():
    by_id = {source.definition.source_id: source for source in registered_sources()}
    assert by_id[vegvesen.SOURCE_ID].definition.active is False
    chosen = {
        source.definition.source_id: source
        for source in registered_sources(official_feeds_scheduled_sources={vegvesen.SOURCE_ID})
    }
    assert chosen[vegvesen.SOURCE_ID].definition.active is True


def test_one_record_per_situation_and_ferry_notices_are_not_road_events():
    records = _records()
    assert len(records) == 14
    assert records["NPRA_HBT_02-11-2026.162256"] is None  # "Ferje - Innstilt."
    kept = {key: record for key, record in records.items() if record is not None}
    assert len(kept) == 13 and all(record.external_id == key for key, record in kept.items())
    types = {key: record.structured.event_type for key, record in kept.items()}
    # Works with a closure and a diversion: the closure leads, and it is planned.
    assert types["NPRA_HBT_02-11-2026.162462"] == EventType.PLANNED_ROAD_CLOSURE.value
    assert kept["NPRA_HBT_02-11-2026.162462"].title == "Road closed – Fv. 4488 Iglemyr i Sandnes, Rogaland (Statens vegvesen)"
    assert types["NPRA_HBT_19-10-2026.154207"] == EventType.ROAD_WORKS.value
    # A road closed for an event is a planned closure.
    assert types["NPRA_HBT_02-11-2026.162556"] == EventType.PLANNED_ROAD_CLOSURE.value
    assert types["NPRA_HBT_04-11-2026.163502"] == EventType.ROAD_HAZARD.value  # a broken-down vehicle
    # An accident closing one lane: the lane closure leads, as in REI's merge order.
    assert types["NPRA_HBT_04-11-2026.163792"] == EventType.LANE_RESTRICTION.value
    assert "Accident / accident" in kept["NPRA_HBT_04-11-2026.163792"].structured.category
    # A winter closure and a strong-wind closure keep their words with no type invented.
    winter = kept["NPRA_HBT_09-10-2026.149375"]
    assert winter.structured.event_type is None and winter.title.startswith("Closed permanently for the winter – E134")
    assert types["NPRA_HBT_04-11-2026.163838"] is None
    # The emergency vehicles' lane is never the lead of works.
    assert types["NPRA_HBT_29-10-2026.160504"] == EventType.ROAD_WORKS.value


def test_times_are_as_stated_with_their_offsets_and_no_end_is_invented():
    records = _records()
    closure = records["NPRA_HBT_02-11-2026.162462"].structured
    assert closure.start == datetime(2026, 11, 5, 8, 0, tzinfo=CET)
    assert closure.end == datetime(2026, 11, 30, 16, 0, tzinfo=CET)
    # Summer time at the start, winter time at the end, both as written.
    tunnel = records["NPRA_HBT_09-10-2026.149112"].structured
    assert tunnel.start == datetime(2026, 10, 12, 20, 0, tzinfo=timezone(timedelta(hours=2)))
    assert tunnel.end == datetime(2026, 12, 23, 6, 0, tzinfo=CET)
    wind = records["NPRA_HBT_04-11-2026.163838"].structured
    assert wind.start == datetime(2026, 11, 4, 11, 57, 28, tzinfo=CET) and wind.end is None
    assert records["NPRA_HBT_02-11-2026.162462"].published_at == datetime(2026, 11, 4, 6, 41, 43, 670000, tzinfo=CET)


def test_norwegian_text_is_kept_as_written_and_contact_lines_are_removed():
    closure = _records()["NPRA_HBT_02-11-2026.162462"]
    # The description's parts (separated by "|" in the source), in Norwegian: dates
    # and hours are not taken for phone numbers.
    assert closure.summary == (
        "Vegarbeid, vegen er stengt, gyldig mellom 05.11.2026 08:00 og 30.11.2026 16:00.\nOmkjøring er skiltet."
    )
    assert closure.structured.affected_road == "Fv. 4488 Iglemyr i Sandnes, Rogaland"
    assert vegvesen.without_contact_details("Kl. 1010-1210, kl. 1220-1315 kvar dag.") == "Kl. 1010-1210, kl. 1220-1315 kvar dag."
    for contact in ("Kontaktperson: [navn]", "Ring 000 00 000 ved spørsmål", "tlf. 00 00 00 00", "[e-post]@example.invalid"):
        assert vegvesen.without_contact_details(f"Vegarbeid.\n{contact}") == "Vegarbeid.\n[contact details removed by REI]"


def test_geometry_is_the_sources_own_and_kept_once_per_situation():
    records = _records()
    by_situation = {}
    for feature in FEED["features"]:
        by_situation.setdefault(feature["properties"]["SITUATION_ID"], feature["geometry"])
    for key, record in records.items():
        if record is None:
            continue
        geometry = record.structured.geometry
        assert geometry == {"type": by_situation[key]["type"], "coordinates": by_situation[key]["coordinates"]}
    assert records["NPRA_HBT_09-10-2026.149112"].structured.geometry["type"] == "MultiLineString"
    # Each situation's records repeat one shape: it is kept on the first only.
    item = records["NPRA_HBT_09-10-2026.149112"].raw["item"]
    assert [bool(record.get("lines")) for record in item["records"]] == [True, False, False]
    # The feed's internal ids and fetch-time flag are not kept.
    evidence = json.dumps([record.raw["item"] for record in records.values() if record], ensure_ascii=False)
    assert all(name not in evidence for name in ('"ACTIVE"', '"PUB_ID"', '"ID"', "531875"))


def test_a_record_served_twice_is_kept_once():
    features = [copy.deepcopy(feature) for feature in FEED["features"] if feature["properties"]["SITUATION_ID"] == "NPRA_HBT_19-10-2026.154207"]
    twice = features + [copy.deepcopy(features[0])]
    twice[-1]["properties"]["ID"] = 1  # another feature row of the same record
    (item,) = vegvesen.situation_items(twice)
    assert len(item["records"]) == 1


def test_revisions_ignore_bookkeeping_but_not_content():
    def key(feed):
        return vegvesen.VegvesenSituationsConnector.revision_key(
            vegvesen.to_record(vegvesen.situation_items(feed["features"])[0], NOW).raw
        )

    first = key(FEED)
    touched = copy.deepcopy(FEED)
    for feature in touched["features"]:
        feature["properties"].update(ACTIVE=1, PUB_ID=1, ID=1, LAST_UPDATE_TIME="2026-11-04T12:00:00+01:00")
    assert key(touched) == first
    changed = copy.deepcopy(FEED)
    changed["features"][0]["properties"]["END_TIME"] = "2026-12-01T16:00:00+01:00"
    assert key(changed) != first


def test_fetch_keeps_what_is_in_force_or_coming_and_refuses_what_is_not_the_layer():
    connector = _connector()
    kept = connector.fetch()
    assert len(connector.observed_ids) == 13
    # The broken-down vehicle was cleared at 10:40 CET, before the run.
    assert "NPRA_HBT_04-11-2026.163502" not in {record.external_id for record in kept} and len(kept) == 12
    assert all(record.structured.end is None or record.structured.end >= NOW for record in kept)
    for bad in ({"rows": []}, {**FEED, "numberMatched": 999}):
        with pytest.raises(ConnectorError):
            _connector(bad).fetch()
    swapped = copy.deepcopy(FEED)
    point = next(f for f in swapped["features"] if f["geometry"]["type"] == "Point")
    point["geometry"]["coordinates"] = point["geometry"]["coordinates"][::-1]
    with pytest.raises(ConnectorError, match="latitude-longitude"):
        _connector(swapped).fetch()


def test_situations_become_located_events_awaiting_validation(session):
    source = vegvesen.vegvesen_source(scheduled=True)
    SourceRepository(session).sync_registry([source])
    session.commit()
    result = run_ingestion(_connector(), KeywordClassifier.from_file(), SqlIngestionStore(session), None, NORWAY)
    session.commit()
    events = list(session.scalars(select(Event).where(Event.source_id == source.source_id)))
    assert result.events_created == len(events) > 0
    assert all(event.geometry and event.status == "VALIDATION_REQUIRED" for event in events)
    assert all(event.start_time for event in events if event.event_type)
