import asyncio
import logging

from .ingestion_service import IngestionService

logger = logging.getLogger(__name__)


async def poll_sources_forever(service: IngestionService, tick_seconds: int) -> None:
    """Background loop: every tick, ingest the sources that are due.

    An in-process loop is enough for one API instance. With several instances
    this moves to a dedicated worker so sources are not polled more than once.
    """
    while True:
        try:
            await asyncio.to_thread(service.run_due)
        except Exception:
            # Never let one bad run stop future polling.
            logger.exception("Scheduled ingestion run failed")
        await asyncio.sleep(tick_seconds)


async def read_articles_forever(service, tick_seconds: int) -> None:
    """Background loop: every tick, let the AI reader read waiting articles.

    It stops by itself for the day when the day's request limit is used.
    """
    while True:
        try:
            await asyncio.to_thread(service.run)
        except Exception:
            logger.exception("Scheduled AI reading failed")
        await asyncio.sleep(tick_seconds)
