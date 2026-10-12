"""Run one connected source now:

    python apps/api/ingest_source.py tfl-road-disruptions
    python apps/api/ingest_source.py toronto-road-restrictions

For sources that are connected but not scheduled (the official feeds of the
international test cities). The run is recorded on the source like a
scheduled poll; items already held are not stored again.
"""

import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent
sys.path[:0] = [str(API_DIR.parents[1]), str(API_DIR)]

from app.core.config import get_settings  # noqa: E402
from app.core.database import create_db_engine, create_session_factory, run_migrations  # noqa: E402
from app.repositories.sources import SourceRepository  # noqa: E402
from app.services.ingestion_service import IngestionService, UnknownSource  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    source_id = sys.argv[1]
    settings = get_settings()
    if settings.auto_migrate:
        run_migrations(settings.database_url)
    session_factory = create_session_factory(create_db_engine(settings.database_url))
    service = IngestionService(session_factory, settings)
    with session_factory() as session:
        SourceRepository(session).sync_registry(s.definition for s in service.sources)
        session.commit()
    try:
        result = service.run_source(source_id)
    except UnknownSource:
        sys.exit(f"'{source_id}' is not a connected source")
    if result.status != "ok":
        sys.exit(f"Failed: {result.error}")
    print(
        f"{source_id}: {result.fetched} records kept for this run, {result.new_artifacts} new, "
        f"{result.duplicates} already held unchanged, {result.revised} revised by the source, "
        f"{result.events_created} events created "
        "(all awaiting validation)"
    )
