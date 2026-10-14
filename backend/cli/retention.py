"""Remove the text of old articles that are not road events (a stub remains):
    python backend/cli/retention.py                 # what would be removed (nothing is changed)
    python backend/cli/retention.py --apply         # remove it
    python backend/cli/retention.py --apply --vacuum   # and shrink the SQLite file (API stopped)
    python backend/cli/retention.py --days 30 ...   # another age than UNRELATED_ARTICLE_TEXT_DAYS

The API does this by itself after each scheduled poll. Events, their evidence
and their history are never touched; see app/services/retention_service.py.
"""

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BACKEND_DIR)]

from sqlalchemy import text  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import create_db_engine, create_session_factory, run_migrations  # noqa: E402
from app.services.retention_service import slim_unrelated_articles  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--apply", action="store_true", help="change the database (default: only report)")
    parser.add_argument("--vacuum", action="store_true", help="SQLite: give the freed space back to the disk")
    args = parser.parse_args()

    settings = get_settings()
    days = args.days if args.days is not None else settings.unrelated_article_text_days
    if days <= 0:
        sys.exit("Retention is off (UNRELATED_ARTICLE_TEXT_DAYS=0); pass --days.")
    if settings.auto_migrate:
        run_migrations(settings.database_url)
    engine = create_db_engine(settings.database_url)
    with create_session_factory(engine)() as session:
        result = slim_unrelated_articles(session, older_than_days=days, dry_run=not args.apply)
    verb = "Removed" if args.apply else "Would remove"
    print(
        f"{verb} the text of {result.articles} articles that are not road events and are "
        f"older than {days} days ({result.bytes_removed / 1e6:.2f} MB)."
    )
    if args.apply and args.vacuum:
        if engine.dialect.name != "sqlite":
            sys.exit("--vacuum is for the local SQLite database; PostgreSQL reclaims space itself.")
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(text("VACUUM"))
        print("Database file compacted.")
