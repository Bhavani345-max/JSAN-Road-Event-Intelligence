"""Bison Futé's records of one situation at one spot become one event (decision 0029).

Fixture: four real situations from the live DATEX II file of 15 October 2026.
In three, every record has the same position and period (works, the closure
they need, a hazard ...); in the fourth, the records are at different spots.
"""

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from app.models import Event
from app.repositories.events import to_rei_event
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from app.services import merge_service
from connectors.official.bison_fute import (
    BisonFuteRoadEventsConnector,
    bison_fute_source,
    same_situation_key,
)
from packages.cities import get_city
from services.extraction import KeywordClassifier
from services.ingestion import run_ingestion

FIXTURE = Path(__file__).parents[1] / "fixtures" / "bison_fute_situations_2026-10-15.xml"
NOW = datetime(2026, 10, 15, 9, 0, tzinfo=timezone.utc)
FRANCE = get_city("france")
SOURCE = bison_fute_source(scheduled=False)
SAME_SPOT = {"260806-002455", "260820-002094", "260903-001790"}
SPLIT = "260403-004178"


def fetched():
    body = FIXTURE.read_bytes()
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=body)))
    return BisonFuteRoadEventsConnector(SOURCE, "test", client=client, clock=lambda: NOW)


@pytest.fixture
def france(session):
    SourceRepository(session).sync_registry([SOURCE])
    session.commit()
    run_ingestion(fetched(), KeywordClassifier.for_city(FRANCE), SqlIngestionStore(session), None, FRANCE)
    session.commit()
    return session


def rows(session) -> list[Event]:
    session.expire_all()
    return session.scalars(select(Event).order_by(Event.created_at, Event.event_id)).unique().all()


def situation_of(row: Event) -> str:
    return row.artifact.external_id.split(":", 1)[0]


def key(row: Event) -> str | None:
    return same_situation_key(to_rei_event(row), row.artifact.external_id)


def test_the_records_of_a_situation_at_one_spot_share_a_key(france):
    every = rows(france)
    for situation in SAME_SPOT:
        keys = {key(row) for row in every if situation_of(row) == situation}
        assert len(keys) == 1 and None not in keys
    split = [key(row) for row in every if situation_of(row) == SPLIT]
    assert len(split) == len(set(split)) > 1


def test_a_situation_at_one_spot_becomes_one_event_and_every_record_is_kept(france):
    before = rows(france)
    run = merge_service.merge_listed_rows(france, SOURCE.source_id)
    france.commit()
    after = rows(france)
    assert len(after) == len(before)  # nothing deleted
    listed = [row for row in after if row.merged_into is None]
    per_situation = Counter(situation_of(row) for row in listed)
    assert all(per_situation[situation] == 1 for situation in SAME_SPOT)
    # Records at different spots stay separate events.
    assert per_situation[SPLIT] == sum(1 for row in before if situation_of(row) == SPLIT)
    assert run.auto_merged == len(before) - len(listed)
    # Each merged record points at its situation's event, which keeps its own period.
    events = {row.event_id: row for row in after}
    for row in after:
        if row.merged_into:
            canonical = events[row.merged_into]
            assert situation_of(canonical) == situation_of(row)
            assert (canonical.start_time, canonical.end_time) == (row.start_time, row.end_time)


def test_merging_situations_again_changes_nothing(france):
    merge_service.merge_listed_rows(france, SOURCE.source_id)
    france.commit()
    again = merge_service.merge_listed_rows(france, SOURCE.source_id)
    assert again.auto_merged == 0


def test_a_record_without_a_situation_or_period_is_never_grouped(france):
    row = rows(france)[0]
    event = to_rei_event(row)
    assert same_situation_key(event, "no-situation-separator") is None
    assert same_situation_key(event.model_copy(update={"end_time": None}), row.artifact.external_id) is None
    assert same_situation_key(event.model_copy(update={"geometry": None}), row.artifact.external_id) is None


def test_the_record_saying_most_about_the_road_leads_its_situation(france):
    """A closure leads the works needing it, a diversion or a hazard warning."""
    merge_service.merge_listed_rows(france, SOURCE.source_id)
    france.commit()
    order = ["PLANNED_ROAD_CLOSURE", "ROAD_WORKS", "TRAFFIC_DIVERSION", "ROAD_HAZARD"]
    every = rows(france)
    for situation in SAME_SPOT:
        records = [row for row in every if situation_of(row) == situation]
        lead = next(row for row in records if row.merged_into is None)
        best = min((row.event_type for row in records), key=lambda t: order.index(t) if t in order else 9)
        assert lead.event_type == best
