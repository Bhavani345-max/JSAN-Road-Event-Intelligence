"""Tokushima Prefecture road restrictions (decision 0034), on real files saved 16 October 2026.

No test reaches the portal: both files are served to the connector.
"""

from datetime import datetime, timezone
from pathlib import Path

import httpx

from connectors.official.tokushima import (
    POINTS_URL,
    RESTRICTIONS_URL,
    TokushimaRoadRestrictionsConnector,
    fetch_restrictions,
    to_record,
    tokushima_source,
)
from connectors.registry import OFFICIAL_SOURCE_IDS, get_registered_source
from packages.cities import get_city
from packages.event_schema import EventType
from packages.source_models import CommercialUse, IntegrationStatus
from services.ingestion.pipeline import classify

FIXTURES = Path(__file__).parents[1] / "fixtures"
NOW = datetime(2026, 10, 16, 12, 30, tzinfo=timezone.utc)


def client():
    files = {
        RESTRICTIONS_URL: (FIXTURES / "tokushima_restrictions_2026-10-16.xml").read_bytes(),
        POINTS_URL: (FIXTURES / "tokushima_points_2026-10-16.xml").read_bytes(),
    }
    return httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=files[str(request.url)])))


def items():
    return fetch_restrictions("ua", client=client())


def test_each_restriction_is_read_with_its_point_road_and_stated_times():
    found = items()
    assert len(found) == 82 and all(item["point"] for item in found)
    record = to_record(next(item for item in found if item["rid"] == "29255"), NOW)
    assert record.title == "Lane restriction: National Route 11, 徳島県徳島市川内町 (Tokushima)"
    assert record.structured.geometry == {"type": "Point", "coordinates": [134.5708765, 34.09394794]}
    assert record.structured.event_type == EventType.LANE_RESTRICTION.value
    # Japan Standard Time, as written: 2026/03/16 10:00 – 2026/11/27 15:00.
    assert record.structured.start == datetime(2026, 3, 16, 1, 0, tzinfo=timezone.utc)
    assert record.structured.end == datetime(2026, 11, 27, 6, 0, tzinfo=timezone.utc)
    assert record.structured.direction is None  # 下り (outbound) is not a compass direction
    assert "(outbound)" in record.structured.locations[0].name
    assert "土曜、日曜を除く" in record.structured.stated_period  # the stated exceptions are kept
    assert record.raw["item"]["rid"] == "29255"


def test_the_type_comes_from_what_the_source_says_is_restricted():
    by_kind = {}
    for item in items():
        record = to_record(item, NOW)
        by_kind.setdefault(item["rc"], set()).add(record.structured.event_type if record else "not taken")
    for kind in ("全面通行止", "時間通行止", "車両通行止"):
        assert by_kind[kind] == {EventType.PLANNED_ROAD_CLOSURE.value}
    for kind in ("片側交互通行", "車線規制", "片側通行制限"):
        assert by_kind[kind] == {EventType.LANE_RESTRICTION.value}
    # A pavement restriction is not road traffic; height limits and "other" get no type invented.
    assert by_kind["歩道通行制限"] == {"not taken"}
    assert by_kind["高さ制限"] == {None} and by_kind["その他"] == {None}


def test_a_restriction_in_japan_is_an_official_source_event_kept_while_in_effect():
    connector = TokushimaRoadRestrictionsConnector(tokushima_source(scheduled=True), "ua", client=client(), clock=lambda: NOW)
    records = connector.fetch()
    assert records and all(r.structured.start for r in records)
    # The source writes 未定 ("not decided") for the end of a few: no end is invented,
    # the word is kept, and the official record runs until the source says it is over.
    open_ended = [r for r in records if r.structured.end is None]
    assert open_ended and all(r.raw["item"]["led"] == "未定" and "未定" in r.structured.stated_period for r in open_ended)
    assert {classify(r, None, get_city("japan")).label.value for r in records} == {"SOURCE_PROVIDED_EVENT"}


def test_it_is_a_connected_official_feed_run_by_hand_unless_scheduled():
    registered = get_registered_source("tokushima-road-restrictions")
    definition = registered.definition
    assert definition.integration_status is IntegrationStatus.CONNECTED and registered.create_connector
    assert definition.active is False and definition.source_id in OFFICIAL_SOURCE_IDS
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    assert definition.attribution.startswith("出典：徳島県オープンデータポータルサイト")


def test_restrictions_become_events_through_the_pipeline(session):
    from sqlalchemy import select

    from app.models import Event
    from app.repositories.ingestion_store import SqlIngestionStore
    from app.repositories.sources import SourceRepository
    from services.extraction import KeywordClassifier
    from services.ingestion import run_ingestion

    source = tokushima_source(scheduled=True)
    connector = TokushimaRoadRestrictionsConnector(source, "ua", client=client(), clock=lambda: NOW)
    SourceRepository(session).sync_registry([source])
    session.commit()
    result = run_ingestion(connector, KeywordClassifier.from_file(), SqlIngestionStore(session), None, get_city("japan"))
    session.commit()
    events = list(session.scalars(select(Event).where(Event.source_id == source.source_id)))
    assert result.events_created == len(events) > 0
    assert all(e.geometry and e.start_time and e.city == "Japan" for e in events)
    assert {e.direction for e in events} <= {"BOTH_DIRECTIONS", None}
