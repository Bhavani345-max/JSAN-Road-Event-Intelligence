"""Search Google News more deeply than the scheduled polls do:

    python backend/cli/search_sweep.py [--window month|year|week|day] [--results 10|20]

The scheduled polls search the past week. A sweep runs the same Hyderabad
road searches over a longer window (the past month by default), so that
measures announced earlier but still running are found. Every result goes
through the same article reading, evidence storage, detection and review as
a poll. Articles already held are not stored again.

Cost: one Serper credit per search for up to 10 results, two for 11-100. The
default sweep costs as many credits as one scheduled poll.
"""

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BACKEND_DIR)]

from app.core.config import get_settings  # noqa: E402
from app.core.database import create_db_engine, create_session_factory, run_migrations  # noqa: E402
from app.services.ingestion_service import IngestionService, UnknownSource  # noqa: E402
from connectors.api.serper_news import SOURCE_ID, WINDOWS, SerperNewsConnector  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sweep Google News for Hyderabad road events")
    parser.add_argument("--window", choices=sorted(WINDOWS), default="month")
    parser.add_argument("--results", type=int, choices=(10, 20, 30, 50, 100), default=10)
    args = parser.parse_args()

    settings = get_settings()
    if not settings.serper_api_key:
        sys.exit("SERPER_API_KEY is not set in .env, so the Google News search is not connected.")
    if settings.auto_migrate:
        run_migrations(settings.database_url)
    service = IngestionService(
        create_session_factory(create_db_engine(settings.database_url)), settings
    )
    try:
        source = service.connected_source(SOURCE_ID)
    except UnknownSource:
        sys.exit("The Google News search source is not connected.")
    connector = SerperNewsConnector(
        source.definition,
        settings.serper_api_key,
        settings.http_user_agent,
        window=WINDOWS[args.window],
        results_per_query=args.results,
    )
    credits = len(connector.queries) * (1 if args.results <= 10 else 2)
    print(f"Searching the past {args.window} ({credits} Serper credits)...")
    result = service.run_with_connector(connector)
    if result.status != "ok":
        sys.exit(f"Failed: {result.error}")
    print(
        f"{result.fetched} results, {result.new_artifacts} new articles stored, "
        f"{result.duplicates} already held, {result.relevant} detected as road articles, "
        f"{result.events_created} events created (all awaiting validation)"
    )
