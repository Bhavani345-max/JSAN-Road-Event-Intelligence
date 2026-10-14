"""Compare every open event with the others of its city:

    python backend/cli/match_events.py              # merge clear duplicates, record the rest
    python backend/cli/match_events.py --dry-run    # only report what would happen
    python backend/cli/match_events.py --rows-only  # only merge rows a source lists for one event

First, the rows an official source lists for one event (NYC DOT: a block's
closure once per permit purpose) are merged into one event. Then clearly the
same events (the same article twice; or the same type, stated period and
place) with nothing conflicting and no reviewer involved are merged: linked,
never deleted. Everything that may be the same becomes a candidate for a
reviewer. Pairs already decided are not proposed again.
"""

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BACKEND_DIR)]

from app.core.config import get_settings  # noqa: E402
from app.core.database import create_db_engine, create_session_factory, run_migrations  # noqa: E402
from app.services.merge_service import (  # noqa: E402
    LISTED_IN_SEVERAL_ROWS,
    MatchRun,
    find_candidates,
    merge_listed_rows,
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Match events across sources")
    parser.add_argument("--dry-run", action="store_true", help="report only; change nothing")
    parser.add_argument(
        "--rows-only",
        action="store_true",
        help="only merge the rows a source lists for one event; compare nothing else",
    )
    args = parser.parse_args()
    settings = get_settings()
    if settings.auto_migrate:
        run_migrations(settings.database_url)
    with create_session_factory(create_db_engine(settings.database_url))() as session:
        for source_id in LISTED_IN_SEVERAL_ROWS:
            listed = merge_listed_rows(session, source_id)
            print(
                f"{source_id}: {listed.auto_merged} rows merged into the event the source lists "
                f"them for, {listed.candidates} left for a reviewer"
            )
            for example in listed.examples[:5]:
                print("  merged:", example)
        run = MatchRun() if args.rows_only else find_candidates(session, automatic=True)
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
