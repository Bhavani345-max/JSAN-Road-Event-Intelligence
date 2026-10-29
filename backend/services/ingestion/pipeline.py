"""Source ingestion: connector -> evidence -> detection -> canonical event.

The pipeline knows nothing about RSS or about the database. It is given a
connector (any source type) and a store (any persistence), so new sources and
storage changes do not touch it.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from connectors.base import SourceConnector
from packages.cities import City
from packages.common.time import utc_now
from packages.event_schema import AiReading, ReiEvent
from packages.source_models import RawSourceRecord, SourceClass
from services.extraction import (
    ClassificationResult,
    KeywordClassifier,
    build_event_from_article,
    build_event_from_source,
    classify_source_record,
    names_a_place,
)
from services.extraction.ai_event import build_event_from_ai, is_ai_road_event
from services.geo_resolution import PlaceResolver
from services.geo_resolution.placement import Placer

logger = logging.getLogger(__name__)


class IngestionStore(Protocol):
    """Persistence the pipeline needs. Implemented by the API's repositories."""

    def known_external_ids(self, source_id: str, external_ids: list[str]) -> set[str]:
        """Which of these source items have already been stored."""
        ...

    def stored_article_urls(self, urls: list[str]) -> set[str]:
        """Which of these article addresses are already stored, from any source."""
        ...

    def stored_article_titles(self, titles: list[str]) -> set[str]:
        """Which of these headlines (compared case-insensitively) are already stored."""
        ...

    def save_artifact(self, record: RawSourceRecord, classification: ClassificationResult) -> str:
        """Persist the item as evidence and return the artifact id."""
        ...

    def save_event(self, event: ReiEvent, artifact_id: str) -> None: ...

    # Optional, for structured sources whose records are revised (official feeds).
    def current_versions(
        self, source_id: str, external_ids: list[str]
    ) -> dict[str, tuple[str, dict]]:
        """The content hash and raw content of the latest stored version of each item."""
        ...

    def save_revision(
        self, record: RawSourceRecord, classification: ClassificationResult, event: ReiEvent | None
    ) -> list[str]:
        """Store a new version of a held item and apply it to its event. Returns what changed."""
        ...


@dataclass
class IngestionResult:
    source_id: str
    started_at: datetime
    finished_at: datetime | None = None
    fetched: int = 0
    new_artifacts: int = 0
    duplicates: int = 0
    # Items already held that the source has revised since (structured sources).
    revised: int = 0
    relevant: int = 0
    events_created: int = 0
    event_ids: list[str] = field(default_factory=list)


def classify(
    record: RawSourceRecord, classifier: KeywordClassifier, city: City | None
) -> ClassificationResult:
    """Keyword detection for text; the city's area for a structured source's record."""
    if record.structured is not None:
        return classify_source_record(record, city)
    return classifier.classify(record)


def _title_key(title: str) -> str:
    return " ".join(title.lower().split())


def event_for_record(
    record: RawSourceRecord,
    classification: ClassificationResult,
    resolver: PlaceResolver | None,
    *,
    now: datetime,
    city: City | None = None,
    ai: AiReading | None = None,
    role_priority: tuple[str, ...] | None = None,
    placer: Placer | None = None,
) -> ReiEvent | None:
    """The event a classified item gives rise to, or None when it gives none.

    With a place resolver, an article must also name a road or a known
    place of the city: a road event that cannot be placed anywhere is not one.
    A record from a structured source is built from what the source states.

    An article an AI reading (checked against the article) says is a road
    event in the city is built from that reading, whatever the keywords
    found. Otherwise the keyword result decides, and the reading, if any, is
    kept on the event for the reviewer (a model that disagrees is shown, not
    obeyed).
    """
    if record.structured is not None:
        if not classification.is_relevant:
            return None
        return build_event_from_source(
            record, classification, now=now, resolver=resolver, city=city
        )
    if ai is not None and is_ai_road_event(ai):
        extra = {"role_priority": role_priority} if role_priority else {}
        event = build_event_from_ai(
            record, classification, ai, now=now, resolver=resolver, city=city, placer=placer, **extra
        )
        if event is not None:
            return event
    if not classification.is_relevant:
        return None
    event = build_event_from_article(
        record, classification, now=now, resolver=resolver, city=city, placer=placer
    )
    if resolver is not None and not names_a_place(event):
        return None
    if ai is not None and event.detection is not None:
        event.detection.ai = ai
    return event


def run_ingestion(
    connector: SourceConnector,
    classifier: KeywordClassifier,
    store: IngestionStore,
    resolver: PlaceResolver | None = None,
    city: City | None = None,
    placer: Placer | None = None,
) -> IngestionResult:
    """Fetch one source and process every item not seen before.

    Raises ConnectorError if the source cannot be fetched; nothing is stored in
    that case.
    """
    source_id = connector.source.source_id
    result = IngestionResult(source_id=source_id, started_at=utc_now())

    records = connector.fetch()
    result.fetched = len(records)

    # A connector whose items arrive incomplete (a search result that only
    # points to an article) fetches the rest, for new items only.
    complete = getattr(connector, "complete", None)

    seen = store.known_external_ids(source_id, [record.external_id for record in records])
    if complete is not None:
        # Such a source only points at articles. One already stored from its
        # publisher's own feed is not stored a second time.
        held = store.stored_article_urls([record.url for record in records if record.url])
        seen |= {record.external_id for record in records if record.url in held}
    discovery = connector.source.source_class is SourceClass.DISCOVERY
    if discovery and hasattr(store, "stored_article_titles"):
        # A search source finds reports of articles. One already held under
        # the same headline, from the publisher's feed or another search, is
        # the same article and is not stored again. Publishers' own feeds are
        # not compared this way: two papers may share a headline.
        held_titles = store.stored_article_titles([record.title for record in records])
        seen |= {
            record.external_id
            for record in records
            if _title_key(record.title) in held_titles
        }
    # A structured source revises its records. A held item whose content has
    # changed is a revision: stored as evidence and applied to its event.
    # A connector may say which fields are content (`revision_key`), so that a
    # record the source only touched (a new "last modified" time) is not a
    # revision. Without it, any change of the content hash is one.
    revision_key = getattr(connector, "revision_key", None)
    held: dict[str, tuple[str, dict]] = {}
    if hasattr(store, "current_versions") and any(r.structured for r in records):
        held = store.current_versions(
            source_id, [r.external_id for r in records if r.structured is not None]
        )

    def is_revision(record: RawSourceRecord) -> bool:
        if record.structured is None or record.external_id not in held:
            return False
        held_hash, held_raw = held[record.external_id]
        if revision_key is not None:
            return revision_key(record.raw) != revision_key(held_raw)
        return held_hash != record.content_hash

    revised_records: list[RawSourceRecord] = []
    new_records: list[RawSourceRecord] = []
    # Headlines of the new results of this poll (search sources only).
    titles_this_poll: set[str] = set()
    for record in records:
        if record.external_id in seen:
            if is_revision(record):
                revised_records.append(record)
                # Also guards against the same revision appearing twice in one fetch.
                held[record.external_id] = (record.content_hash, record.raw)
            else:
                result.duplicates += 1
            continue
        if discovery:
            # A search can list syndicated copies of one article (the same
            # headline on several sites) in one poll: the first is kept, as
            # one held from an earlier poll would be (decision 0033).
            key = _title_key(record.title)
            if key in titles_this_poll:
                result.duplicates += 1
                continue
            titles_this_poll.add(key)
        # Also guards against the same item appearing twice in one fetch.
        seen.add(record.external_id)
        # All fetching happens here, before the first write: a database write
        # holds a lock, and a reviewer saving a change must not wait behind a
        # run that is still reading web pages.
        new_records.append(complete(record) if complete is not None else record)

    for record in new_records:
        classification = classify(record, classifier, city)
        # Evidence is stored for every item, relevant or not, before anything
        # is derived from it.
        artifact_id = store.save_artifact(record, classification)
        result.new_artifacts += 1

        result.relevant += classification.is_relevant
        event = event_for_record(
            record, classification, resolver, now=utc_now(), city=city, placer=placer
        )
        if event is not None:
            store.save_event(event, artifact_id)
            result.events_created += 1
            result.event_ids.append(event.event_id)

    # An official source's refresh lists its current records. Which held ones
    # it no longer lists is counted, not taken as the event ending, except for
    # a source that lists only what is in force (decision 0049).
    observed = getattr(connector, "observed_ids", None)
    if observed is not None and hasattr(store, "record_observation"):
        store.record_observation(
            source_id, set(observed), utc_now(),
            in_force_only=getattr(connector, "lists_only_what_is_in_force", False),
        )  # fmt: skip

    for record in revised_records:
        classification = classify(record, classifier, city)
        derived = event_for_record(
            record, classification, resolver, now=utc_now(), city=city, placer=placer
        )
        store.save_revision(record, classification, derived)
        result.revised += 1

    result.finished_at = utc_now()
    logger.info(
        "%s: fetched=%d new=%d duplicates=%d revised=%d relevant=%d events=%d",
        source_id,
        result.fetched,
        result.new_artifacts,
        result.duplicates,
        result.revised,
        result.relevant,
        result.events_created,
    )
    return result
