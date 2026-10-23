"""Cross-source merging: candidates, automatic merges of clear duplicates, review decisions.

    events of a city -> pairwise matching (services/merging) ->
      SAME, nothing conflicting, nobody reviewed, same standing -> merged now
      anything else that may be the same                   -> a candidate for review

A merge links, it never deletes or rewrites:

- the merged event keeps its row, its evidence and its history, and is
  marked `merged_into` the canonical event, so it is no longer listed alone;
- the canonical event lists it under `detection.contributions` (source,
  evidence, link, publication time) and records in `detection.provenance`
  which event each field came from;
- the canonical event takes a field from a merged event only where it has
  none. Where both have a value and the values differ, both are kept in
  `detection.merge_conflicts` and the event is flagged for review. A news
  report never replaces what an official source states.

The canonical event is the one from the most authoritative source; among
equals, the one furthest through review, then the better located, then the
first reported.

Two records of one official source are separate events, except where the
source lists one event in several rows (`LISTED_IN_SEVERAL_ROWS`: NYC DOT
lists a block's closure once per permit purpose). Those rows are merged in the
same way, by `merge_listed_rows`.
"""

import json
import math
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field, replace
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, defer, load_only, selectinload

from app.models import Event, EventMergeCandidate, EventVersion, SourceArtifact
from app.repositories.events import EventRepository, to_rei_event
from packages.common.time import ensure_utc, utc_now
from connectors.official.calgary import SOURCE_ID as CALGARY_SOURCE_ID
from connectors.official import (
    dialog, drivebc, edmonton, finland, gold_coast, lyon, main_roads_wa, ottawa, roads_act, tfl,
    toronto, winnipeg, wodonga,
)  # fmt: skip
from connectors.official.calgary import same_place_and_period_key
from connectors.official.bison_fute import SOURCE_ID as BISON_FUTE_SOURCE_ID
from connectors.official.bison_fute import same_situation_key
from connectors.official.nyc import SOURCE_ID as NYC_SOURCE_ID
from connectors.official.nyc import same_closure_key
from packages.event_schema import EventStatus, ReiEvent
from packages.geo_models import positions_of
from services.merging import EventFacts, MatchClass, compare
from services.lifecycle import is_current
from services.merging.matcher import headline_key, normalise

AUTOMATIC = "auto-merge"
# Who changes events without a person deciding.
_AUTOMATIC_ACTORS = {"ingestion", "reprocessing", "source-update", "gis-resolver", AUTOMATIC}
_CLOSED = {
    EventStatus.REJECTED.value, EventStatus.CANCELLED.value,
    EventStatus.SUPERSEDED.value, EventStatus.EXPIRED.value,
}  # fmt: skip
# What a canonical event may take from an event merged into it.
MERGE_FIELDS = ("event_type", "start_time", "end_time", "direction", "affected_road", "geometry")
_STATUS_RANK = {
    EventStatus.VALIDATION_REQUIRED.value: 0,
    EventStatus.QC_PENDING.value: 1,
}
_LOCATION_RANK = {
    "QC_APPROVED": 5, "SOURCE_PROVIDED": 4, "GIS_RESOLVED": 4, "HUMAN_CORRECTED": 3,
    "APPROXIMATE": 1, "UNRESOLVED": 0,
}  # fmt: skip
# Of the rows a source lists for one event, the one that says most about the
# road leads: a closure before the works needing it, before a diversion or a
# hazard warning (a DATEX II situation's records, decision 0029).
_LEAD_TYPE_RANK = {
    "EMERGENCY_ROAD_CLOSURE": 0, "PLANNED_ROAD_CLOSURE": 0, "WEATHER_CLOSURE": 0,
    "BRIDGE_TUNNEL_RESTRICTION": 1, "ROAD_WORKS": 2, "ROAD_CONSTRUCTION": 2,
    "LANE_RESTRICTION": 3, "TURN_RESTRICTION": 3, "ACCIDENT": 4, "FLOODING": 4,
    "WATERLOGGING": 4, "TRAFFIC_DIVERSION": 5, "ROAD_HAZARD": 6,
}  # fmt: skip


def _row_lead_rank(row: Event):
    """Which of one event's rows leads: authority, review, location, then the type above."""
    rank = _canonical_rank(row)
    return (*rank[:3], _LEAD_TYPE_RANK.get(row.event_type or "", 7), *rank[3:])


def identical_rows_key(event: ReiEvent, _external_id: str | None) -> str | None:
    """Rows a source lists under different ids but identical to a reader (decision 0029).

    Same type, same title, same position and same stated period: the same
    closure entered twice. Rows that differ in any of these stay separate events.
    """
    if event.geometry is None or event.start_time is None or event.end_time is None:
        return None
    start, end = (
        ensure_utc(moment).strftime("%Y-%m-%d %H:%M") for moment in (event.start_time, event.end_time)
    )
    spot = json.dumps(event.geometry.model_dump(mode="json")["coordinates"])
    return f"{event.event_type} | {normalise(event.title)} | {spot} | {start} to {end} UTC"


# Official sources that list one event in several rows, and what the rows of
# one event share, given the event and its row's id in the source (None: the
# row cannot be grouped and stays on its own).
LISTED_IN_SEVERAL_ROWS: dict[str, Callable[[ReiEvent, str | None], str | None]] = {
    # A block's closure, once per permit purpose: same segment and work period.
    NYC_SOURCE_ID: lambda event, _external_id: same_closure_key(event),
    # A DATEX II situation's records at one spot over one period (decision 0029).
    BISON_FUTE_SOURCE_ID: same_situation_key,
    # Calgary's rows of one closure, per direction or lane: same place and period.
    CALGARY_SOURCE_ID: same_place_and_period_key,
    # Every other official feed: rows identical to a reader are one event.
    **{
        module.SOURCE_ID: identical_rows_key
        for module in (
            tfl, toronto, dialog, lyon, finland, drivebc, ottawa, edmonton, winnipeg,
            main_roads_wa, gold_coast, roads_act, wodonga,
        )
    },
}


class CandidateNotFound(Exception):
    pass


class CandidateDecided(Exception):
    pass


@dataclass
class MatchRun:
    compared: int = 0
    candidates: int = 0
    auto_merged: int = 0
    examples: list[str] = field(default_factory=list)


# --- facts ----------------------------------------------------------------------


def reviewed(row: Event) -> bool:
    """Whether a person has acted on the event."""
    return row.status not in (EventStatus.VALIDATION_REQUIRED.value,) or any(
        version.changed_by not in _AUTOMATIC_ACTORS for version in row.versions
    )


def facts(row: Event) -> EventFacts:
    event = to_rei_event(row)
    detection = event.detection
    position = None
    if event.geometry is not None:
        points = positions_of(event.geometry)
        position = (
            sum(p[0] for p in points) / len(points),
            sum(p[1] for p in points) / len(points),
        )
    places = set()
    roads = set()
    place_kind = place_name = None
    if detection:
        places |= {normalise(loc.name) for loc in detection.affected_locations}
        # Every place the article names (events reviewed before 6 October 2026
        # have only this list). It makes a possible match, never an automatic one.
        places |= {normalise(name) for name in detection.places}
        if detection.location:
            places.add(normalise(detection.location.place_name))
            place_kind = detection.location.place_kind
            place_name = detection.location.place_name
        roads |= {normalise(road) for road in detection.road_mentions}
    if event.affected_road:
        roads |= {normalise(part) for part in event.affected_road.split(";")}
    artifact = row.artifact
    return EventFacts(
        event_id=row.event_id,
        source_id=row.source_id,
        source_tier=row.source.source_tier,
        official=row.source.source_class in ("AUTHORITATIVE_OFFICIAL", "GOVERNMENT_OPEN_DATA"),
        title=row.title,
        url=(artifact.url if artifact else None) or row.source_reference,
        event_type=event.event_type.value if event.event_type else None,
        start=event.start_time,
        end=event.end_time,
        direction=event.direction.value if event.direction else None,
        position=position,
        approximate=bool(detection and detection.location_class == "APPROXIMATE"),
        place_kind=place_kind,
        place_name=place_name,
        places=frozenset(p for p in places if p),
        roads=frozenset(r for r in roads if r),
        reported_at=(artifact.published_at if artifact else None) or row.created_at,
        reviewed=reviewed(row),
        source_status=detection.source_status if detection else None,
        city=row.city,
    )


# --- finding candidates ----------------------------------------------------------


def is_current_row(row: Event, now: datetime | None = None) -> bool:
    """Whether the event is upcoming, ongoing or recently reported (services/lifecycle)."""
    artifact = row.artifact
    reported_at = (artifact.published_at or artifact.retrieved_at) if artifact else None
    return is_current(to_rei_event(row), reported_at=reported_at, now=now or utc_now())


def _open_events(session: Session, city: str | None) -> list[Event]:
    """Events that may still be merged: not merged, not closed, and current.

    An event that is over (ended, or an old report with no times) is not
    compared: nobody needs to decide whether it is the same as another.
    """
    return _open_events_where(session, [] if city is None else [Event.city == city])


def _open_events_where(session: Session, filters: list) -> list[Event]:
    # Each event's article in one query, without its raw content: matching reads
    # only the link and the publication and retrieval times.
    query = (
        select(Event)
        .where(Event.merged_into.is_(None), Event.status.not_in(_CLOSED), *filters)
        .options(
            selectinload(Event.artifact).options(
                defer(SourceArtifact.raw_content), defer(SourceArtifact.classification_details)
            ),
            # Who changed each event (`reviewed`), not every version's snapshot.
            selectinload(Event.versions).options(load_only(EventVersion.changed_by)),
        )
    )
    now = utc_now()
    rows = session.scalars(query.order_by(Event.created_at, Event.event_id)).unique()
    return [row for row in rows if is_current_row(row, now)]


def _open_events_of_cities(session: Session, event_ids: list[str], city: str | None) -> list[Event]:
    """The open events of the cities the given events are in: only events of one
    city are ever compared (`compare`: "different cities")."""
    cities: set[str | None] = set()
    for chunk in range(0, len(event_ids), 500):
        cities |= set(
            session.scalars(select(Event.city).where(Event.event_id.in_(event_ids[chunk : chunk + 500])))
        )
    if city is not None:
        cities &= {city}
    if not cities:
        return []
    named = sorted(name for name in cities if name is not None)
    conditions = [Event.city.in_(named)] if named else []
    if None in cities:
        conditions.append(Event.city.is_(None))
    return _open_events_where(session, [or_(*conditions)])


def _candidates_involving(
    session: Session, event_ids: Iterable[str], *, status: str | None = None
) -> list[EventMergeCandidate]:
    """The recorded candidates that concern any of `event_ids`, by either event,
    in id order. Never every candidate: on 23 October 2026 production held far
    more than any one run concerns, and loading all of them at every run, and at
    every event list, used up its memory."""
    ids = list(dict.fromkeys(event_ids))
    found: dict[int, EventMergeCandidate] = {}
    for start in range(0, len(ids), 500):
        chunk = ids[start : start + 500]
        for column in (EventMergeCandidate.event_a, EventMergeCandidate.event_b):
            query = select(EventMergeCandidate).where(column.in_(chunk))
            if status is not None:
                query = query.where(EventMergeCandidate.status == status)
            for candidate in session.scalars(query):
                found[candidate.id] = candidate
    return [found[key] for key in sorted(found)]


# compare() finds two events anything but DIFFERENT only if they share an article
# or a link, a place or a road name, or lie within SAME_SPOT_KM (services/merging).
# Events are indexed by those keys, per city, and only events sharing one are
# compared. Map cells are CELL_DEGREES square: wider than SAME_SPOT_KM (0.3 km) in
# both directions up to 80 degrees of latitude, so two such events are always in
# the same or neighbouring cells.
CELL_DEGREES = 0.02


def _cell(position: tuple[float, float]) -> tuple[int, int]:
    longitude, latitude = position
    return math.floor(longitude / CELL_DEGREES), math.floor(latitude / CELL_DEGREES)


def _match_keys(city: str | None, facts: EventFacts) -> set[tuple]:
    """What an event is filed under for matching."""
    keys: set[tuple] = {(city, "name", name) for name in facts.places | facts.roads}
    if facts.position:
        keys.add((city, "cell", _cell(facts.position)))
    headline = headline_key(facts.title)
    if headline:
        keys.add((city, "headline", headline))
    if facts.url:
        keys.add((city, "url", facts.url))
    return keys


def _lookup_keys(city: str | None, facts: EventFacts) -> set[tuple]:
    """Where an event's possible matches are filed: its own keys, and the cells around its own."""
    keys = {key for key in _match_keys(city, facts) if key[1] != "cell"}
    if facts.position:
        x, y = _cell(facts.position)
        keys |= {(city, "cell", (x + dx, y + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    return keys


# A web address more open events share than this is a feed's or a portal's page,
# not one article, and says nothing about which event a report is. On 22 October
# 2026 NDW gave https://opendata.ndw.nu/ as the reference of every record: its
# 14,343 Dutch events were all compared with one another as "the same article"
# (7.7 GB of memory, millions of pairs).
SHARED_URL_EVENTS = 10


def _pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


def find_candidates(
    session: Session,
    *,
    event_ids: Iterable[str] | None = None,
    city: str | None = None,
    automatic: bool = True,
) -> MatchRun:
    """Compare events and record what may be the same. Commits nothing.

    With `event_ids`, only pairs involving those events are compared (after
    an ingestion run); otherwise every pair of open events in each city.
    """
    run = MatchRun()
    focus_ids = None if event_ids is None else list(dict.fromkeys(event_ids))
    pool = (
        _open_events(session, city) if focus_ids is None else _open_events_of_cities(session, focus_ids, city)
    )
    by_id = {row.event_id: row for row in pool}
    focus = [by_id[i] for i in focus_ids if i in by_id] if focus_ids is not None else pool
    # Every pair compared below involves an event of `focus`: only their
    # recorded pairs can be known already.
    known = (
        {(c.event_a, c.event_b) for c in _candidates_involving(session, focus_ids)}
        if focus_ids is not None
        else {(a, b) for a, b in session.execute(select(EventMergeCandidate.event_a, EventMergeCandidate.event_b))}
    )
    facts_of: dict[str, EventFacts] = {}

    def fact(row: Event) -> EventFacts:
        if row.event_id not in facts_of:
            facts_of[row.event_id] = facts(row)
        return facts_of[row.event_id]

    # A shared page is neither a match key nor proof of "the same article".
    url_counts = Counter(fact(row).url for row in pool if fact(row).url)
    shared_urls = {url for url, count in url_counts.items() if count > SHARED_URL_EVENTS}
    for event_id, known_facts in list(facts_of.items()):
        if known_facts.url in shared_urls:
            facts_of[event_id] = replace(known_facts, url=None)

    order = {row.event_id: position for position, row in enumerate(pool)}
    filed: dict[tuple, dict[str, Event]] = defaultdict(dict)

    def file(row: Event) -> None:
        for match_key in _match_keys(row.city, fact(row)):
            filed[match_key][row.event_id] = row

    for row in pool:
        file(row)

    for row in focus:
        if row.merged_into:
            continue
        # Every event that may match, in the pool's order (as when every pair was compared).
        nearby: dict[str, Event] = {}
        for match_key in _lookup_keys(row.city, fact(row)):
            nearby.update(filed.get(match_key, {}))
        for other in sorted(nearby.values(), key=lambda event: order[event.event_id]):
            if other.event_id == row.event_id or row.merged_into or other.merged_into:
                continue
            if row.city != other.city:
                continue
            mine, theirs = fact(row), fact(other)
            if mine.source_id == theirs.source_id and mine.official and theirs.official:
                # compare(): separate records of one official source are separate events.
                continue
            key = _pair(row.event_id, other.event_id)
            if key in known:
                continue
            known.add(key)
            run.compared += 1
            match = compare(fact(row), fact(other))
            if match.classification is MatchClass.DIFFERENT:
                continue
            candidate = EventMergeCandidate(
                event_a=key[0],
                event_b=key[1],
                classification=match.classification.value,
                reasons=list(match.reasons) + list(match.notes),
                conflicts=list(match.conflicts),
                status="PENDING",
                created_at=utc_now(),
            )
            session.add(candidate)
            run.candidates += 1
            if automatic and match.auto_merge:
                canonical, member = choose_canonical(row, other)
                merge(
                    session, canonical, member, decided_by=AUTOMATIC, how="automatic",
                    reason="Clearly the same event: " + "; ".join(match.reasons),
                    conflicts=[],
                )  # fmt: skip
                candidate.status = "AUTO_MERGED"
                candidate.decided_at = utc_now()
                candidate.decided_by = AUTOMATIC
                candidate.decision_reason = "Clearly the same event; nothing conflicting"
                run.auto_merged += 1
                run.examples.append(f"{canonical.title} ← {member.source_id}")
                facts_of.pop(canonical.event_id, None)
                # The merged event may now share more with others: filed again.
                file(canonical)
    session.flush()
    return run


def merge_listed_rows(session: Session, source_id: str) -> MatchRun:
    """Merge the rows a source lists for one event (`LISTED_IN_SEVERAL_ROWS`). Commits nothing.

    Rows with the same key are one event. Those nobody has reviewed are merged
    into one of them: linked, never deleted, like any automatic merge. A row a
    reviewer has acted on is not merged automatically; it becomes a candidate
    for review beside the event. A pair a reviewer has decided stays decided.
    """
    run = MatchRun()
    key_of = LISTED_IN_SEVERAL_ROWS.get(source_id)
    if key_of is None:
        return run
    rows = session.scalars(
        select(Event)
        .where(
            Event.source_id == source_id,
            Event.merged_into.is_(None),
            Event.status.not_in(_CLOSED),
        )
        .order_by(Event.created_at, Event.event_id)
    ).unique()
    groups: dict[str, list[Event]] = {}
    for row in rows:
        external_id = row.artifact.external_id if row.artifact else None
        if key := key_of(to_rei_event(row), external_id):
            groups.setdefault(key, []).append(row)
    # Only pairs of rows listed for one event are looked up below.
    listed_ids = [row.event_id for rows_of_event in groups.values() if len(rows_of_event) > 1 for row in rows_of_event]
    known = {(c.event_a, c.event_b): c for c in _candidates_involving(session, listed_ids)}
    now = utc_now()

    for key, rows_of_event in groups.items():
        if len(rows_of_event) < 2:
            continue
        reason = f"The source lists one event in several rows: {key}"
        notes = ["a reviewer has acted on one of them: merged only by a reviewer"]
        untouched = [row for row in rows_of_event if not reviewed(row)]
        canonical = min(untouched or rows_of_event, key=_row_lead_rank)
        for row in rows_of_event:
            if row is canonical:
                continue
            pair = _pair(canonical.event_id, row.event_id)
            automatic = row in untouched and canonical in untouched
            candidate = known.get(pair)
            if candidate is None:
                candidate = EventMergeCandidate(
                    event_a=pair[0],
                    event_b=pair[1],
                    classification=MatchClass.SAME.value,
                    reasons=[reason] + ([] if automatic else notes),
                    conflicts=[],
                    status="PENDING",
                    created_at=now,
                )
                session.add(candidate)
                known[pair] = candidate
                if not automatic:
                    run.candidates += 1  # left for a reviewer
            elif candidate.status in ("PENDING", "REJECTED") or not automatic:
                # Awaiting or decided by a reviewer.
                continue
            # Otherwise the pair was merged before and separated by a source
            # revision; with the same key again, it is merged again.
            run.compared += 1
            if not automatic:
                continue
            merge(
                session, canonical, row, decided_by=AUTOMATIC, how="automatic", reason=reason,
                conflicts=[],
            )  # fmt: skip
            candidate.status = "AUTO_MERGED"
            candidate.decided_at = now
            candidate.decided_by = AUTOMATIC
            candidate.decision_reason = "One event the source lists in several rows"
            run.auto_merged += 1
            if len(run.examples) < 20:
                run.examples.append(f"{canonical.title} <- {row.event_id}")
    session.flush()
    return run


# --- merging ---------------------------------------------------------------------


def _canonical_rank(row: Event):
    """Lowest first: most authoritative, then furthest in review, better located, first."""
    detection = row.detection or {}
    return (
        row.source.source_tier or 9,
        -_STATUS_RANK.get(row.status, 2),
        -_LOCATION_RANK.get(detection.get("location_class") or "UNRESOLVED", 0),
        ensure_utc(row.created_at),
        row.event_id,
    )


def choose_canonical(a: Event, b: Event) -> tuple[Event, Event]:
    """(canonical, merged): most authoritative, then furthest in review, better located, first."""
    return (a, b) if _canonical_rank(a) <= _canonical_rank(b) else (b, a)


def _value(row: Event, name: str):
    value = getattr(row, name)
    if isinstance(value, datetime):
        return ensure_utc(value).isoformat()
    return value


def merge(
    session: Session,
    canonical: Event,
    member: Event,
    *,
    decided_by: str,
    how: str,
    reason: str,
    conflicts: list[dict] | None = None,
) -> list[str]:
    # `conflicts` is what matching found; merging re-checks every field itself.
    del conflicts
    """Link `member` under `canonical`. Returns the fields the canonical event took."""
    events = EventRepository(session)
    now = utc_now()
    detection = dict(canonical.detection or {})
    provenance = dict(detection.get("provenance") or {})
    own = {"event_id": canonical.event_id, "source_id": canonical.source_id}
    for name in MERGE_FIELDS:
        if name not in provenance and getattr(canonical, name) is not None:
            provenance[name] = own
    found: list[dict] = list(detection.get("merge_conflicts") or [])
    taken: list[str] = []
    origin = {"event_id": member.event_id, "source_id": member.source_id}
    member_detection = member.detection or {}

    for name in MERGE_FIELDS:
        theirs = getattr(member, name)
        if theirs is None:
            continue
        mine = getattr(canonical, name)
        if mine is None:
            setattr(canonical, name, theirs)
            provenance[name] = origin
            taken.append(name)
            if name == "geometry":
                detection["location"] = member_detection.get("location")
                detection["location_class"] = member_detection.get("location_class")
            continue
        if _value(canonical, name) != _value(member, name):
            found.append(
                {
                    "field": name,
                    "values": [
                        {**provenance.get(name, own), "value": _value(canonical, name)},
                        {**origin, "value": _value(member, name)},
                    ],
                }
            )

    # Places: every one either names, once.
    names = {loc.get("name") for loc in detection.get("affected_locations") or []}
    detection["affected_locations"] = list(detection.get("affected_locations") or []) + [
        loc for loc in member_detection.get("affected_locations") or [] if loc.get("name") not in names
    ]
    artifact = member.artifact
    contribution = {
        "event_id": member.event_id,
        "source_id": member.source_id,
        "artifact_id": member.source_artifact_id,
        "title": member.title,
        "url": (artifact.url if artifact else None) or member.source_reference,
        "published_at": (
            ensure_utc(artifact.published_at).isoformat() if artifact and artifact.published_at else None
        ),
        "merged_at": now.isoformat(),
        "merged_by": decided_by,
        "how": how,
        "reason": reason,
        "fields": taken,
    }
    # What was merged into the member before comes along, still attributed.
    detection["contributions"] = (
        list(detection.get("contributions") or [])
        + [contribution]
        + list(member_detection.get("contributions") or [])
    )
    detection["provenance"] = provenance
    new_conflicts = found[len(detection.get("merge_conflicts") or []) :]
    if new_conflicts:
        detection["merge_review_required"] = True
    detection["merge_conflicts"] = found
    canonical.detection = detection
    canonical.version += 1
    canonical.updated_at = now
    summary = f"Merged with {member.event_id} ({member.source_id}), {how}: {reason}"
    if taken:
        summary += f" Took {', '.join(taken)} from it."
    if new_conflicts:
        summary += " Sources disagree on " + ", ".join(c["field"] for c in new_conflicts) + ": review needed."
    events.record_version(canonical, change_reason=summary, changed_by=decided_by)

    member.merged_into = canonical.event_id
    member.version += 1
    member.updated_at = now
    events.record_version(
        member,
        change_reason=f"Merged into {canonical.event_id} ({canonical.source_id}), {how}: {reason}",
        changed_by=decided_by,
    )
    # Events merged into the member before now belong to the canonical event.
    for child in session.scalars(select(Event).where(Event.merged_into == member.event_id)):
        child.merged_into = canonical.event_id
    _repoint_candidates(session, member.event_id, canonical.event_id)
    session.flush()
    return taken


def _repoint_candidates(session: Session, old: str, new: str) -> None:
    """Pending candidates about the merged event now concern its canonical event."""
    pending = session.scalars(
        select(EventMergeCandidate).where(
            EventMergeCandidate.status == "PENDING",
            or_(EventMergeCandidate.event_a == old, EventMergeCandidate.event_b == old),
        )
    )
    # Every pair checked below involves `new`.
    existing = {(c.event_a, c.event_b) for c in _candidates_involving(session, [new])}
    for candidate in pending:
        other = candidate.event_b if candidate.event_a == old else candidate.event_a
        if other == new:
            candidate.status = "SUPERSEDED"
            candidate.decision_reason = "The two events were merged by another decision"
            continue
        key = _pair(new, other)
        if key in existing:
            candidate.status = "SUPERSEDED"
            candidate.decision_reason = f"Replaced by the candidate for {key[0]} and {key[1]}"
            continue
        candidate.event_a, candidate.event_b = key
        existing.add(key)


# --- review decisions ---------------------------------------------------------------


def _root(session: Session, event_id: str) -> Event:
    row = session.get(Event, event_id)
    seen = set()
    while row is not None and row.merged_into and row.event_id not in seen:
        seen.add(row.event_id)
        row = session.get(Event, row.merged_into)
    return row


def confirm(session: Session, candidate_id: int, *, reviewer: str, reason: str) -> Event:
    """A reviewer says the two are one event: merge them. Returns the canonical event."""
    candidate = session.get(EventMergeCandidate, candidate_id)
    if candidate is None:
        raise CandidateNotFound(candidate_id)
    if candidate.status != "PENDING":
        raise CandidateDecided(f"This candidate is already {candidate.status.lower()}.")
    a, b = _root(session, candidate.event_a), _root(session, candidate.event_b)
    if a.event_id != b.event_id:
        canonical, member = choose_canonical(a, b)
        merge(
            session, canonical, member, decided_by=reviewer, how="reviewer",
            reason=reason, conflicts=candidate.conflicts,
        )  # fmt: skip
    else:
        canonical = a
    candidate.status = "CONFIRMED"
    candidate.decided_at = utc_now()
    candidate.decided_by = reviewer
    candidate.decision_reason = reason
    session.commit()
    return canonical


def reject(session: Session, candidate_id: int, *, reviewer: str, reason: str) -> EventMergeCandidate:
    """A reviewer says they are different events: they stay apart and are not proposed again."""
    candidate = session.get(EventMergeCandidate, candidate_id)
    if candidate is None:
        raise CandidateNotFound(candidate_id)
    if candidate.status != "PENDING":
        raise CandidateDecided(f"This candidate is already {candidate.status.lower()}.")
    candidate.status = "REJECTED"
    candidate.decided_at = utc_now()
    candidate.decided_by = reviewer
    candidate.decision_reason = reason
    session.commit()
    return candidate


class NotOneGroup(Exception):
    pass


def confirm_all(
    session: Session, candidate_ids: list[int], *, reviewer: str, reason: str
) -> Event:
    """A reviewer says every one of these candidates is the same event: merge them all.

    The candidates must share one event (those listed on that event's panel),
    so one decision covers the reports of one story. Each merge is recorded as
    a single confirmation would be. Returns the canonical event.
    """
    candidates = []
    for candidate_id in dict.fromkeys(candidate_ids):
        candidate = session.get(EventMergeCandidate, candidate_id)
        if candidate is None:
            raise CandidateNotFound(candidate_id)
        if candidate.status != "PENDING":
            raise CandidateDecided(f"Candidate {candidate_id} is already {candidate.status.lower()}.")
        candidates.append(candidate)
    if not candidates:
        raise NotOneGroup("No candidates were given.")
    shared = set.intersection(*({c.event_a, c.event_b} for c in candidates))
    if not shared:
        raise NotOneGroup("These candidates do not all concern one event.")
    # The pairs as they are now: merging repoints the remaining candidates.
    pairs = [(c.event_a, c.event_b, c) for c in candidates]
    for event_a, event_b, candidate in pairs:
        a, b = _root(session, event_a), _root(session, event_b)
        if a.event_id != b.event_id:
            canonical, member = choose_canonical(a, b)
            merge(
                session, canonical, member, decided_by=reviewer, how="reviewer",
                reason=reason, conflicts=candidate.conflicts,
            )  # fmt: skip
        # Recorded as the reviewer's decision, as a single confirmation is,
        # although merging may have marked it superseded meanwhile.
        candidate.status = "CONFIRMED"
        candidate.decided_at = utc_now()
        candidate.decided_by = reviewer
        candidate.decision_reason = reason
    session.commit()
    return _root(session, next(iter(shared)))


def pending_candidates_by_event(
    session: Session, now: datetime | None = None, *, event_ids: Iterable[str] | None = None
) -> dict[str, list[EventMergeCandidate]]:
    """Pending candidates a reviewer is asked about: both events still current.
    With `event_ids`, only those concerning these events (a page of a list).

    A candidate involving an event that is over stays recorded (and comes back
    if the event is extended), but nobody is asked about it.
    """
    pending = (
        list(session.scalars(select(EventMergeCandidate).where(EventMergeCandidate.status == "PENDING")))
        if event_ids is None
        else _candidates_involving(session, event_ids, status="PENDING")
    )
    ids = {i for c in pending for i in (c.event_a, c.event_b)}
    now = now or utc_now()
    current = (
        {
            row.event_id
            for row in session.scalars(select(Event).where(Event.event_id.in_(ids))).unique()
            if is_current_row(row, now)
        }
        if ids
        else set()
    )
    by_event: dict[str, list[EventMergeCandidate]] = {}
    for candidate in pending:
        if candidate.event_a not in current or candidate.event_b not in current:
            continue
        by_event.setdefault(candidate.event_a, []).append(candidate)
        by_event.setdefault(candidate.event_b, []).append(candidate)
    return by_event
