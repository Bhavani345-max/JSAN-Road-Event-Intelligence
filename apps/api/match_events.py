"""Compare every open event with the others of its city:

    python apps/api/match_events.py            # merge clear duplicates, record the rest
    python apps/api/match_events.py --dry-run  # only report what would happen

Clearly the same events (the same article twice; or the same type, stated
period and place) with nothing conflicting and no reviewer involved are merged:
linked, never deleted. Everything that may be the same becomes a candidate for
a reviewer. Pairs already decided are not proposed again.
"""

import argparse
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent
sys.path[:0] = [str(API_DIR.parents[1]), str(API_DIR)]

from app.core.config import get_settings  # noqa: E402
from app.core.database import create_db_engine, create_session_factory, run_migrations  # noqa: E402
from app.services.merge_service import find_candidates  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Match events across sources")
    parser.add_argument("--dry-run", action="store_true", help="report only; change nothing")
    args = parser.parse_args()
    settings = get_settings()
    if settings.auto_migrate:
        run_migrations(settings.database_url)
    with create_session_factory(create_db_engine(settings.database_url))() as session:
        run = find_candidates(session, automatic=True)
        if args.dry_run:
            session.rollback()
        else:
            session.commit()
    print(
        f"{run.compared} pairs compared: {run.candidates} possible matches recorded, "
        f"{run.auto_merged} merged automatically" + (" (dry run: nothing saved)" if args.dry_run else "")
    )
    for example in run.examples:
        print("  merged:", example)
