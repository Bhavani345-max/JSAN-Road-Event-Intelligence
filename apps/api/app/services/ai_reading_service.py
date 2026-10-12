"""Reads stored news articles with a language model and applies what it finds.

Two passes keep within a free key's daily limit (50 requests on OpenRouter):

1. triage: about twenty headlines and summaries per request; the model says
   which articles report a road event, and of what kind;
2. full: the whole text of a few articles per request, only for those the
   triage pass called road events; the model returns the intent, impact,
   cause, the places with their roles, the period and the evidence.

Each answer is checked against the article (services/ai_reading/reading.py)
before it is stored with the article (classification_details["ai"]). The
article's event is then re-derived exactly as reprocessing does, so an event
a person has touched is never changed, and every change is a new version.

Nothing is sent for structured official records (they state their own type
and place), for manual entries, or for sources whose terms forbid it
(AI_EXCLUDED_SOURCES).
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import REPO_ROOT, Settings
from app.models import Event, SourceArtifact
from app.services.ingestion_service import IngestionService
from app.services.reprocess_service import AI_CHANGED_BY, record_from_artifact, rederive_artifact
from app.services.retention_service import is_stub
from packages.common.time import IST, utc_now
from packages.event_schema import AiReading
from services.ai_reading import (
    FULL,
    TRIAGE,
    AiConfig,
    AiError,
    ArticleText,
    OpenRouterClient,
    full_prompt,
    read_full_answer,
    read_triage_answer,
    triage_prompt,
)
from services.ai_reading.reading import DEFAULT_CONFIG_PATH
from services.extraction.ai_event import ROUTE_ROLES, resolve_place

logger = logging.getLogger(__name__)

DEFAULT_USAGE_PATH = REPO_ROOT / "apps" / "api" / ".data" / "ai_usage.json"
# Articles read by keywords, i.e. news text; official records and manual entries are not.
_TEXT_CLASSIFICATIONS = ("RELEVANT_TRAFFIC_ARTICLE", "NOT_RELEVANT")
# An article the model leaves out of its answer this many times is not sent again.
_MAX_UNANSWERED = 3
# Free requests left on the key that are never used automatically.
_RESERVE = 2


@dataclass
class AiRunResult:
    requests: int = 0
    triaged: int = 0
    road_events_in_triage: int = 0
    fully_read: int = 0
    road_events: int = 0
    events_created: int = 0
    events_updated: int = 0
    events_restored: int = 0
    events_rejected: int = 0
    stopped: str | None = None
    error: str | None = None
    models: list[str] = field(default_factory=list)


class AiUsage:
    """Requests sent today (UTC), kept in a small file so restarts do not reset it."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def _today(self) -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def used_today(self) -> int:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return 0
        return int(data.get("requests", 0)) if data.get("date") == self._today() else 0

    def add(self, requests: int) -> None:
        if requests <= 0:
            return
        total = self.used_today() + requests
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps({"date": self._today(), "requests": total}), encoding="utf-8"
            )
        except OSError:
            logger.warning("Could not record AI request usage in %s", self.path)


class AiReadingService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        settings: Settings,
        ingestion: IngestionService,
        *,
        client_factory=None,
        usage_path: Path | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._ingestion = ingestion
        self.config = AiConfig.from_file(settings.ai_reading_config_path or DEFAULT_CONFIG_PATH)
        self.usage = AiUsage(usage_path or DEFAULT_USAGE_PATH)
        self._excluded = settings.ai_excluded_source_ids
        self._client_factory = client_factory or self._openrouter

    # --- configuration -------------------------------------------------------------

    @property
    def configured(self) -> bool:
        return self._settings.ai_configured

    def _openrouter(self) -> OpenRouterClient:
        return OpenRouterClient(
            self._settings.openrouter_api_key or "",
            self._settings.ai_model or "",
            fallback_models=self._settings.ai_fallback_model_list,
            base_url=self._settings.openrouter_base_url,
            reasoning=self._settings.ai_reasoning,
        )

    # --- what is waiting -------------------------------------------------------------

    def _candidates(self, session: Session, lookback_days: int | None) -> list[SourceArtifact]:
        query = select(SourceArtifact).where(
            SourceArtifact.classification.in_(_TEXT_CLASSIFICATIONS)
        )
        if lookback_days is not None:
            query = query.where(
                SourceArtifact.created_at >= utc_now() - timedelta(days=lookback_days)
            )
        query = query.order_by(SourceArtifact.created_at.desc())
        return [
            artifact
            for artifact in session.scalars(query)
            if artifact.source_id not in self._excluded and not is_stub(artifact)
        ]

    def _stage_needed(self, artifact: SourceArtifact) -> str | None:
        """TRIAGE or FULL when the article still needs that pass, else None."""
        details = artifact.classification_details or {}
        if details.get("ai_unanswered", 0) >= _MAX_UNANSWERED and (
            details.get("ai_unanswered_version") in (self.config.version, self.config.full_version)
        ):
            return None
        stored = details.get("ai")
        if not stored:
            return TRIAGE
        if stored.get("stage") == TRIAGE:
            if stored.get("prompt_version") != self.config.version:
                return TRIAGE
            return FULL if stored.get("is_road_event") else None
        # A road event read in full with an older full-reading prompt is read again.
        if stored.get("prompt_version") != self.config.full_version and stored.get("is_road_event"):
            return FULL
        return None

    def pending(self, lookback_days: int | None) -> dict[str, list[str]]:
        """Artifact ids waiting for each pass, newest first."""
        waiting: dict[str, list[str]] = {TRIAGE: [], FULL: []}
        with self._session_factory() as session:
            for artifact in self._candidates(session, lookback_days):
                stage = self._stage_needed(artifact)
                if stage:
                    waiting[stage].append(artifact.artifact_id)
        return waiting

    def status(self) -> dict:
        waiting = self.pending(self._settings.ai_lookback_days)
        return {
            "configured": self.configured,
            "enabled": self._settings.ai_reading_enabled,
            "model": self._settings.ai_model,
            "fallback_models": self._settings.ai_fallback_model_list,
            "prompt_version": self.config.version,
            "requests_today": self.usage.used_today(),
            "daily_limit": self._settings.ai_daily_request_limit,
            "lookback_days": self._settings.ai_lookback_days,
            "waiting_for_triage": len(waiting[TRIAGE]),
            "waiting_for_full_reading": len(waiting[FULL]),
            "excluded_sources": sorted(self._excluded),
        }

    # --- running ---------------------------------------------------------------------

    def run(
        self, *, max_requests: int | None = None, lookback_days: int | None = -1
    ) -> AiRunResult:
        """Read waiting articles until none wait or the day's requests are used.

        `lookback_days` -1 uses the configured window; None reads every stored article.
        """
        result = AiRunResult()
        if not self.configured:
            result.stopped = "No OpenRouter key or model is configured."
            return result
        days = self._settings.ai_lookback_days if lookback_days == -1 else lookback_days

        allowed = self._settings.ai_daily_request_limit - self.usage.used_today()
        if max_requests is not None:
            allowed = min(allowed, max_requests)
        if allowed <= 0:
            result.stopped = "Today's AI request limit is used up."
            return result

        client = self._client_factory()
        try:
            remaining = client.free_requests_remaining()
            if remaining is not None:
                allowed = min(allowed, remaining - _RESERVE)
                if allowed <= 0:
                    result.stopped = f"The OpenRouter key has {remaining} free requests left today."
                    return result
            while True:
                waiting = self.pending(days)
                stage = FULL if waiting[FULL] else TRIAGE if waiting[TRIAGE] else None
                if stage is None:
                    result.stopped = "Every article in the window has been read."
                    break
                if client.requests_sent >= allowed:
                    result.stopped = "The request budget for this run is used."
                    break
                size = self.config.full["batch_size"] if stage == FULL else self.config.triage["batch_size"]
                batch = waiting[stage][:size]
                before = client.requests_sent
                try:
                    self._read_batch(client, stage, batch, result)
                except AiError:
                    # The model answered, but not usably: count it against these
                    # articles so a batch that keeps failing is set aside after a
                    # few tries instead of using up the day's requests.
                    if client.requests_sent > before:
                        self._mark_unanswered(batch)
                    raise
                finally:
                    self.usage.add(client.requests_sent - before)
                    result.requests = client.requests_sent
        except AiError as error:
            result.error = str(error)
            logger.warning("AI reading stopped: %s", error)
        finally:
            close = getattr(client, "close", None)
            if close:
                close()
        logger.info(
            "AI reading: %d requests, %d triaged (%d road events), %d read in full "
            "(%d road events), events %d created, %d updated. %s",
            result.requests, result.triaged, result.road_events_in_triage, result.fully_read,
            result.road_events, result.events_created, result.events_updated,
            result.error or result.stopped or "",
        )  # fmt: skip
        return result

    def _articles(self, session: Session, artifact_ids: list[str]) -> list[tuple[ArticleText, tuple]]:
        rows = {
            artifact.artifact_id: artifact
            for artifact in session.scalars(
                select(SourceArtifact).where(SourceArtifact.artifact_id.in_(artifact_ids))
            )
        }
        articles = []
        for artifact_id in artifact_ids:
            artifact = rows.get(artifact_id)
            if artifact is None:
                continue
            record = record_from_artifact(artifact)
            tools = self._ingestion.tools_for_source(artifact.source_id)
            articles.append(
                (
                    ArticleText(
                        key=f"a{len(articles) + 1}",
                        artifact_id=artifact_id,
                        title=record.title,
                        summary=record.summary,
                        body=record.content_text,
                        published_at=record.published_at,
                        city=tools[2],
                    ),
                    tools,
                )
            )
        return articles

    def _read_batch(
        self, client, stage: str, artifact_ids: list[str], result: AiRunResult
    ) -> None:
        with self._session_factory() as session:
            prepared = self._articles(session, artifact_ids)
        if not prepared:
            raise AiError("The articles waiting to be read could not be loaded.")
        articles = [article for article, _ in prepared]
        tools = {article.artifact_id: tool for article, tool in prepared}
        today = datetime.now(IST).date()
        now = utc_now()

        if stage == TRIAGE:
            answer = client.chat_json(
                self.config.triage["system"],
                triage_prompt(self.config, articles, today),
                max_tokens=self.config.triage["max_tokens"],
            )
            readings = read_triage_answer(
                self.config, answer.content, articles, model=answer.model, now=now
            )
            result.triaged += len(readings)
            result.road_events_in_triage += sum(r.is_road_event for r in readings.values())
        else:
            answer = client.chat_json(
                self.config.full["system"],
                full_prompt(self.config, articles, today),
                max_tokens=self.config.full["max_tokens"],
            )

            def in_scope(article: ArticleText, reading: AiReading) -> bool:
                classifier, resolver, _ = tools[article.artifact_id]
                return reading_in_scope(reading, classifier, resolver)

            readings = read_full_answer(
                self.config, answer.content, articles, model=answer.model, now=now, in_scope=in_scope
            )
            result.fully_read += len(readings)
            result.road_events += sum(r.is_road_event and bool(r.in_scope) for r in readings.values())
        if answer.model not in result.models:
            result.models.append(answer.model)

        self._store(articles, readings, tools, result, reason=f"AI reading ({answer.model})")

    def _mark_unanswered(self, artifact_ids: list[str]) -> None:
        with self._ingestion.lock, self._session_factory() as session:
            for artifact in session.scalars(
                select(SourceArtifact).where(SourceArtifact.artifact_id.in_(artifact_ids))
            ):
                details = dict(artifact.classification_details or {})
                same_version = details.get("ai_unanswered_version") == self.config.version
                details["ai_unanswered"] = (details.get("ai_unanswered", 0) if same_version else 0) + 1
                details["ai_unanswered_version"] = self.config.version
                artifact.classification_details = details
            session.commit()

    def _store(self, articles, readings: dict[str, AiReading], tools, result: AiRunResult, *, reason: str) -> None:
        """Store the readings with their articles and re-derive the articles' events."""
        created: list[str] = []
        with self._ingestion.lock, self._session_factory() as session:
            ids = [article.artifact_id for article in articles]
            artifacts = {
                artifact.artifact_id: artifact
                for artifact in session.scalars(
                    select(SourceArtifact).where(SourceArtifact.artifact_id.in_(ids))
                )
            }
            events = {
                event.source_artifact_id: event
                for event in session.scalars(
                    select(Event).where(Event.source_artifact_id.in_(ids))
                ).unique()
            }
            for article in articles:
                artifact = artifacts.get(article.artifact_id)
                if artifact is None:
                    continue
                details = dict(artifact.classification_details or {})
                reading = readings.get(article.artifact_id)
                if reading is None:
                    # Left out of the answer: asked again later, a few times at most.
                    same_version = details.get("ai_unanswered_version") == self.config.version
                    details["ai_unanswered"] = (details.get("ai_unanswered", 0) if same_version else 0) + 1
                    details["ai_unanswered_version"] = self.config.version
                    artifact.classification_details = details
                    continue
                details["ai"] = reading.model_dump(mode="json")
                details.pop("ai_unanswered", None)
                details.pop("ai_unanswered_version", None)
                artifact.classification_details = details

                row = events.get(article.artifact_id)
                # A triage verdict changes nothing for an article without an event:
                # the full reading decides that. With an event, the verdict is shown on it.
                if reading.stage == TRIAGE and (reading.is_road_event or row is None):
                    continue
                classifier, resolver, city = tools[article.artifact_id]
                outcome, event_id = rederive_artifact(
                    session,
                    artifact,
                    row,
                    classifier=classifier,
                    resolver=resolver,
                    city=city,
                    rebuild=self._ingestion.rebuild_for_source(artifact.source_id),
                    reason=reason,
                    changed_by=AI_CHANGED_BY,
                    role_priority=self.config.role_priority,
                    placer=self._ingestion.placer_for_source(artifact.source_id),
                )
                if outcome == "created":
                    result.events_created += 1
                    created.append(event_id)
                elif outcome == "updated":
                    result.events_updated += 1
                elif outcome == "restored":
                    result.events_restored += 1
                elif outcome == "rejected":
                    result.events_rejected += 1
            session.commit()

            if created and self._settings.event_matching_after_ingestion:
                from app.services.merge_service import find_candidates

                try:
                    find_candidates(session, event_ids=created)
                    session.commit()
                except Exception:
                    session.rollback()
                    logger.exception("Matching after the AI reading failed; the readings are kept")


def reading_in_scope(reading: AiReading, classifier, resolver) -> bool:
    """Whether the event the reading describes is in the city the source covers.

    The city the model names decides when REI knows it (the source's city, or
    another city whose news is kept out). Otherwise the article must name a
    place of the city that the city's place list can find.
    """
    if reading.city:
        if classifier.names_scope_city(reading.city):
            return True
        if classifier.names_other_city(reading.city):
            return False
    for place in reading.places:
        if place.role in ROUTE_ROLES:
            continue
        match = resolve_place(resolver, place.name, place.found_in or "body")
        if match is not None and match.has_position:
            return True
    return False
