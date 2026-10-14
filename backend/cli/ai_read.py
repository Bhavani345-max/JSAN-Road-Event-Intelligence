"""Read stored news articles with the configured language model (OpenRouter):

    python backend/cli/ai_read.py                  # read what is waiting, within today's limit
    python backend/cli/ai_read.py --status         # what is waiting and how many requests are left
    python backend/cli/ai_read.py --max-requests 5 # stop after five requests
    python backend/cli/ai_read.py --days 7         # also read articles stored in the last 7 days
    python backend/cli/ai_read.py --all-days       # every stored article (several days on a free key)

The API does the same in the background every AI_TICK_SECONDS while it runs.
Each answer is checked against its article before it is used, and events are
re-derived exactly as reprocessing does: an event a person has touched is
never changed. See docs/decisions/0020-ai-reading-of-articles.md.
"""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BACKEND_DIR)]

from app.core.config import get_settings  # noqa: E402
from app.core.database import create_db_engine, create_session_factory, run_migrations  # noqa: E402
from app.services.ai_reading_service import AiReadingService  # noqa: E402
from app.services.ingestion_service import IngestionService  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--status", action="store_true", help="show what is waiting and stop")
    parser.add_argument("--max-requests", type=int, default=None)
    parser.add_argument("--days", type=int, default=None, help="read articles stored within this many days")
    parser.add_argument("--all-days", action="store_true", help="read every stored article")
    args = parser.parse_args()

    settings = get_settings()
    if settings.auto_migrate:
        run_migrations(settings.database_url)
    session_factory = create_session_factory(create_db_engine(settings.database_url))
    ingestion = IngestionService(session_factory, settings)
    service = AiReadingService(session_factory, settings, ingestion)

    if args.status:
        print(json.dumps(service.status(), indent=2))
        sys.exit(0)
    if not service.configured:
        sys.exit("AI reading is off: set OPENROUTER_API_KEY and AI_MODEL in .env")

    days = None if args.all_days else (args.days if args.days is not None else -1)
    result = service.run(max_requests=args.max_requests, lookback_days=days)
    print(json.dumps(asdict(result), indent=2))
    sys.exit(1 if result.error else 0)
