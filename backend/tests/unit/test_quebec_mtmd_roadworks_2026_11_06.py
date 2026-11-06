"""Transports Québec road works (decision 0062), on 8 real segments of 6 November 2026.

The fixture is a trimmed copy of the WFS layer's GeoJSON as fetched that day (15:10
UTC). No test reaches the service.
"""

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

import httpx
import pytest

from connectors.official import quebec_mtmd_roadworks as qc
from connectors.registry import OFFICIAL_SOURCE_IDS, registered_sources
from packages.cities import get_city
from packages.event_schema import EventType
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass

FIXTURES = Path(__file__).parents[1] / "fixtures"
BODY = (FIXTURES / "quebec_mtmd_chantiers_2026-11-06.geojson").read_text(encoding="utf-8")
EASTERN = ZoneInfo("America/Toronto")
# 10:10 in Québec on 6 November 2026, when the fixture was fetched.
NOW = datetime(2026, 11, 6, 15, 10, tzinfo=timezone.utc)
CLOSED, LANES, WORKS = (
    EventType.PLANNED_ROAD_CLOSURE.value, EventType.LANE_RESTRICTION.value, EventType.ROAD_WORKS.value,
)  # fmt: skip


def fetch(now: datetime = NOW):
    requests = []

    def answer(request):
        requests.append(request)
        return httpx.Response(200, text=BODY)

    client = httpx.Client(transport=httpx.MockTransport(answer))
    connector = qc.QuebecMtmdRoadWorksConnector(qc.quebec_mtmd_source(scheduled=True), "ua", client=client, clock=lambda: now)
    return connector.fetch(), connector, requests


def by_id():
    records, _, _ = fetch()
    return {r.external_id: r for r in records}


def test_it_is_an_official_canadian_feed_run_by_hand_unless_scheduled():
    assert qc.SOURCE_ID in OFFICIAL_SOURCE_IDS
    assert qc.SOURCE_ID in get_city("canada").official_sources
    definition = {s.definition.source_id: s.definition for s in registered_sources()}[qc.SOURCE_ID]
    assert definition.integration_status is IntegrationStatus.CONNECTED and definition.active is False
    assert definition.source_class is SourceClass.AUTHORITATIVE_OFFICIAL and definition.source_tier == 1
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    assert "CC BY 4.0" in definition.licence and "Données Québec" in definition.attribution


def test_it_asks_for_the_road_works_layer_as_geojson_in_wgs84():
    _, _, requests = fetch()
    query = {k: v[0] for k, v in parse_qs(urlsplit(str(requests[0].url)).query).items()}
    assert query["typename"] == "ms:chantiers_mtmdet" and query["outputformat"] == "geojson"
    assert query["srsname"] == "EPSG:4326" and len(requests) == 1


def test_each_segment_keeps_its_line_local_times_road_and_english_description():
    tunnel = by_id()["149555"]
    assert tunnel.structured.geometry["type"] == "LineString"
    assert tunnel.structured.start == datetime(2025, 5, 5, 5, 0, tzinfo=EASTERN)
    assert tunnel.structured.end == datetime(2026, 12, 31, 23, 59, tzinfo=EASTERN)
    assert tunnel.structured.affected_road == "25" and tunnel.structured.direction == "BOTH_DIRECTIONS"
    assert tunnel.title.startswith("Road closed: Entre Longueuil et Montréal") and "road 25" in tunnel.title
    assert tunnel.summary.startswith("Refurbishment of structures")
    assert tunnel.structured.stated_period == "2025/05/05 05:00:00 – 2026/12/31 23:59:00"
    assert tunnel.raw["item"]["properties"]["identifiant"] == "149555"  # the feature itself is the evidence


def test_what_the_works_do_to_traffic_comes_from_the_ministrys_words():
    records = by_id()
    assert records["168663"].structured.event_type == CLOSED  # "Autoroute fermée"
    assert records["166812"].structured.event_type == CLOSED  # "Fermeture de l'accès à la sortie 314"
    assert records["163457"].structured.event_type == LANES  # "Fermeture de 1 voie sur 2"
    assert records["155134"].structured.event_type == LANES  # "Circulation en alternance"
    # Closed to pedestrians and cyclists only: vehicles alternate.
    assert records["165172"].structured.event_type == LANES
    assert records["165172"].structured.direction is None  # "Dans une direction à la fois"
    # Alternating traffic only if needed ("Au besoin:") states no effect for certain.
    assert records["168938"].structured.event_type == WORKS


@pytest.mark.parametrize(
    ("entrave", "expected"),
    [
        ("Aucune fermeture de voie\nRestrictions des véhicules hors normes en dimension", WORKS),
        ("En tout temps:\n- Route fermée entre la sortie 22 et le chemin Saint-Louis", CLOSED),
        ("Du dimanche au mercredi :\nCirculation en alternance, entre 0 h et 7 h\nROUTE FERMÉE, entre 7 h et 12 h", CLOSED),
        ("Fermeture des accotements, en tout temps", WORKS),
        ("Fermeture de 2 voies sur 3, en tout temps", LANES),
        ("Fermeture de la voie de virage à gauche", LANES),
        ("Fermeture de l'accotement en tout temps\nAu besoin:\n- Fermeture de très courte durée de la route", WORKS),
        ("Circulation sur voie rétrécie en tout temps\nAccès fermé:\n- Mercredi 11 novembre entre 19 h et 6 h", CLOSED),
        ("Fermeture du demi-tour en tout temps", WORKS),
    ],
)
def test_the_strongest_stated_effect_on_road_traffic_decides_the_type(entrave, expected):
    assert qc.event_type(entrave) == expected


def test_a_run_keeps_what_is_in_force_or_coming_and_drops_the_ended():
    records, connector, _ = fetch()
    assert len(connector.observed_ids) == 8
    assert "168170" not in {r.external_id for r in records} and len(records) == 7  # ended 05:00 that morning
    upcoming = {r.external_id for r in records if r.structured.start > NOW}
    assert {"168663", "166812", "155134"} <= upcoming


def test_segments_become_events_through_the_pipeline(session):
    from sqlalchemy import select

    from app.models import Event
    from app.repositories.ingestion_store import SqlIngestionStore
    from app.repositories.sources import SourceRepository
    from services.extraction import KeywordClassifier
    from services.ingestion import run_ingestion

    source = qc.quebec_mtmd_source(scheduled=True)
    _, connector, _ = fetch()
    SourceRepository(session).sync_registry([source])
    session.commit()
    result = run_ingestion(connector, KeywordClassifier.from_file(), SqlIngestionStore(session), None, get_city("canada"))
    session.commit()
    events = list(session.scalars(select(Event).where(Event.source_id == qc.SOURCE_ID)))
    assert result.events_created == len(events) == 7
    assert all(e.geometry and e.start_time and e.end_time for e in events)
    assert {e.event_type for e in events} == {CLOSED, LANES, WORKS}
