"""Official records that disappear from a feed (6 October 2026).

Absence from a refresh is not proof that an event has ended. It is counted;
after ABSENCE_REVIEW_AFTER refreshes the event is flagged for a reviewer;
nothing is expired or cancelled. A source that explicitly reports a record
cleared is a real status change.
"""

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models import Event
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from app.services.source_revision import ABSENCE_REVIEW_AFTER
from connectors.official import tfl_source
from connectors.official.tfl import revision_key, to_record
from packages.cities import get_city
from services.extraction import KeywordClassifier
from services.ingestion import run_ingestion
from tests.support import FakeConnector


@pytest.fixture(autouse=True)
def _no_minimum_length(monkeypatch):
    """These tests use the real 28 m Toronto closure in the fixtures to test
    something else; the 200 m minimum is tested in test_road_block_minimum.py."""
    monkeypatch.setattr("packages.source_models.road_block.MIN_ROAD_BLOCK_LENGTH_M", 0)


FIXTURE = Path(__file__).parents[1] / "fixtures" / "tfl_road_disruptions_2026-10-06.json"
RECORDS = json.loads(FIXTURE.read_text(encoding="utf-8"))["records"]
WORKS = next(r for r in RECORDS if r["id"] == "TIMS-235412")
OTHER = next(r for r in RECORDS if r["id"] == "TIMS-235733")
NOW = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
LONDON = get_city("london")
SOURCE = tfl_source(scheduled=False)


class Refresh(FakeConnector):
    """A TfL-like refresh: some records, and the ids the feed listed."""

    def __init__(self, records, observed):
        super().__init__([to_record(r, NOW) for r in records], source=SOURCE)
        self.observed_ids = set(observed)

    @staticmethod
    def revision_key(raw):
        return revision_key(raw)


def refresh(session, records, observed):
    result = run_ingestion(
        Refresh(records, observed), KeywordClassifier.for_city(LONDON), SqlIngestionStore(session), None, LONDON
    )
    session.commit()
    return result


def event_for(session, external_id) -> Event:
    session.expire_all()
    return next(e for e in session.scalars(select(Event)).unique() if e.source_reference.endswith(external_id))


@pytest.fixture
def london(session):
    SourceRepository(session).sync_registry([SOURCE])
    session.commit()
    refresh(session, [WORKS, OTHER], {"TIMS-235412", "TIMS-235733"})
    return session


def test_a_listed_record_is_marked_as_seen(london):
    observation = event_for(london, "TIMS-235412").detection["observation"]
    assert observation["missed_refreshes"] == 0 and observation["last_seen_at"]
    assert observation["review_required"] is False


def test_a_missing_record_is_counted_not_ended(london):
    refresh(london, [OTHER], {"TIMS-235733"})
    event = event_for(london, "TIMS-235412")
    observation = event.detection["observation"]
    assert observation["missed_refreshes"] == 1 and observation["missing_since"]
    assert observation["review_required"] is False
    # Nothing ended: same status, same end, no new version.
    assert event.status == "VALIDATION_REQUIRED"
    assert event.end_time.isoformat().startswith("2026-11-07")
    assert event.version == 1


def test_after_the_threshold_it_is_flagged_for_review_once(london):
    for _ in range(ABSENCE_REVIEW_AFTER + 2):
        refresh(london, [OTHER], {"TIMS-235733"})
    event = event_for(london, "TIMS-235412")
    assert event.detection["observation"]["review_required"] is True
    assert event.detection["observation"]["missed_refreshes"] == ABSENCE_REVIEW_AFTER + 2
    assert event.status == "VALIDATION_REQUIRED"
    flags = [v for v in event.versions if "Not listed by the source" in (v.change_reason or "")]
    assert len(flags) == 1 and "Not taken as ended" in flags[0].change_reason


def test_a_record_that_comes_back_lifts_the_flag(london):
    for _ in range(ABSENCE_REVIEW_AFTER):
        refresh(london, [OTHER], {"TIMS-235733"})
    refresh(london, [WORKS, OTHER], {"TIMS-235412", "TIMS-235733"})
    event = event_for(london, "TIMS-235412")
    assert event.detection["observation"] == {
        **event.detection["observation"], "missed_refreshes": 0, "review_required": False, "missing_since": None,
    }  # fmt: skip
    assert "lifted" in event.versions[-1].change_reason


def test_a_record_left_out_only_by_the_run_limit_is_still_seen(london):
    """The run keeps 30 records; the feed listing the rest still counts as seeing them."""
    refresh(london, [OTHER], {"TIMS-235412", "TIMS-235733"})
    assert event_for(london, "TIMS-235412").detection["observation"]["missed_refreshes"] == 0


def test_an_explicitly_cleared_record_is_a_real_status_change(london):
    cleared = copy.deepcopy(WORKS)
    cleared.update(status="Recently Cleared", lastModifiedTime="2026-10-07T08:00:00Z")
    result = refresh(london, [cleared, OTHER], {"TIMS-235412", "TIMS-235733"})
    assert result.revised == 1
    event = event_for(london, "TIMS-235412")
    assert event.detection["source_reports_ended"] is True
    assert event.detection["source_status"] == "Recently Cleared"
    assert "the source now reports it ended" in event.detection["source_revision"]["changes"]


def test_a_decided_event_that_the_source_clears_is_flagged_not_changed(london):
    event = event_for(london, "TIMS-235412")
    event.status = "APPROVED"
    london.commit()
    cleared = copy.deepcopy(WORKS)
    cleared.update(status="Recently Cleared")
    refresh(london, [cleared], {"TIMS-235412"})
    event = event_for(london, "TIMS-235412")
    assert event.status == "APPROVED"
    assert "the source now reports it ended" in event.detection["pending_source_revision"]["changes"]
