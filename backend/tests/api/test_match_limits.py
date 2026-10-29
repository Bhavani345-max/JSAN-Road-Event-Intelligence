"""Limits that keep a matching fault from running the API out of memory.

On 22 October 2026 a match rule paired 252 NDW situations with about 14,000
NDW roadworks each: 3.5 million pending pairs. From then on every page of the
Netherlands review queue loaded thousands of pairs per event, with the other
event of each, and the API used up its 24 GB and restarted (29 October 2026).
"""

import logging
from datetime import timedelta

from app.models import EventMergeCandidate
from app.repositories.events import LISTED_MATCHES_PER_EVENT, to_event_outs
from app.services import merge_service
from packages.common.time import utc_now
from connectors.rss.the_hindu import THE_HINDU
from connectors.rss.telangana_today import TELANGANA_TODAY
from tests.api.test_merging_api import add, db  # noqa: F401  (db is a fixture)


def current_event(session, event_id, source, title="Traffic diversions at Khajaguda junction"):
    now = utc_now()
    return add(session, event_id, source, title, start=now - timedelta(days=1), end=now + timedelta(days=5))


def pend(session, event_a, event_b):
    session.add(
        EventMergeCandidate(
            event_a=event_a, event_b=event_b, classification="POSSIBLE", reasons=["test"], conflicts=[],
            status="PENDING", created_at=utc_now(),
        )  # fmt: skip
    )


def test_a_list_page_loads_no_more_than_ten_possible_matches_per_event(db, caplog):
    many = current_event(db, "EVT-A00000000001", TELANGANA_TODAY)
    others = [current_event(db, f"EVT-B{n:011d}", THE_HINDU) for n in range(LISTED_MATCHES_PER_EVENT + 5)]
    for other in others:
        pend(db, many.event_id, other.event_id)
    db.commit()

    with caplog.at_level(logging.WARNING, logger="app.services.merge_service"):
        outs = {out.event_id: out for out in to_event_outs(db, [many, others[0]])}

    assert len(outs[many.event_id].merge_candidates) == LISTED_MATCHES_PER_EVENT
    # The other side of a pair is listed as before.
    assert len(outs[others[0].event_id].merge_candidates) == 1
    assert any(many.event_id in record.getMessage() for record in caplog.records)


def test_a_list_page_lists_every_possible_match_of_an_event_with_few(db, caplog):
    event = current_event(db, "EVT-A00000000001", TELANGANA_TODAY)
    others = [current_event(db, f"EVT-B{n:011d}", THE_HINDU) for n in range(3)]
    for other in others:
        pend(db, event.event_id, other.event_id)
    db.commit()

    with caplog.at_level(logging.WARNING, logger="app.services.merge_service"):
        (out,) = to_event_outs(db, [event])

    assert len(out.merge_candidates) == 3
    assert not caplog.records


def test_an_event_that_may_match_more_than_a_hundred_open_events_gets_no_pair(db, caplog):
    for n in range(merge_service.MAX_MATCHES_PER_EVENT + 1):
        current_event(db, f"EVT-B{n:011d}", THE_HINDU)
    new = current_event(db, "EVT-A00000000001", TELANGANA_TODAY)

    with caplog.at_level(logging.WARNING, logger="app.services.merge_service"):
        run = merge_service.find_candidates(db, event_ids=[new.event_id])
    db.commit()

    assert run.too_many == [new.event_id]
    assert run.candidates == 0 and run.auto_merged == 0
    assert db.query(EventMergeCandidate).count() == 0
    assert any(new.event_id in record.getMessage() for record in caplog.records)


def test_an_event_that_may_match_a_hundred_open_events_is_matched_as_before(db):
    for n in range(merge_service.MAX_MATCHES_PER_EVENT):
        current_event(db, f"EVT-B{n:011d}", THE_HINDU)
    new = current_event(db, "EVT-A00000000001", TELANGANA_TODAY)

    run = merge_service.find_candidates(db, event_ids=[new.event_id])
    db.commit()

    assert run.too_many == []
    assert run.candidates >= 1
