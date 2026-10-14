"""Bring in one article that a connected source's feed no longer carries:

    python backend/cli/backfill.py <source_id> <article URL>

For example a long-running closure announced before REI began polling. The
article is read from its own page (see connectors/html/article.py), stored as
evidence and put through the same detection as a feed item. It becomes an
event only if the rules detect one, and that event still needs validation.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BACKEND_DIR)]

from app.core.config import get_settings  # noqa: E402
from app.core.database import create_db_engine, create_session_factory, run_migrations  # noqa: E402
from app.services.ingestion_service import IngestionService, UnknownSource  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    source_id, url = sys.argv[1:]
    settings = get_settings()
    if settings.auto_migrate:
        run_migrations(settings.database_url)
    service = IngestionService(
        create_session_factory(create_db_engine(settings.database_url)), settings
    )
    try:
        result = service.ingest_article(source_id, url)
    except UnknownSource:
        sys.exit(f"'{source_id}' is not a connected source")
    if result.status != "ok":
        sys.exit(f"Failed: {result.error}")
    print(
        f"{source_id}: {result.new_artifacts} article stored, {result.duplicates} already held, "
        f"{result.events_created} event created"
    )
