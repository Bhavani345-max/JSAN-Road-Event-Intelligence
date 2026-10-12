"""Storage retention: the text of old articles that are not road events.

Most stored articles are not road events (politics, sport, …): each feed poll
stores every new item so that it is not read again. After a while their full
text is of no use, so it is removed and a small stub is kept: source, item id,
link, headline, publication time, content hash and the classification. The
stub is what stops the same item being stored again (the pipeline recognises
an item by its id, link and headline, never by its text).

Never touched: articles classified as road events, structured source records,
manual entries, and any article an event was made from. Events, their
evidence and their history are kept in full.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Event, SourceArtifact
from packages.common.time import utc_now

NOT_RELEVANT = "NOT_RELEVANT"
# Marks a stub in raw_content: when and why the text was removed.
TEXT_REMOVED = "text_removed"
# raw_content keys kept in the stub: what identifies the item.
_STUB_KEYS = ("guid", "link", "url", "title", "published")


@dataclass
class RetentionResult:
    articles: int = 0
    bytes_removed: int = 0


def is_stub(artifact: SourceArtifact) -> bool:
    return TEXT_REMOVED in (artifact.raw_content or {})


def _size(value) -> int:
    return len(json.dumps(value, ensure_ascii=False, default=str))


def slim_unrelated_articles(
    session: Session,
    *,
    older_than_days: int,
    now: datetime | None = None,
    dry_run: bool = False,
) -> RetentionResult:
    """Remove the text of articles not about road events, published (or, without
    a publication time, retrieved) more than `older_than_days` ago. Commits
    unless `dry_run`."""
    now = now or utc_now()
    cutoff = now - timedelta(days=older_than_days)
    used = select(Event.source_artifact_id).where(Event.source_artifact_id.is_not(None))
    candidates = session.scalars(
        select(SourceArtifact).where(
            SourceArtifact.classification == NOT_RELEVANT,
            func.coalesce(SourceArtifact.published_at, SourceArtifact.retrieved_at) < cutoff,
            SourceArtifact.artifact_id.not_in(used),
        )
    )
    result = RetentionResult()
    for artifact in candidates:
        if is_stub(artifact) or artifact.revisions:
            continue
        raw = artifact.raw_content or {}
        stub = {key: raw[key] for key in _STUB_KEYS if key in raw}
        stub[TEXT_REMOVED] = {
            "at": now.isoformat(),
            "reason": f"Not a road event; text kept {older_than_days} days",
        }
        result.articles += 1
        result.bytes_removed += max(0, _size(raw) - _size(stub))
        if not dry_run:
            artifact.raw_content = stub
    if dry_run:
        session.rollback()
    else:
        session.commit()
    return result
