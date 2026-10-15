"""Every registered source fits the sources table's column limits.

PostgreSQL (production) refuses a value longer than its column; SQLite (the
tests and local runs) does not check. On 15 October 2026 a parser name of 34
characters in a 32-character column stopped the production API at startup.
"""

import pytest
from sqlalchemy import String

from app.models import Source
from connectors.registry import registered_sources

LIMITS = {
    column.name: column.type.length
    for column in Source.__table__.columns
    if isinstance(column.type, String) and column.type.length
}


@pytest.mark.parametrize(
    "registered",
    registered_sources(official_feeds_scheduled=True, google_news_rss_enabled=True, serper_api_key="test"),
    ids=lambda registered: registered.definition.source_id,
)
def test_every_source_value_fits_its_column(registered):
    values = registered.definition.model_dump(mode="json")
    too_long = {
        name: f"{len(str(values[name]))} > {limit}"
        for name, limit in LIMITS.items()
        if values.get(name) is not None and len(str(values[name])) > limit
    }
    assert not too_long, too_long


def test_events_and_evidence_of_the_new_feeds_fit_their_columns(session):
    """The real samples of the feeds connected on 15 October 2026, stored and checked
    value by value against each table's column limits (PostgreSQL enforces them)."""
    from sqlalchemy import select

    from app.models import Event, EventVersion, SourceArtifact
    from app.repositories.ingestion_store import SqlIngestionStore
    from app.repositories.sources import SourceRepository
    from packages.cities import get_city
    from services.extraction import KeywordClassifier
    from services.ingestion import run_ingestion
    from tests.support import FakeConnector
    from tests.unit.test_country_sources import MODULES, records

    by_id = {s.definition.source_id: s.definition for s in registered_sources()}
    SourceRepository(session).sync_registry(by_id[source_id] for source_id in MODULES)
    session.commit()
    for source_id, (_, city) in MODULES.items():
        _, found = records(source_id)
        run_ingestion(
            FakeConnector([record for _, record in found], source=by_id[source_id]),
            KeywordClassifier.for_city(get_city(city)), SqlIngestionStore(session), None, get_city(city),
        )  # fmt: skip
        session.commit()
    too_long = []
    for model in (Event, SourceArtifact, EventVersion):
        limits = {
            column.name: column.type.length
            for column in model.__table__.columns
            if isinstance(column.type, String) and column.type.length
        }
        for row in session.scalars(select(model)).unique():
            for name, limit in limits.items():
                value = getattr(row, name)
                if value is not None and len(str(value)) > limit:
                    too_long.append((model.__tablename__, name, len(str(value)), limit))
    assert session.scalar(select(Event.event_id)) is not None
    assert not too_long, too_long[:10]
