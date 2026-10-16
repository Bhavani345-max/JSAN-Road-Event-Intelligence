"""Re-derive events from the evidence already stored:

    python backend/cli/reprocess.py

Run it after a change to the detection rules, the place list or a city's
configuration, so that old and new articles are treated alike. Nothing is
fetched and no evidence is altered. Each artifact is read with the rules and
place list of its source's city. Events still awaiting validation are
re-derived (each change is a new version); ones the rules no longer support
are rejected, not deleted; a reviewer's decision is never touched.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BACKEND_DIR)]

from app.core.config import get_settings  # noqa: E402
from app.core.database import create_db_engine, create_session_factory, run_migrations  # noqa: E402
from app.services.ingestion_service import IngestionService  # noqa: E402
from app.services.reprocess_service import reprocess_stored_evidence  # noqa: E402

if __name__ == "__main__":
    settings = get_settings()
    if settings.auto_migrate:
        run_migrations(settings.database_url)
    session_factory = create_session_factory(create_db_engine(settings.database_url))
    service = IngestionService(session_factory, settings)
    with session_factory() as session:
        result = reprocess_stored_evidence(
            session,
            service.classifier,
            service.resolver,
            tools_for_source=service.tools_for_source,
            rebuild_for_source=service.rebuild_for_source,
            placer_for_source=service.placer_for_source,
        )
    print(
        f"{result.artifacts} stored articles read with rules {service.classifier.version}: "
        f"{result.created} events created, {result.updated} updated, "
        f"{result.rejected} rejected, {result.restored} restored, {result.unchanged} unchanged"
        + (f", {result.unknown_source} of unknown sources left as they are" if result.unknown_source else "")
    )
