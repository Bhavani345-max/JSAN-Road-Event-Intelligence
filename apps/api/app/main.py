import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Engine

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.database import create_db_engine, create_session_factory, run_migrations
from app.services.bootstrap import sync_reference_data
from app.services.auth_service import seed_admin_user
from app.services.ingestion_service import IngestionService
from app.services.ai_reading_service import AiReadingService
from app.services.scheduler import poll_sources_forever, read_articles_forever

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app(settings: Settings | None = None, engine: Engine | None = None) -> FastAPI:
    """Build the API. Tests pass their own settings and database engine."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.auto_migrate:
            run_migrations(settings.database_url)
        with app.state.session_factory() as session:
            if settings.seed_admin_email and settings.seed_admin_password:
                user, created = seed_admin_user(
                    session, settings.seed_admin_email, settings.seed_admin_password
                )
                session.commit()
                logging.getLogger(__name__).info(
                    "Bootstrap reviewer %s (%s)",
                    user.email,
                    "created" if created else "already present",
                )
            elif settings.seed_admin_email or settings.seed_admin_password:
                logging.getLogger(__name__).warning(
                    "Bootstrap reviewer skipped: set both SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD."
                )
            sync_reference_data(session, app.state.ingestion_service.sources)

        poller = None
        if settings.ingestion_scheduler_enabled:
            poller = asyncio.create_task(
                poll_sources_forever(
                    app.state.ingestion_service, settings.ingestion_scheduler_tick_seconds
                )
            )
        reader = None
        ai = app.state.ai_reading_service
        if settings.ingestion_scheduler_enabled and settings.ai_reading_enabled and ai.configured:
            reader = asyncio.create_task(read_articles_forever(ai, settings.ai_tick_seconds))
        elif not ai.configured:
            logging.getLogger(__name__).info(
                "AI reading is off: set OPENROUTER_API_KEY and AI_MODEL to switch it on."
            )
        yield
        for task in (poller, reader):
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    app = FastAPI(
        title="JSAN Road Event Intelligence API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.state.session_factory = create_session_factory(
        engine or create_db_engine(settings.database_url)
    )
    app.state.ingestion_service = IngestionService(app.state.session_factory, settings)
    app.state.ai_reading_service = AiReadingService(
        app.state.session_factory, settings, app.state.ingestion_service
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        allow_credentials=True,
    )
    app.include_router(api_router)
    return app


app = create_app()
