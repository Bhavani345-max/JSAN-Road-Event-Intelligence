"""Set aside AI readings made with the wrong rules, and re-derive the events they rejected.

    python backend/cli/correct_ai_readings.py IDS.json --reason "..."            # check only
    python backend/cli/correct_ai_readings.py IDS.json --reason "..." --apply
    python backend/cli/correct_ai_readings.py IDS.json --reason "..." --undo --apply

IDS.json holds {"artifacts": [artifact ids], "events": [event ids]}: the exact
records, listed beforehand. Without --apply nothing is saved: the command
prints what it would change. --undo puts the readings back (with the
classification they were set aside with) and rejects the restored events
again, each as a new version. Nothing is ever deleted (decision 0033).
"""

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BACKEND_DIR)]

from app.core.config import get_settings  # noqa: E402
from app.core.database import create_db_engine, create_session_factory  # noqa: E402
from app.services.ai_reading_correction import (  # noqa: E402
    rederive_events,
    reject_again,
    restore_readings,
    supersede_readings,
)
from app.services.ingestion_service import IngestionService  # noqa: E402
from packages.common.time import utc_now  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ids_file")
    parser.add_argument("--reason", required=True)
    parser.add_argument("--apply", action="store_true", help="save the changes (default: check only)")
    parser.add_argument("--undo", action="store_true", help="put back what an earlier --apply changed")
    args = parser.parse_args()

    ids = json.loads(Path(args.ids_file).read_text(encoding="utf-8"))
    settings = get_settings()
    session_factory = create_session_factory(create_db_engine(settings.database_url))
    service = IngestionService(session_factory, settings)
    print("database:", settings.database_url.split("@")[-1])
    with session_factory() as session:
        if args.undo:
            events = reject_again(session, ids["events"], reason=f"Correction undone: {args.reason}")
            readings = restore_readings(session, ids["artifacts"], reason=args.reason)
        else:
            readings = supersede_readings(session, ids["artifacts"], reason=args.reason, at=utc_now())
            session.flush()
            events = rederive_events(
                session, service, ids["events"], reason=f"keyword rules ({args.reason})"
            )
        print(f"readings {'restored' if args.undo else 'set aside'}: {len(readings.changed)}; "
              f"skipped: {len(readings.skipped)} {dict(list(readings.skipped.items())[:5])}")
        print(f"events {'rejected again' if args.undo else 'restored'}: {events.changed}; "
              f"skipped: {events.skipped}")
        if args.apply:
            session.commit()
            print("saved")
        else:
            session.rollback()
            print("check only: nothing saved (add --apply)")


if __name__ == "__main__":
    main()
