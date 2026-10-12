"""Official sources revise their records (6 October 2026).

A revision is kept as evidence alongside the original (append-only), and the
event follows the source while it is still in review. A reviewer's work is
never overridden: an extended end and a corrected location stay, and an
approved or rejected event is only flagged.
"""

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models import Event, SourceArtifact, SourceArtifactRevision
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from app.services.reprocess_service import record_from_artifact, reprocess_stored_evidence
from connectors.official import tfl_source
from connectors.official.tfl import to_record
from packages.cities import get_city
from services.extraction import KeywordClassifier
from services.ingestion import run_ingestion
from tests.support import FakeConnector, khajaguda_article


@pytest.fixture(autouse=True)
def _no_minimum_length(monkeypatch):
    """These tests use the real 28 m Toronto closure in the fixtures to test
    something else; the 200 m minimum is tested in test_road_block_minimum.py."""
    monkeypatch.setattr("packages.source_models.road_block.MIN_ROAD_BLOCK_LENGTH_M", 0)


FIXTURE = Path(__file__).parents[1] / "fixtures" / "tfl_road_disruptions_2026-10-06.json"
WORKS = next(
    record
    for record in json.loads(FIXTURE.read_text(encoding="utf-8"))["records"]
    if record["id"] == "TIMS-235412"
)
NOW = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
LONDON = get_city("london")
SOURCE = tfl_source(scheduled=False)


def revised(**changes):
    disruption = copy.deepcopy(WORKS)
    disruption.update(changes)
    return disruption


def run(session, *disruptions):
    result = run_ingestion(
        FakeConnector([to_record(item, NOW) for item in disruptions], source=SOURCE),
        KeywordClassifier.for_city(LONDON),
        SqlIngestionStore(session),
        None,
        LONDON,
    )
    session.commit()
    return result


@pytest.fixture
def london(session):
    SourceRepository(session).sync_registry([SOURCE])
    session.commit()
    run(session, WORKS)
    return session


def the_event(session) -> Event:
    return session.scalars(select(Event)).unique().one()


LATER = revised(endDateTime="2026-11-20T18:00:00Z", lastModifiedTime="2026-10-07T08:00:00Z")


def test_an_unchanged_record_is_a_duplicate(london):
    result = run(london, WORKS)
    assert (result.duplicates, result.revised, result.new_artifacts) == (1, 0, 0)


def test_a_revised_record_is_kept_as_evidence_beside_the_original(london):
    result = run(london, LATER)
    assert (result.revised, result.duplicates, result.new_artifacts) == (1, 0, 0)
    artifact = london.scalars(select(SourceArtifact)).one()
    # The original is untouched; the revision is added.
    assert artifact.raw_content["disruption"]["endDateTime"] == WORKS["endDateTime"]
    [revision] = artifact.revisions
    assert revision.revision == 2
    assert revision.raw_content["disruption"]["endDateTime"] == "2026-11-20T18:00:00Z"
    assert artifact.latest is revision and artifact.revision_count == 2
    # Seen again, the revision is not stored twice.
    again = run(london, LATER)
    assert (again.revised, again.duplicates) == (0, 1)
    assert london.scalars(select(SourceArtifactRevision)).all() == [revision]


def test_an_event_in_review_follows_the_source(london):
    run(london, LATER)
    event = the_event(london)
    assert event.end_time == datetime(2026, 11, 20, 18, 0, tzinfo=timezone.utc)
    assert event.status == "VALIDATION_REQUIRED"
    note = event.detection["source_revision"]
    assert note["revision"] == 2
    assert note["changes"] == ["end 2026-11-07 18:00 UTC → 2026-11-20 18:00 UTC"]
    last = event.versions[-1]
    assert last.changed_by == "source-update" and "revision 2" in last.change_reason
    assert event.version == 2


def test_a_reviewers_extension_and_correction_are_kept(london):
    from app.services.review_service import extend_event, set_event_location
    from services.geo_resolution import resolver_for

    event = the_event(london)
    extend_event(london, event.event_id, datetime(2026, 12, 31).date(), "Seen still closed on site")
    set_event_location(
        london, resolver_for(LONDON), event.event_id,
        longitude=-0.12, latitude=51.5, place_name="The works entrance", reason="Seen on site",
    )  # fmt: skip
    run(london, revised(endDateTime="2026-11-20T18:00:00Z", severity="Serious",
                        lastModifiedTime="2026-10-07T08:00:00Z"))  # fmt: skip
    event = the_event(london)
    # The reviewer's end and spot stay; the source's other changes apply.
    assert event.end_time.date().isoformat() == "2026-12-31"
    assert event.geometry["coordinates"] == [-0.12, 51.5]
    assert event.detection["location_class"] == "HUMAN_CORRECTED"
    assert event.detection["period_revision"]["reason"] == "Seen still closed on site"
    assert event.detection["source_severity"] == "Serious"


@pytest.mark.parametrize("status", ["REJECTED", "APPROVED"])
def test_a_decided_event_is_flagged_not_changed(london, status):
    event = the_event(london)
    event.status = status
    london.commit()
    run(london, LATER)
    event = the_event(london)
    assert event.status == status
    assert event.end_time == datetime(2026, 11, 7, 18, 0, tzinfo=timezone.utc)
    pending = event.detection["pending_source_revision"]
    assert pending["revision"] == 2 and pending["changes"]
    assert "for a reviewer to decide" in event.versions[-1].change_reason


def test_a_revision_that_changes_nothing_shown_adds_no_version(london):
    # Only TfL's own last-modified time changed: new evidence, same event.
    run(london, revised(lastModifiedTime="2026-10-07T08:00:00Z"))
    event = the_event(london)
    assert event.version == 1 and event.detection.get("source_revision") is None
    assert len(london.scalars(select(SourceArtifactRevision)).all()) == 1


def test_reprocessing_reads_the_latest_version_and_keeps_the_note(london):
    run(london, LATER)
    artifact = london.scalars(select(SourceArtifact)).one()
    assert record_from_artifact(artifact).structured.end == datetime(
        2026, 11, 20, 18, 0, tzinfo=timezone.utc
    )
    result = reprocess_stored_evidence(london, KeywordClassifier.for_city(LONDON), None,
                                       tools_for_source=lambda _: (KeywordClassifier.for_city(LONDON), None, LONDON))  # fmt: skip
    assert result.updated == 0
    event = the_event(london)
    assert event.detection["source_revision"]["revision"] == 2
    assert event.end_time == datetime(2026, 11, 20, 18, 0, tzinfo=timezone.utc)


def test_news_articles_are_not_treated_as_revisions(session):
    """A publisher editing an article is unchanged behaviour: the first version stands."""
    from connectors.rss.telangana_today import TELANGANA_TODAY

    SourceRepository(session).sync_registry([TELANGANA_TODAY])
    session.commit()
    article = khajaguda_article()
    store = SqlIngestionStore(session)
    run_ingestion(FakeConnector([article], source=TELANGANA_TODAY), KeywordClassifier.from_file(), store)
    edited = article.model_copy(update={"content_hash": "f" * 64, "summary": "Edited."})
    result = run_ingestion(
        FakeConnector([edited], source=TELANGANA_TODAY), KeywordClassifier.from_file(), store
    )
    assert (result.duplicates, result.revised) == (1, 0)
    assert session.scalars(select(SourceArtifactRevision)).all() == []


class TflLikeConnector(FakeConnector):
    """A fixed-records connector that knows, as the TfL connector does, which fields are content."""

    @staticmethod
    def revision_key(raw):
        from connectors.official.tfl import revision_key

        return revision_key(raw)


def test_a_touch_without_a_change_of_content_is_not_a_revision(london):
    touched = revised(lastModifiedTime="2026-10-07T08:00:00Z", currentUpdateDateTime="2026-10-07T08:00:00Z", ordinal="9")
    result = run_ingestion(
        TflLikeConnector([to_record(touched, NOW)], source=SOURCE),
        KeywordClassifier.for_city(LONDON), SqlIngestionStore(london), None, LONDON,
    )  # fmt: skip
    assert (result.duplicates, result.revised) == (1, 0)
    changed = revised(endDateTime="2026-11-20T18:00:00Z", lastModifiedTime="2026-10-07T09:00:00Z")
    result = run_ingestion(
        TflLikeConnector([to_record(changed, NOW)], source=SOURCE),
        KeywordClassifier.for_city(LONDON), SqlIngestionStore(london), None, LONDON,
    )  # fmt: skip
    assert result.revised == 1
