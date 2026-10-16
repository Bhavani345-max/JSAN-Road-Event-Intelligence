"""The state of each source, said once for the API and the console (decision 0034).

Derived from what the registry and the database record, never assumed: the
source's integration status and terms, its polling state, and the events it
has given. A source that polls well but found no road event lately is "no
relevant road events", not failing; one that is off is never shown healthy.
"""

import re
from collections import Counter
from dataclasses import dataclass

from app.models import Source
from packages.common.time import ensure_utc
from packages.source_models import IntegrationStatus, TermsStatus

# How far back "collecting" looks for road events from a source.
RECENT_DAYS = 7


@dataclass(frozen=True)
class SourceState:
    # COLLECTING, NO_RECENT_EVENTS, FAILING, NOT_POLLED_YET, NOT_SCHEDULED,
    # DISABLED, AWAITING_PERMISSION, BLOCKED_BY_TERMS, BLOCKED, REMOVED,
    # NEEDS_CREDENTIALS, RESEARCHED, MANUAL_ONLY
    code: str
    label: str
    reason: str | None
    # Whether REI polls it on its own (on a schedule).
    polled: bool


def _last_sentences(text: str | None, limit: int = 260) -> str | None:
    """The end of a note: where the registry says why a source stands where it does."""
    if not text:
        return None
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    out = ""
    for sentence in reversed(sentences):
        if len(out) + len(sentence) > limit and out:
            break
        out = f"{sentence} {out}".strip()
    return out[:limit]


def _not_accessed(source: Source) -> str | None:
    access = source.access_method or ""
    return access.removeprefix("Not accessed: ").strip() or None if access.startswith("Not accessed") else None


def source_state(source: Source, counts: Counter | None = None) -> SourceState:
    counts = counts or Counter()
    status = source.integration_status
    if status == IntegrationStatus.CONNECTED.value:
        if not source.active:
            return SourceState(
                "NOT_SCHEDULED",
                "Off here: not scheduled (run by hand)",
                "Connected, but this installation does not poll it on a schedule "
                "(OFFICIAL_FEEDS_SCHEDULED / OFFICIAL_FEEDS_SCHEDULED_SOURCES).",
                polled=False,
            )
        if source.last_poll_at is None:
            return SourceState("NOT_POLLED_YET", "Active: not polled yet", None, polled=True)
        failure, success = source.last_failure_at, source.last_success_at
        if failure is not None and (success is None or ensure_utc(failure) > ensure_utc(success)):
            never = " It has never been polled successfully." if success is None else ""
            return SourceState(
                "FAILING", "Active: failing", f"{source.last_error or 'The last poll failed.'}{never}", polled=True
            )
        recent = counts.get("recent", 0)
        if recent:
            return SourceState(
                "COLLECTING",
                "Active: collecting",
                f"{recent} road event{'s' if recent != 1 else ''} detected in the last {RECENT_DAYS} days.",
                polled=True,
            )
        return SourceState(
            "NO_RECENT_EVENTS",
            "Active: no relevant road events found",
            f"Polled successfully; no road event detected in the last {RECENT_DAYS} days.",
            polled=True,
        )
    if status == IntegrationStatus.DISABLED.value:
        return SourceState(
            "DISABLED", "Off: disabled by configuration", _last_sentences(source.notes), polled=False
        )
    if status == IntegrationStatus.TERMS_REVIEW_REQUIRED.value:
        if source.terms_status == TermsStatus.RESTRICTED.value:
            return SourceState(
                "BLOCKED_BY_TERMS", "Blocked by the source's terms",
                _not_accessed(source) or source.licence, polled=False,
            )  # fmt: skip
        return SourceState(
            "AWAITING_PERMISSION", "Awaiting permission",
            _not_accessed(source) or _last_sentences(source.notes), polled=False,
        )  # fmt: skip
    if status == IntegrationStatus.BLOCKED.value:
        label = (
            "Blocked by the source's terms"
            if source.terms_status == TermsStatus.RESTRICTED.value
            else "Blocked"
        )
        code = "BLOCKED_BY_TERMS" if source.terms_status == TermsStatus.RESTRICTED.value else "BLOCKED"
        return SourceState(code, label, _last_sentences(source.notes), polled=False)
    if status == IntegrationStatus.NOT_USABLE.value:
        return SourceState(
            "REMOVED", "Removed", _not_accessed(source) or _last_sentences(source.notes), polled=False
        )
    if status == IntegrationStatus.REQUIRES_ACCESS.value:
        return SourceState(
            "NEEDS_CREDENTIALS", "Needs an API key or account",
            source.access_method or _last_sentences(source.notes), polled=False,
        )  # fmt: skip
    if status == IntegrationStatus.MANUAL_ONLY.value:
        return SourceState(
            "MANUAL_ONLY", "Published for people only (no feed)", _last_sentences(source.notes), polled=False
        )
    return SourceState(
        "RESEARCHED", "Researched, not connected", _last_sentences(source.notes), polled=False
    )


def describe(source: Source, counts: Counter | None) -> dict:
    """The status fields and event counts added to a source's API form."""
    counts = counts or Counter()
    state = source_state(source, counts)
    return {
        "status": state.code,
        "status_label": state.label,
        "status_reason": state.reason,
        "polled": state.polled,
        "recent_event_count": counts.get("recent", 0),
        "pending_review_count": counts.get("pending_review", 0),
        "validated_count": counts.get("validated", 0),
        # Never added up: one map shows events awaiting review, the other
        # validated ones (decision 0035).
        "on_map_review_count": counts.get("on_map_review", 0),
        "on_map_operations_count": counts.get("on_map_operations", 0),
    }
