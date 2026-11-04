"""Check stored AI dates against the weekday the article names, and correct the events they gave.

    python backend/cli/recheck_ai_weekdays.py            # check only: lists what would change
    python backend/cli/recheck_ai_weekdays.py --apply    # re-derive those events

A model counting weekdays from the publication day sometimes lands on the
wrong day ("diversions on Monday" dated Tuesday). Readings made since
4 November 2026 are checked as they are read; this corrects the events of
readings made before (services/extraction/stated_weekday.py). Without --apply
nothing is saved. With it, each corrected event gets a new version (every
earlier one is kept); an event a person has touched is never changed.
"""

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BACKEND_DIR)]

from app.core.config import get_settings  # noqa: E402
from app.core.database import create_db_engine, create_session_factory  # noqa: E402
from app.services.ai_reading_correction import readings_with_wrong_weekdays, recheck_weekdays  # noqa: E402
from app.services.ingestion_service import IngestionService  # noqa: E402

REASON = "AI dates checked against the weekday the article names"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="save the corrections (default: check only)")
    args = parser.parse_args()

    settings = get_settings()
    session_factory = create_session_factory(create_db_engine(settings.database_url))
    service = IngestionService(session_factory, settings)
    with session_factory() as session:
        found = readings_with_wrong_weekdays(session, service)
        for artifact, row, note in found:
            where = f"{row.event_id} ({row.status})" if row else f"article {artifact.artifact_id} (no event)"
            print(f"{where}: {note}")
        print(f"{len(found)} stored reading(s) with a date off the article's weekday")
        if not args.apply:
            print("Check only: nothing saved. Run again with --apply to correct the events.")
            return
        result = recheck_weekdays(session, service, reason=REASON)
        session.commit()
    print(f"Corrected {len(result.changed)} event(s): {', '.join(result.changed) or '-'}")
    for key, why in result.skipped.items():
        print(f"  not changed {key}: {why}")


if __name__ == "__main__":
    main()
