import logging
import threading
from pathlib import Path
from collections.abc import Callable
from datetime import timedelta

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from app.schemas.source import IngestionResultOut
from app.services.retention_service import slim_unrelated_articles
from connectors.base import ConnectorError, SourceConnector
from connectors.html import ArticlePageConnector
from connectors.registry import registered_sources
from packages.cities import DEFAULT_CITY_ID, City, get_city, load_cities
from packages.common.time import utc_now
from services.extraction import KeywordClassifier
from services.extraction.keyword_classifier import DEFAULT_CONFIG_PATH
from services.geo_resolution import PlaceResolver, default_resolver, resolver_for
from services.geo_resolution.google_maps import GoogleMapsLookup
from services.geo_resolution.placement import Placer
from services.ingestion import IngestionResult, run_ingestion

logger = logging.getLogger(__name__)


class UnknownSource(Exception):
    pass


class IngestionService:
    """Runs the ingestion pipeline for registered sources and records the outcome."""

    def __init__(self, session_factory: sessionmaker[Session], settings: Settings) -> None:
        self._session_factory = session_factory
        self._user_agent = settings.http_user_agent
        # One classifier and one place resolver per configured city; each
        # source's city picks them. The default city's pair is also exposed as
        # `classifier` and `resolver` for tools that work on one city.
        self.cities = load_cities()
        self.resolvers: dict[str, PlaceResolver | None] = {
            city_id: resolver_for(city) for city_id, city in self.cities.items()
        }
        self.classifiers: dict[str, KeywordClassifier] = {
            city_id: (
                KeywordClassifier.from_file(
                    settings.traffic_keywords_path, self.resolvers[city_id], city
                )
                if settings.traffic_keywords_path
                else KeywordClassifier.for_city(city, self.resolvers[city_id])
            )
            for city_id, city in self.cities.items()
        }

        # How each city's events are placed: OpenStreetMap, and Google Maps for
        # names OSM cannot place when a Serper key is configured.
        self.google_maps = (
            GoogleMapsLookup(
                settings.serper_api_key,
                Path(settings.place_lookup_cache_path),
                daily_credits=settings.place_lookup_daily_credits,
            )
            if settings.place_lookup_google and settings.serper_api_key
            else None
        )
        self.placers: dict[str, Placer | None] = {
            city_id: (
                Placer.for_city(self.resolvers[city_id], city, self.google_maps)
                if self.resolvers[city_id] is not None
                else None
            )
            for city_id, city in self.cities.items()
        }

        # Every known source, connected or not, given the configured credentials.
        self.sources = registered_sources(
            settings.serper_api_key,
            settings.google_news_rss_enabled,
            official_feeds_scheduled=settings.official_feeds_scheduled,
            official_feed_max_records=settings.official_feed_max_records,
            tfl_app_key=settings.tfl_app_key,
        )
        # source_id -> how to build its connector. Replaceable in tests.
        self.connector_factories: dict[str, Callable[[], SourceConnector]] = {
            source.definition.source_id: (
                lambda create=source.create_connector: create(settings.http_user_agent)
            )
            for source in self.sources
            if source.create_connector is not None
        }
        # One run at a time: the scheduler and a manual run must not race to
        # insert the same articles.
        self._lock = threading.Lock()
        self._match_after = settings.event_matching_after_ingestion
        self._text_days = settings.unrelated_article_text_days

    def run_source(self, source_id: str) -> IngestionResultOut:
        if source_id not in self.connector_factories:
            raise UnknownSource(source_id)
        with self._lock, self._session_factory() as session:
            return self._run(session, source_id)

    def ingest_article(self, source_id: str, url: str) -> IngestionResultOut:
        """Bring in one article of a connected source that its feed no longer carries.

        The article is stored as evidence and goes through the same detection
        as a feed item. The source's polling record is left alone.
        """
        source = self.connected_source(source_id)
        return self.run_with_connector(
            ArticlePageConnector(source.definition, url, self._user_agent)
        )

    def connected_source(self, source_id: str):
        """The registered source, if it is one with a connector."""
        if source_id not in self.connector_factories:
            raise UnknownSource(source_id)
        return next(s for s in self.sources if s.definition.source_id == source_id)

    @property
    def lock(self) -> threading.Lock:
        """Held while writing derived data, so runs and the AI reader do not race."""
        return self._lock

    @property
    def classifier(self) -> KeywordClassifier:
        """The default city's classifier."""
        return self.classifiers[DEFAULT_CITY_ID]

    @classifier.setter
    def classifier(self, value: KeywordClassifier) -> None:
        self.classifiers[DEFAULT_CITY_ID] = value

    @property
    def resolver(self) -> PlaceResolver | None:
        """The default city's place resolver; None switches location off (tests)."""
        return self.resolvers[DEFAULT_CITY_ID]

    @resolver.setter
    def resolver(self, value: PlaceResolver | None) -> None:
        self.resolvers[DEFAULT_CITY_ID] = value

    def rebuild_for_source(self, source_id: str) -> Callable | None:
        """How the source's connector re-reads a stored item's structured fields, if it can."""
        factory = self.connector_factories.get(source_id)
        if factory is None:
            return None
        return getattr(factory(), "rebuild_structured", None)

    def tools_for_source(
        self, source_id: str
    ) -> tuple[KeywordClassifier, PlaceResolver | None, City]:
        """The classifier, resolver and city a source's items are processed with."""
        source = next((s for s in self.sources if s.definition.source_id == source_id), None)
        city_id = (source.definition.city if source else None) or DEFAULT_CITY_ID
        if city_id not in self.cities:
            raise UnknownSource(f"{source_id}: its city {city_id!r} is not configured")
        return self.classifiers[city_id], self.resolvers[city_id], get_city(city_id)

    def placer_for_source(self, source_id: str) -> Placer | None:
        """How a source's events are placed on the map (its city's placer)."""
        _, resolver, city = self.tools_for_source(source_id)
        placer = self.placers.get(city.id)
        # Tests replace the resolver; a placer is then made for the one in use.
        if resolver is None:
            return None
        if placer is None or placer.resolver is not resolver:
            return Placer.for_city(resolver, city, self.google_maps)
        return placer

    def run_with_connector(self, connector: SourceConnector) -> IngestionResultOut:
        """Run the pipeline once with a connector built for the occasion.

        For one-off reads (an article by its address, a deeper search sweep)
        that go through the same evidence storage, detection and review as a
        poll, but leave the source's polling record alone.
        """
        source_id = connector.source.source_id
        classifier, resolver, city = self.tools_for_source(source_id)
        started_at = utc_now()
        with self._lock, self._session_factory() as session:
            try:
                result = run_ingestion(
                    connector, classifier, SqlIngestionStore(session), resolver, city,
                    placer=self.placer_for_source(source_id),
                )
            except ConnectorError as error:
                session.rollback()
                return IngestionResultOut(
                    source_id=source_id,
                    status="failed",
                    error=str(error),
                    started_at=started_at,
                    finished_at=utc_now(),
                )
            session.commit()
            self._match(session, result)
            return self._to_out(result)

    def run_all_active(self) -> list[IngestionResultOut]:
        return [self.run_source(source_id) for source_id in self._active_source_ids()]

    def run_due(self) -> list[IngestionResultOut]:
        """Poll every active source whose polling interval has elapsed."""
        now = utc_now()
        with self._session_factory() as session:
            due = [
                source.source_id
                for source in SourceRepository(session).list()
                if self._is_pollable(source)
                and (
                    source.last_poll_at is None
                    or source.polling_frequency_minutes is None
                    or now - source.last_poll_at
                    >= timedelta(minutes=source.polling_frequency_minutes)
                )
            ]
        results = [self.run_source(source_id) for source_id in due]
        if results:
            self.apply_retention()
        return results

    def apply_retention(self) -> None:
        """Remove the text of old articles that are not road events (stubs remain)."""
        if self._text_days <= 0:
            return
        with self._lock, self._session_factory() as session:
            slimmed = slim_unrelated_articles(session, older_than_days=self._text_days)
        if slimmed.articles:
            logger.info(
                "Retention: removed the text of %d old articles that are not road events (%d KB)",
                slimmed.articles, slimmed.bytes_removed // 1024,
            )  # fmt: skip

    def _active_source_ids(self) -> list[str]:
        with self._session_factory() as session:
            return [
                source.source_id
                for source in SourceRepository(session).list()
                if self._is_pollable(source)
            ]

    def _is_pollable(self, source) -> bool:
        """Connected, switched on, and something knows how to read it."""
        return (
            source.active
            and source.integration_status == "CONNECTED"
            and source.source_id in self.connector_factories
        )

    def _run(self, session: Session, source_id: str) -> IngestionResultOut:
        started_at = utc_now()
        try:
            connector = self.connector_factories[source_id]()
            classifier, resolver, city = self.tools_for_source(source_id)
            result = run_ingestion(
                connector, classifier, SqlIngestionStore(session), resolver, city,
                placer=self.placer_for_source(source_id),
            )
        except ConnectorError as error:
            session.rollback()
            logger.warning("Ingestion failed for %s: %s", source_id, error)
            self._record_poll(session, source_id, error=str(error))
            return IngestionResultOut(
                source_id=source_id,
                status="failed",
                error=str(error),
                started_at=started_at,
                finished_at=utc_now(),
            )

        self._record_poll(session, source_id, error=None)
        self._match(session, result)
        return self._to_out(result)

    def _match(self, session: Session, result: IngestionResult) -> None:
        """Compare the run's new events with the open events of their city."""
        if not self._match_after or not result.event_ids:
            return
        from app.services.merge_service import find_candidates

        try:
            run = find_candidates(session, event_ids=result.event_ids)
            session.commit()
            if run.candidates:
                logger.info(
                    "%s: %d possible matches recorded, %d merged automatically",
                    result.source_id, run.candidates, run.auto_merged,
                )  # fmt: skip
        except Exception:
            # Matching must never lose a run's evidence or events.
            session.rollback()
            logger.exception("Matching after %s failed; the run itself is kept", result.source_id)

    @staticmethod
    def _to_out(result: IngestionResult) -> IngestionResultOut:
        return IngestionResultOut(
            source_id=result.source_id,
            status="ok",
            fetched=result.fetched,
            new_artifacts=result.new_artifacts,
            duplicates=result.duplicates,
            revised=result.revised,
            relevant=result.relevant,
            events_created=result.events_created,
            started_at=result.started_at,
            finished_at=result.finished_at,
        )

    @staticmethod
    def _record_poll(session: Session, source_id: str, *, error: str | None) -> None:
        """Update the source's polling state and commit the run."""
        source = SourceRepository(session).get(source_id)
        now = utc_now()
        if source is not None:
            source.last_poll_at = now
            if error is None:
                source.last_success_at = now
                source.last_error = None
            else:
                source.last_failure_at = now
                source.last_error = error
        session.commit()
