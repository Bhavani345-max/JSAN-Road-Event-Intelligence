import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Event, SourceArtifact, SourceArtifactRevision
from packages.common.time import utc_now
from packages.event_schema import EventStatus, ReiEvent
from packages.source_models import RawSourceRecord
from services.extraction import ClassificationResult

from .events import EventRepository

_ID_BATCH = 200


class SqlIngestionStore:
    """Database-backed `IngestionStore` for the ingestion pipeline."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.events = EventRepository(session)

    def known_external_ids(self, source_id: str, external_ids: list[str]) -> set[str]:
        known: set[str] = set()
        for start in range(0, len(external_ids), _ID_BATCH):
            batch = external_ids[start : start + _ID_BATCH]
            known.update(
                self.session.scalars(
                    select(SourceArtifact.external_id).where(
                        SourceArtifact.source_id == source_id,
                        SourceArtifact.external_id.in_(batch),
                    )
                )
            )
        return known

    def stored_article_urls(self, urls: list[str]) -> set[str]:
        stored: set[str] = set()
        for start in range(0, len(urls), _ID_BATCH):
            batch = urls[start : start + _ID_BATCH]
            stored.update(
                self.session.scalars(
                    select(SourceArtifact.url).where(SourceArtifact.url.in_(batch))
                )
            )
        return stored

    def stored_article_titles(self, titles: list[str]) -> set[str]:
        """Headlines already stored from any source, lower-cased with spaces collapsed."""
        wanted = sorted({" ".join(title.lower().split()) for title in titles if title})
        stored: set[str] = set()
        for start in range(0, len(wanted), _ID_BATCH):
            batch = wanted[start : start + _ID_BATCH]
            stored.update(
                " ".join(title.split())
                for title in self.session.scalars(
                    select(func.lower(SourceArtifact.title)).where(
                        func.lower(SourceArtifact.title).in_(batch)
                    )
                )
            )
        return stored

    def save_artifact(self, record: RawSourceRecord, classification: ClassificationResult) -> str:
        artifact = SourceArtifact(
            artifact_id=str(uuid.uuid4()),
            source_id=record.source_id,
            external_id=record.external_id,
            url=record.url,
            title=record.title,
            published_at=record.published_at,
            retrieved_at=record.retrieved_at,
            raw_content=record.raw,
            content_hash=record.content_hash,
            classification=classification.label.value,
            classification_details={
                "method": classification.method,
                "classifier_version": classification.classifier_version,
                "score": classification.score,
                "matched_keywords": classification.matched_keywords,
                "in_scope_city": classification.city,
            },
            created_at=utc_now(),
        )
        self.session.add(artifact)
        # Evidence must exist in the database before an event refers to it.
        self.session.flush()
        return artifact.artifact_id

    def current_versions(
        self, source_id: str, external_ids: list[str]
    ) -> dict[str, tuple[str, dict]]:
        versions: dict[str, tuple[str, dict]] = {}
        for start in range(0, len(external_ids), _ID_BATCH):
            batch = external_ids[start : start + _ID_BATCH]
            for artifact in self.session.scalars(
                select(SourceArtifact).where(
                    SourceArtifact.source_id == source_id,
                    SourceArtifact.external_id.in_(batch),
                )
            ):
                latest = artifact.latest
                versions[artifact.external_id] = (latest.content_hash, latest.raw_content or {})
        return versions

    def save_revision(
        self, record: RawSourceRecord, classification: ClassificationResult, event: ReiEvent | None
    ) -> list[str]:
        """Add the new version as evidence, then apply it to the event built from the item."""
        from app.services.source_revision import CHANGED_BY, apply_source_revision

        artifact = self.session.scalars(
            select(SourceArtifact).where(
                SourceArtifact.source_id == record.source_id,
                SourceArtifact.external_id == record.external_id,
            )
        ).one()
        now = utc_now()
        revision = artifact.revision_count + 1
        artifact.revisions.append(
            SourceArtifactRevision(
                revision=revision,
                url=record.url,
                title=record.title,
                published_at=record.published_at,
                retrieved_at=record.retrieved_at,
                raw_content=record.raw,
                content_hash=record.content_hash,
                classification=classification.label.value,
                created_at=now,
            )
        )
        self.session.flush()
        row = self.session.scalars(
            select(Event).where(Event.source_artifact_id == artifact.artifact_id)
        ).first()
        if event is None:
            return []
        if row is None:
            self.events.add(
                event,
                artifact_id=artifact.artifact_id,
                change_reason=f"Created from revision {revision} of the source record",
                changed_by=CHANGED_BY,
            )
            return ["created"]
        return apply_source_revision(self.events, row, event, revision=revision, now=now)

    def record_observation(
        self, source_id: str, observed: set[str], now, *, in_force_only: bool = False
    ) -> list[str]:
        """Note, for each open event of the source, whether this refresh listed its record.

        Absence is not taken as the end of an event. After ABSENCE_REVIEW_AFTER
        refreshes without the record, the event is flagged for a reviewer (one
        version); if the record comes back, the flag is lifted (one version).
        Returns the ids of events newly flagged.

        `in_force_only`: the source lists only what is in force now (NDW's
        current picture, decision 0049). An event still in review whose record
        it has not listed for ABSENCE_REVIEW_AFTER refreshes is then taken as
        reported over by the source (one version, no end time made up), but
        only on a refresh that listed something: an empty refresh ends nothing.
        If the record comes back, it is current again (one version).
        """
        from app.services.source_revision import ABSENCE_REVIEW_AFTER, CHANGED_BY

        in_review = (EventStatus.VALIDATION_REQUIRED.value, EventStatus.QC_PENDING.value)

        flagged: list[str] = []
        rows = self.session.execute(
            select(Event, SourceArtifact.external_id)
            .join(SourceArtifact, Event.source_artifact_id == SourceArtifact.artifact_id)
            .where(
                Event.source_id == source_id,
                Event.status.not_in(("REJECTED", "CANCELLED", "SUPERSEDED", "EXPIRED")),
                # An event's record is its own source's. Saying so lets PostgreSQL
                # read only this source's records (its index) instead of joining
                # against every source's (27 October 2026, decision 0042).
                SourceArtifact.source_id == source_id,
            )
        ).all()
        for row, external_id in rows:
            detection = dict(row.detection or {})
            before = dict(detection.get("observation") or {})
            if external_id in observed:
                after = {
                    "last_seen_at": now.isoformat(),
                    "missing_since": None,
                    "missed_refreshes": 0,
                    "review_required": False,
                }
                note = (
                    "The source lists the record again; the absence flag is lifted."
                    if before.get("review_required")
                    else None
                )
                if before.get("ended_by_absence"):
                    detection["source_reports_ended"] = False
                    note = "The source lists the record again: it is no longer taken as over."
            else:
                missed = int(before.get("missed_refreshes") or 0) + 1
                after = {
                    "last_seen_at": before.get("last_seen_at"),
                    "missing_since": before.get("missing_since") or now.isoformat(),
                    "missed_refreshes": missed,
                    "review_required": before.get("review_required") or missed >= ABSENCE_REVIEW_AFTER,
                }
                since = after["missing_since"][:16].replace("T", " ")
                if before.get("ended_by_absence"):
                    after["ended_by_absence"] = True
                    note = None
                elif (
                    in_force_only
                    and observed
                    and missed >= ABSENCE_REVIEW_AFTER
                    and row.status in in_review
                    and not detection.get("source_reports_ended")
                ):
                    # The source lists only what is in force: no longer listing it says it is over.
                    after["ended_by_absence"] = True
                    detection["source_reports_ended"] = True
                    note = (
                        f"Not in the source's current picture for {missed} refreshes since {since} UTC. "
                        "The source lists only what is in force, so it is taken as over (decision 0049)."
                    )
                else:
                    note = (
                        f"Not listed by the source for {missed} refreshes since {since} UTC. "
                        "Not taken as ended: a reviewer should check it."
                        if after["review_required"] and not before.get("review_required")
                        else None
                    )
                    if after["review_required"] and not before.get("review_required"):
                        flagged.append(row.event_id)
            detection["observation"] = after
            row.detection = detection
            if note:
                row.version += 1
                row.updated_at = now
                self.events.record_version(row, change_reason=note, changed_by=CHANGED_BY)
        self.session.flush()
        return flagged

    def save_event(self, event: ReiEvent, artifact_id: str) -> None:
        self.events.add(
            event,
            artifact_id=artifact_id,
            change_reason="Created from source artifact by keyword detection",
            changed_by="ingestion",
        )
