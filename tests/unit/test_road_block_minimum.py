"""No length filter (brief of 8 October 2026, section 8; decision 0018).

A road block is kept at whatever length its source draws: 20 m is 20 m. The
length of the source's own geometry is measured and recorded on the event
for the reviewer, never used to drop it. Decision 0016's 200 m minimum is
withdrawn; a closure it rejected comes back on reprocessing.
"""

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from connectors.official import TorontoRoadRestrictionsConnector, toronto_source
from connectors.official.toronto import to_record
from packages.cities import get_city
from packages.geo_models import distance_m, line_length_m
from packages.source_models import (
    MIN_ROAD_BLOCK_LENGTH_M,
    SourceEvent,
    SourceLocation,
    source_length_m,
    too_short_road_block,
)
from services.extraction import ArticleRelevance, build_event_from_source, classify_source_record

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
FIXTURE = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "toronto_road_restrictions_2026-10-06.json").read_text(encoding="utf-8")
)
# The real record: "Ln E Strachan N King 29 m North of King St W to King St W", 28 m long.
SHORT_CLOSURE = next(item for item in FIXTURE["Closure"] if item["type"] == "ROAD_CLOSED")
TORONTO = get_city("toronto")


def toronto_item(polyline: str, *, special_event: str = "No", record_id: str = "Tor-TEST-1") -> dict:
    """The real closure record with another line (test data)."""
    item = copy.deepcopy(SHORT_CLOSURE)
    item.update(id=record_id, geoPolyline=polyline, specialEvent=special_event,
                startTime=str(int(NOW.timestamp() * 1000)), endTime=str(int(NOW.timestamp() * 1000) + 86_400_000))  # fmt: skip
    return item


# Along King St W: 0.003 degrees of longitude at 43.64 N is about 241 m.
LONG_LINE = "[-79.4000,43.6400],[-79.3970,43.6400]"
SHORT_LINE = "[-79.4000,43.6400],[-79.3998,43.6400]"


def test_lengths_are_measured_on_the_ground():
    assert distance_m((0, 0), (0, 1)) == pytest.approx(111_195, rel=1e-3)
    assert line_length_m({"type": "LineString", "coordinates": [[-79.4, 43.64], [-79.397, 43.64]]}) == pytest.approx(241, abs=2)
    assert line_length_m({"type": "Point", "coordinates": [-79.4, 43.64]}) is None


def test_there_is_no_minimum_length():
    assert MIN_ROAD_BLOCK_LENGTH_M == 0
    record = to_record(SHORT_CLOSURE, NOW)
    assert too_short_road_block(record.structured) is None
    classification = classify_source_record(record, TORONTO)
    assert classification.label is ArticleRelevance.SOURCE_PROVIDED_EVENT
    assert classification.is_relevant


def test_the_real_28_m_closure_is_an_event_with_its_exact_line_and_measured_length():
    record = to_record(SHORT_CLOSURE, NOW)
    event = build_event_from_source(record, classify_source_record(record, TORONTO), now=NOW)
    assert event is not None
    assert event.geometry.type == "LineString"
    assert [list(p) for p in event.geometry.coordinates] == json.loads(f"[{SHORT_CLOSURE['geoPolyline']}]")
    # Measured on the City's own line, for the reviewer; nothing is extended.
    assert event.detection.source_geometry_length_m == pytest.approx(28, abs=2)
    assert source_length_m(record.structured) == pytest.approx(28, abs=2)


def test_a_source_that_draws_no_line_has_no_length():
    event = SourceEvent(event_type="ROAD_WORKS", locations=[SourceLocation(name="Street", closure="Closed")])
    assert source_length_m(event) is None


def test_closed_stretches_are_summed_when_the_event_itself_is_an_area():
    event = SourceEvent(
        event_type="ROAD_WORKS",
        geometry={"type": "Polygon", "coordinates": [[[-0.1, 51.5], [-0.09, 51.5], [-0.09, 51.51], [-0.1, 51.5]]]},
        locations=[
            SourceLocation(name="A", closure="Closed", geometry={"type": "MultiLineString", "coordinates": [[[-0.1, 51.5], [-0.0995, 51.5]]]}),
            SourceLocation(name="B", closure="Open", geometry={"type": "MultiLineString", "coordinates": [[[-0.11, 51.5], [-0.107, 51.5]]]}),
        ],
    )  # fmt: skip
    assert source_length_m(event) == pytest.approx(35, abs=2)


def test_the_connector_keeps_short_closures():
    feed = {"Closure": [toronto_item(SHORT_LINE, record_id="Tor-SHORT"), toronto_item(LONG_LINE, record_id="Tor-LONG")]}
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=feed)))
    connector = TorontoRoadRestrictionsConnector(
        toronto_source(scheduled=False), "ua", client=client, clock=lambda: NOW, max_records=5
    )
    assert {record.external_id for record in connector.fetch()} == {"Tor-SHORT", "Tor-LONG"}
    assert connector.observed_ids == {"Tor-SHORT", "Tor-LONG"}


def test_a_closure_rejected_under_the_old_minimum_comes_back_on_reprocessing(session, monkeypatch):
    from sqlalchemy import select

    from app.models import Event
    from app.repositories.ingestion_store import SqlIngestionStore
    from app.repositories.sources import SourceRepository
    from app.services.reprocess_service import reprocess_stored_evidence
    from services.extraction import KeywordClassifier
    from services.ingestion import run_ingestion
    from tests.support import FakeConnector

    source = toronto_source(scheduled=False)
    SourceRepository(session).sync_registry([source])
    record = to_record(toronto_item(SHORT_LINE), NOW)
    run_ingestion(FakeConnector([record], source=source), KeywordClassifier.from_file(), SqlIngestionStore(session), None, TORONTO)
    session.commit()
    classifier = KeywordClassifier.from_file()
    tools = lambda _: (classifier, None, TORONTO)  # noqa: E731

    # Under decision 0016 (7 October) reprocessing rejected it for its length.
    monkeypatch.setattr("packages.source_models.road_block.MIN_ROAD_BLOCK_LENGTH_M", 200)
    rejected = reprocess_stored_evidence(session, classifier, None, tools_for_source=tools)
    assert rejected.rejected == 1
    event = session.scalars(select(Event)).one()
    assert event.status == "REJECTED"
    assert event.versions[-1].change_reason == "Road block 16 m long, under the 200 m minimum"
    monkeypatch.undo()

    # With the minimum withdrawn it is an event again; nothing was deleted.
    restored = reprocess_stored_evidence(session, classifier, None, tools_for_source=tools)
    assert restored.restored == 1 and restored.rejected == 0
    event = session.scalars(select(Event)).one()
    assert event.status == "VALIDATION_REQUIRED"
    assert event.detection["source_geometry_length_m"] == pytest.approx(16, abs=1)
