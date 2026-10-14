"""Several sources through the one ingestion pipeline and evidence store."""

import pytest
from sqlalchemy import func, select

from app.models import Event, SourceArtifact
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from services.extraction import KeywordClassifier
from services.ingestion import run_ingestion
from tests.support import SOURCE_FIXTURES, FakeConnector, parse_fixture

# source id -> (artifacts, events) expected from its fixture feed
EXPECTED = {
    "telangana-today": (6, 3),
    "the-hindu": (5, 2),
    "deccan-chronicle": (5, 2),
    "newsmeter": (5, 2),
    "the-hans-india": (5, 2),
}


@pytest.fixture(scope="module")
def classifier() -> KeywordClassifier:
    return KeywordClassifier.from_file()


@pytest.fixture
def news_session(session):
    SourceRepository(session).sync_registry(source for source, _ in SOURCE_FIXTURES)
    session.commit()
    return session


def ingest_all(session, classifier):
    results = {}
    for source, filename in SOURCE_FIXTURES:
        connector = FakeConnector(parse_fixture(source, filename), source=source)
        results[source.source_id] = run_ingestion(connector, classifier, SqlIngestionStore(session))
        session.commit()
    return results


def per_source(session, model) -> dict[str, int]:
    return dict(session.execute(select(model.source_id, func.count()).group_by(model.source_id)).all())


def test_articles_and_events_are_stored_under_their_own_source(news_session, classifier):
    results = ingest_all(news_session, classifier)

    for source_id, (artifacts, events) in EXPECTED.items():
        assert results[source_id].new_artifacts == artifacts, source_id
        assert results[source_id].events_created == events, source_id
    assert per_source(news_session, SourceArtifact) == {k: v[0] for k, v in EXPECTED.items()}
    assert per_source(news_session, Event) == {k: v[1] for k, v in EXPECTED.items()}


def test_every_source_keeps_the_same_evidence(news_session, classifier):
    ingest_all(news_session, classifier)
    artifacts = news_session.scalars(select(SourceArtifact)).all()
    assert len(artifacts) == sum(stored for stored, _ in EXPECTED.values())
    for artifact in artifacts:
        assert artifact.source_id in EXPECTED
        assert artifact.external_id
        assert artifact.url.startswith("https://")
        assert artifact.title
        assert artifact.retrieved_at is not None
        assert len(artifact.content_hash) == 64
        assert {"guid", "link", "title", "summary_html", "content_html"} <= set(artifact.raw_content)
        assert artifact.classification in {"RELEVANT_TRAFFIC_ARTICLE", "NOT_RELEVANT"}
    # Publication time is kept wherever the feed gave a valid one (one item of
    # news_feed_sample.xml has none).
    assert sum(1 for artifact in artifacts if artifact.published_at is None) == 1


def test_event_stays_linked_to_its_source_and_original_article(news_session, classifier):
    ingest_all(news_session, classifier)
    for event in news_session.scalars(select(Event)):
        assert event.status == "VALIDATION_REQUIRED"
        assert event.artifact.source_id == event.source_id
        assert event.source.source_id == event.source_id
        assert event.source_reference == event.artifact.url
        assert event.title == event.artifact.title


def test_repeated_polling_of_every_source_adds_nothing(news_session, classifier):
    ingest_all(news_session, classifier)
    second = ingest_all(news_session, classifier)

    for source_id, result in second.items():
        assert result.new_artifacts == 0, source_id
        assert result.events_created == 0, source_id
        assert result.duplicates == result.fetched, source_id
    assert per_source(news_session, SourceArtifact) == {k: v[0] for k, v in EXPECTED.items()}
    assert per_source(news_session, Event) == {k: v[1] for k, v in EXPECTED.items()}


def test_similar_reports_from_different_sources_are_not_merged(news_session, classifier):
    """Two papers reporting what may be one real-world event stay two events."""
    ingest_all(news_session, classifier)
    lakeview = news_session.scalars(
        select(Event).where(Event.title.ilike("%traffic diversions at lakeview junction%"))
    ).all()
    assert sorted(event.source_id for event in lakeview) == [
        "deccan-chronicle",
        "newsmeter",
        "telangana-today",
        "the-hans-india",
    ]
    assert len({event.event_id for event in lakeview}) == 4
    assert len({event.source_artifact_id for event in lakeview}) == 4


def test_the_same_item_id_in_two_sources_is_two_separate_artifacts(news_session, classifier):
    """Duplicate detection is per source: an id only has meaning within its source."""
    (first_source, filename), (second_source, _) = SOURCE_FIXTURES[0], SOURCE_FIXTURES[1]
    record = parse_fixture(first_source, filename)[0]
    twin = record.model_copy(update={"source_id": second_source.source_id})

    for source, item in ((first_source, record), (second_source, twin)):
        run_ingestion(FakeConnector([item], source=source), classifier, SqlIngestionStore(news_session))
    news_session.commit()

    stored = news_session.scalars(
        select(SourceArtifact).where(SourceArtifact.external_id == record.external_id)
    ).all()
    assert sorted(artifact.source_id for artifact in stored) == ["telangana-today", "the-hindu"]
    assert news_session.scalar(select(func.count()).select_from(Event)) == 2
