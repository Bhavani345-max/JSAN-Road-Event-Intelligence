"""Matching and the event lists read only the merge candidates that concern the
events they handle, never every recorded one (23 October 2026: production
loaded all of them after every ingestion run and for every event list, and
ran out of memory)."""

from contextlib import contextmanager

from sqlalchemy import event

from app.models import Event, EventMergeCandidate
from app.repositories.events import to_event_outs
from app.services import merge_service
from connectors.rss.siasat import SIASAT
from connectors.rss.telangana_today import TELANGANA_TODAY
from packages.common.time import utc_now
from tests.api.test_merging_api import add, candidates, db  # noqa: F401  (db is a fixture)

NOW = utc_now()
KBR = dict(place="KBR Park", kind="landmark", position=(78.4201, 17.4202), event_type=None)


def kbr_pair(db) -> None:
    """Two reports of one KBR Park plan: a possible match, not a clear one."""
    add(db, "EVT-A", TELANGANA_TODAY, "KBR flyover plan changed due to success of one way traffic", **KBR, created=NOW)
    add(db, "EVT-B", SIASAT, "GHMC revises KBR Park flyover plans, mulls permanent one-way", **KBR, created=NOW)


def record(db, a: str, b: str, status: str = "PENDING") -> EventMergeCandidate:
    candidate = EventMergeCandidate(
        event_a=a, event_b=b, classification="POSSIBLE", reasons=[], conflicts=[], status=status, created_at=NOW,
    )  # fmt: skip
    db.add(candidate)
    db.commit()
    return candidate


def elsewhere(db, count: int = 30) -> None:
    """Pairs recorded long ago among events of another city, as a database in use holds."""
    for n in range(count):
        add(db, f"EVT-D{n:03d}", TELANGANA_TODAY, f"Road closed in Delhi, stretch {n}", city="Delhi",
            place=f"Delhi stretch {n}", position=(77.2 + n / 100, 28.6), created=NOW)  # fmt: skip
    for n in range(count - 1):
        record(db, f"EVT-D{n:03d}", f"EVT-D{n + 1:03d}")


@contextmanager
def loaded_candidates(db):
    """The ids of the candidates read from the database inside the block."""
    db.expunge_all()  # read again from the database, not from the session
    ids: list[int] = []

    def on_load(candidate, _context):
        ids.append(candidate.id)

    event.listen(EventMergeCandidate, "load", on_load)
    try:
        yield ids
    finally:
        event.remove(EventMergeCandidate, "load", on_load)


def test_matching_new_events_reads_only_their_recorded_pairs(db):
    elsewhere(db)
    kbr_pair(db)
    with loaded_candidates(db) as ids:
        run = merge_service.find_candidates(db, event_ids=["EVT-B"])
    db.commit()
    assert run.candidates == 1 and ids == []
    assert [(c.event_a, c.event_b) for c in candidates(db)][-1] == ("EVT-A", "EVT-B")


def test_a_pair_already_decided_is_not_proposed_again(db):
    elsewhere(db)
    kbr_pair(db)
    decided = record(db, "EVT-A", "EVT-B", status="REJECTED").id
    with loaded_candidates(db) as ids:
        run = merge_service.find_candidates(db, event_ids=["EVT-B"])
    assert run.candidates == 0
    assert ids == [decided]


def test_an_event_list_reads_only_the_pairs_of_its_events(db):
    elsewhere(db)
    kbr_pair(db)
    pair = record(db, "EVT-A", "EVT-B").id
    with loaded_candidates(db) as ids:
        [out] = to_event_outs(db, [db.get(Event, "EVT-A")])
    assert [c.other_event_id for c in out.merge_candidates] == ["EVT-B"]
    assert ids == [pair]


def test_the_pairs_of_a_page_are_those_every_pending_pair_gives(db):
    elsewhere(db, count=5)
    kbr_pair(db)
    record(db, "EVT-A", "EVT-B")
    every = merge_service.pending_candidates_by_event(db)
    page = ["EVT-A", "EVT-D002"]
    found = merge_service.pending_candidates_by_event(db, event_ids=page)
    for event_id in page:
        assert [c.id for c in found[event_id]] == [c.id for c in every[event_id]]


def test_pairs_are_found_by_either_event_with_long_lists_and_a_status(db):
    kbr_pair(db)
    pending = record(db, "EVT-A", "EVT-B").id
    # Past the 500 ids of one query, and by the second event of the pair.
    ids = [f"EVT-NONE{n}" for n in range(600)] + ["EVT-B"]
    assert [c.id for c in merge_service._candidates_involving(db, ids)] == [pending]
    assert merge_service._candidates_involving(db, ids, status="REJECTED") == []
