"""The source list and the coverage share one count of every event, counted again
after any commit (23 October 2026: with 30,000 events each count took seconds, and
the console's parallel requests and retries ran past the web proxy's 30 s limit)."""

import threading
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models import Event
from app.repositories import events as events_repository
from app.repositories.events import EventRepository
from tests.api.test_source_status import ingest
from tests.support import TEST_SOURCE

NOW = datetime.now(timezone.utc)
POINT = {"type": "Point", "coordinates": [78.4867, 17.385]}


def _counted(monkeypatch) -> list[int]:
    """Records each count of all events."""
    calls: list[int] = []
    count_all = EventRepository._count_all

    def counting(self, now):
        calls.append(1)
        return count_all(self, now)

    monkeypatch.setattr(EventRepository, "_count_all", counting)
    return calls


def test_one_count_serves_both_groupings_until_a_commit(client, session, monkeypatch):
    ingest(client)
    calls = _counted(monkeypatch)
    by_source = EventRepository(session).tally(by="source")
    by_city = EventRepository(session).tally(by="city")
    assert len(calls) == 1
    detected = by_source[TEST_SOURCE.source_id]["detected"]
    assert detected > 0 and by_source[TEST_SOURCE.source_id]["validated"] == 0
    assert sum(found["detected"] for found in by_city.values()) == detected

    row = session.scalars(select(Event)).first()
    row.status = "APPROVED"
    session.commit()
    assert EventRepository(session).tally(by="source")[TEST_SOURCE.source_id]["validated"] == 1
    assert len(calls) == 2


def test_the_shared_count_is_the_fresh_count(client, session):
    ingest(client)
    for by in ("source", "city"):
        assert EventRepository(session).tally(by=by) == EventRepository(session).tally(by=by, now=NOW)


def test_a_caller_may_change_its_counts(client, session):
    ingest(client)
    first = EventRepository(session).tally(by="city")
    first.clear()
    assert EventRepository(session).tally(by="city")


def test_requests_during_a_count_wait_for_it(client, session_factory, monkeypatch):
    ingest(client)
    calls = []
    count_all = EventRepository._count_all

    def slow(self, now):
        calls.append(1)
        time.sleep(0.2)
        return count_all(self, now)

    monkeypatch.setattr(EventRepository, "_count_all", slow)
    results = []

    def request(by):
        with session_factory() as session:
            results.append(EventRepository(session).tally(by=by))

    threads = [threading.Thread(target=request, args=(by,)) for by in ("source", "city") * 3]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(calls) == 1 and len(results) == 6


def test_a_count_is_redone_once_it_is_a_minute_old(client, session, monkeypatch):
    ingest(client)
    calls = _counted(monkeypatch)
    EventRepository(session).tally(by="source")
    shared = events_repository._shared_tally(session.get_bind().engine)
    shared.counted_at -= timedelta(seconds=61)
    EventRepository(session).tally(by="source")
    assert len(calls) == 2


def test_the_database_reads_the_detection_facts_the_map_rules_need(client, session):
    """Only `source_reports_ended` and `method` are read from each detection record."""
    ingest(client)
    ended, lapsed = session.scalars(select(Event).order_by(Event.event_id)).all()[:2]
    for row in (ended, lapsed):
        row.geometry, row.status = POINT, "APPROVED"
    ended.start_time, ended.end_time = NOW - timedelta(days=1), NOW + timedelta(days=1)
    ended.detection = {**ended.detection, "source_reports_ended": True}
    # Read from an article, with a start and no end, over 30 days ago.
    assert lapsed.detection["method"] == "keyword_rules"
    lapsed.start_time, lapsed.end_time = NOW - timedelta(days=40), None
    session.commit()

    found = EventRepository(session).tally(by="source")[TEST_SOURCE.source_id]
    assert found["hidden_operations_source_ended"] == 1
    assert found["hidden_operations_open_end_lapsed"] == 1
    assert found["on_map_operations"] == 0
