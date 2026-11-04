"""Correcting stored AI dates that miss the article's weekday (4 November 2026).

Reproduces EVT-DAB920541B01 on an in-memory database: an article published on
Monday 2 November says "restrictions on Monday ... between 1 pm and 7 pm"; a
reading made before the weekday check dated it Tuesday 3 November. The recheck
finds it and re-derives the event with Monday's date, as a new version.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.main import create_app
from app.models import Event, SourceArtifact
from app.repositories.sources import SourceRepository
from app.services.ai_reading_correction import readings_with_wrong_weekdays, recheck_weekdays
from app.services.reprocess_service import AI_CHANGED_BY, rederive_artifact
from connectors.rss.telangana_today import TELANGANA_TODAY
from packages.common.hashing import sha256_hex
from packages.source_models import RawSourceRecord
from tests.support import FakeConnector

PUBLISHED = datetime(2026, 11, 2, 4, 51, tzinfo=timezone.utc)  # Monday, 10:21 in Hyderabad
TITLE = "Hyderabad traffic diversions on Monday for BJP padayatra; check affected routes"
SUMMARY = (
    "Hyderabad commuters are likely to face traffic restrictions on Monday as the Hyderabad Traffic "
    "Police implement diversions for a BJP padayatra from BJR Statue to MJ Market. Restrictions will "
    "remain in force on several key roads and junctions between 1 pm and 7 pm."
)
# The reading as the model gave it before the check: Tuesday instead of Monday.
OLD_READING = {
    "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
    "prompt_version": "test",
    "read_at": "2026-11-02T06:00:00Z",
    "stage": "full",
    "is_road_event": True,
    "in_scope": True,
    "intent": "PUBLIC_PROCESSION",
    "places": [{"name": "MJ Market", "role": "AFFECTED", "quote": "to MJ Market", "found_in": "summary"}],
    "period_text": "between 1 pm and 7 pm",
    "period_read_by": "ai",
    "start_time": "2026-11-03T13:00:00+05:30",
    "end_time": "2026-11-03T19:00:00+05:30",
}


def padayatra_article() -> RawSourceRecord:
    raw = {"title": TITLE, "summary_html": SUMMARY, "content_html": "", "categories": []}
    return RawSourceRecord(
        source_id="telangana-today",
        external_id="https://telangana.example.com/padayatra",
        url="https://telangana.example.com/padayatra",
        title=TITLE,
        summary=SUMMARY,
        content_text=None,
        categories=[],
        published_at=PUBLISHED,
        retrieved_at=PUBLISHED,
        raw=raw,
        content_hash=sha256_hex(TITLE + SUMMARY),
    )


@pytest.fixture
def app(engine, session):
    SourceRepository(session).sync_registry([TELANGANA_TODAY])
    session.commit()
    settings = Settings(
        _env_file=None,
        database_url="sqlite://",
        auto_migrate=False,
        ingestion_scheduler_enabled=False,
        event_matching_after_ingestion=False,
    )
    app = create_app(settings, engine=engine)
    service = app.state.ingestion_service
    service.connector_factories = {
        "telangana-today": lambda: FakeConnector([padayatra_article()], source=TELANGANA_TODAY)
    }
    service.run_source("telangana-today")
    return app


def _event_from_the_old_reading(app) -> str:
    """The event as the older code left it: the AI reading's Tuesday."""
    service = app.state.ingestion_service
    with app.state.session_factory() as session:
        artifact = session.scalar(select(SourceArtifact))
        artifact.classification_details = {**(artifact.classification_details or {}), "ai": OLD_READING}
        row = session.scalar(select(Event).where(Event.source_artifact_id == artifact.artifact_id))
        classifier, resolver, city = service.tools_for_source(artifact.source_id)
        _, event_id = rederive_artifact(
            session, artifact, row, classifier=classifier, resolver=resolver, city=city,
            reason="AI reading (test)", changed_by=AI_CHANGED_BY,
        )  # fmt: skip
        session.flush()
        event = session.get(Event, event_id)
        # Older code kept the model's Tuesday.
        event.start_time = datetime(2026, 11, 3, 7, 30, tzinfo=timezone.utc)
        event.end_time = datetime(2026, 11, 3, 13, 30, tzinfo=timezone.utc)
        session.commit()
        return event_id


def test_the_recheck_finds_the_reading_and_moves_the_event_to_monday(app):
    event_id = _event_from_the_old_reading(app)
    service = app.state.ingestion_service
    with app.state.session_factory() as session:
        found = readings_with_wrong_weekdays(session, service)
        assert [(row.event_id, "not a Monday" in note) for _, row, note in found] == [(event_id, True)]

        versions_before = len(session.get(Event, event_id).versions)
        result = recheck_weekdays(session, service, reason="AI dates checked against the weekday")
        session.commit()
        assert result.changed == [event_id]

    with app.state.session_factory() as session:
        event = session.get(Event, event_id)
        assert event.start_time.replace(tzinfo=timezone.utc) == datetime(2026, 11, 2, 7, 30, tzinfo=timezone.utc)
        assert event.end_time.replace(tzinfo=timezone.utc) == datetime(2026, 11, 2, 13, 30, tzinfo=timezone.utc)
        assert len(event.versions) == versions_before + 1
        assert event.versions[-1].changed_by == AI_CHANGED_BY
        assert any("not a Monday" in note for note in event.detection["ai"]["discarded"])
        # The stored reading is kept as the model gave it.
        artifact = session.get(SourceArtifact, event.source_artifact_id)
        assert artifact.classification_details["ai"]["start_time"].startswith("2026-11-03")

    # Run again: nothing left to correct.
    with app.state.session_factory() as session:
        result = recheck_weekdays(session, service, reason="again")
        assert result.changed == [] and list(result.skipped.values()) == ["re-derivation gave 'unchanged'"]
