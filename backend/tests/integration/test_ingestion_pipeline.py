import pytest
from sqlalchemy import func, select, text

from app.models import Event, EventVersion, SourceArtifact
from app.repositories.ingestion_store import SqlIngestionStore
from connectors.base import ConnectorError
from services.extraction import KeywordClassifier
from services.ingestion import run_ingestion
from tests.support import FakeConnector


@pytest.fixture(scope="module")
def classifier() -> KeywordClassifier:
    return KeywordClassifier.from_file()


def count(session, model) -> int:
    return session.scalar(select(func.count()).select_from(model))


def ingest(session, records, classifier):
    result = run_ingestion(FakeConnector(records), classifier, SqlIngestionStore(session))
    session.commit()
    return result


def test_first_run_stores_evidence_for_every_article_and_events_for_relevant_ones(
    session, records, classifier
):
    result = ingest(session, records, classifier)

    # 7 parsed items, one of them a repeat of the first within the same feed.
    assert result.fetched == 7
    assert result.new_artifacts == 6
    assert result.duplicates == 1
    assert result.relevant == 3
    assert result.events_created == 3

    assert count(session, SourceArtifact) == 6
    assert count(session, Event) == 3
    labels = dict(
        session.execute(
            select(SourceArtifact.classification, func.count()).group_by(SourceArtifact.classification)
        ).all()
    )
    assert labels == {"RELEVANT_TRAFFIC_ARTICLE": 3, "NOT_RELEVANT": 3}


def test_same_articles_are_not_inserted_again(session, records, classifier):
    ingest(session, records, classifier)
    second = ingest(session, records, classifier)

    assert second.fetched == 7
    assert second.new_artifacts == 0
    assert second.duplicates == 7
    assert second.events_created == 0
    assert count(session, SourceArtifact) == 6
    assert count(session, Event) == 3


def test_only_new_articles_are_processed_on_a_later_run(session, records, classifier):
    ingest(session, records[:2], classifier)
    later = ingest(session, records, classifier)
    assert later.duplicates == 3  # the two already stored, plus the in-feed repeat
    assert later.new_artifacts == 4


def test_evidence_is_preserved_and_linked_to_the_event(session, records, classifier):
    ingest(session, records, classifier)
    event = session.scalars(
        select(Event).where(Event.title.startswith("Traffic diversions at Lakeview"))
    ).one()
    artifact = event.artifact

    assert event.source_artifact_id == artifact.artifact_id
    assert event.source_reference == artifact.url
    assert artifact.source_id == "test-news"
    assert artifact.external_id == "https://news.example.com/?p=1001"
    assert artifact.title == event.title
    assert artifact.published_at.isoformat() == "2026-10-01T06:30:00+00:00"
    assert artifact.retrieved_at.isoformat() == "2026-10-02T08:00:00+00:00"
    assert len(artifact.content_hash) == 64
    # The original markup, exactly as received.
    assert "<p>Motorists heading towards Station Road" in artifact.raw_content["summary_html"]
    assert artifact.classification_details["matched_keywords"]
    assert artifact.classification_details["method"] == "keyword_rules"


def test_stored_event_requires_validation_and_has_no_invented_fields(session, records, classifier):
    ingest(session, records, classifier)
    for event in session.scalars(select(Event)):
        assert event.status == "VALIDATION_REQUIRED"

        assert event.geometry is None
        assert event.start_time is None
        assert event.end_time is None
        assert event.severity is None
        assert event.confidence is None


def test_missing_geometry_is_stored_as_sql_null(session, records, classifier):
    # Not as the JSON literal `null`: on PostgreSQL the PostGIS geometry column
    # is generated from this value and cannot parse `null` as a geometry.
    ingest(session, records, classifier)
    assert session.scalar(text("SELECT count(*) FROM events WHERE geometry IS NULL")) == 3


def test_event_creation_is_recorded_as_version_one(session, records, classifier):
    ingest(session, records, classifier)
    versions = session.scalars(select(EventVersion)).all()
    assert len(versions) == 3
    for version in versions:
        assert version.version == 1
        assert version.status == "VALIDATION_REQUIRED"
        assert version.changed_by == "ingestion"
        assert version.snapshot["event_id"] == version.event_id


def test_failed_fetch_stores_nothing(session, classifier):
    connector = FakeConnector([], error="feed unreachable")
    with pytest.raises(ConnectorError):
        run_ingestion(connector, classifier, SqlIngestionStore(session))
    assert count(session, SourceArtifact) == 0
    assert count(session, Event) == 0
