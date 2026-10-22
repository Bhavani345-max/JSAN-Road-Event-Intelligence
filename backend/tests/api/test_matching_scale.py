"""Matching finds exactly what comparing every pair finds, without comparing every pair
(decision 0040).

An ingestion run's new events are compared only with open events of their own city
that share an article or a link, a place or a road name, or a map cell next to
theirs; two records of one official source are never compared. On 21 October 2026
the old way took 6 GB and minutes for one 18,000-event run.
"""

import random
from datetime import timedelta
from itertools import combinations

from sqlalchemy import select

from app.models import Event, EventMergeCandidate
from app.services import merge_service
from app.services.merge_service import facts
from connectors.official import tfl_source
from connectors.rss.the_hindu import THE_HINDU
from connectors.rss.telangana_today import TELANGANA_TODAY
from services.merging import MatchClass, compare
from tests.api.test_merging_api import KHAJAGUDA, T0, add, db  # noqa: F401  (db is a fixture)

PLACES = ["Khajaguda Jn", "Gachibowli", "Raidurg", "Madhapur", "Kondapur"]
TITLES = [
    "Traffic diversions at Khajaguda junction",
    "Road closed near Gachibowli flyover",
    "Metro works: diversions in Madhapur",
    "Waterlogging slows traffic in Raidurg",
]


def mixed_events(session, count: int = 70) -> list[str]:
    """Events close together and far apart, with and without shared names or
    articles, located and not, in two cities, from news feeds and one official source."""
    rng = random.Random(40)
    sources = [TELANGANA_TODAY, THE_HINDU, tfl_source(scheduled=False)]
    ids = []
    for n in range(count):
        source = sources[n % 3]
        # Up to about 3 km from Khajaguda: some within 300 m, most not.
        spread = rng.choice([0.001, 0.003, 0.01, 0.03])
        position = None if n % 11 == 0 else (KHAJAGUDA[0] + rng.uniform(-spread, spread), KHAJAGUDA[1] + rng.uniform(-spread, spread))
        start = T0 + timedelta(days=rng.choice([0, 1, 30]))
        event_id = f"EVT-SCALE{n:06d}"
        add(
            session, event_id, source, rng.choice(TITLES) + ("" if n % 4 else f" (update {n})"),
            place=rng.choice(PLACES), kind=rng.choice(["junction", "area"]), position=position,
            method="source_provided" if source.source_id == "tfl-road-disruptions" else "named_place",
            event_type=rng.choice(["TRAFFIC_DIVERSION", "ROAD_WORKS"]),
            start=start, end=start + timedelta(days=rng.choice([1, 5])),
            city="London" if n % 9 == 0 else "Hyderabad", created=T0 + timedelta(minutes=n),
        )  # fmt: skip
        ids.append(event_id)
    return ids


def every_pair(session, focus: set[str]) -> dict[tuple[str, str], str]:
    """The old way: every open event against every other, by compare() alone."""
    pool = merge_service._open_events(session, None)
    found = {}
    for a, b in combinations(pool, 2):
        if a.event_id not in focus and b.event_id not in focus:
            continue
        if a.city != b.city:
            continue
        match = compare(facts(a), facts(b))
        if match.classification is not MatchClass.DIFFERENT:
            found[merge_service._pair(a.event_id, b.event_id)] = match.classification.value
    return found


def test_only_pairs_that_can_match_are_compared_and_nothing_is_missed(db, monkeypatch):
    ids = mixed_events(db)
    # Current at the time of the test, whatever today is.
    monkeypatch.setattr(merge_service, "is_current_row", lambda row, now=None: True)
    expected = every_pair(db, set(ids))
    assert len(expected) > 20, "the mix must hold enough possible matches to mean anything"

    run = merge_service.find_candidates(db, event_ids=ids, automatic=False)
    found = {
        (c.event_a, c.event_b): c.classification
        for c in db.scalars(select(EventMergeCandidate))
    }
    assert found == expected
    assert run.candidates == len(expected)
    # Never more comparisons than every pair of one city.
    same_city = sum(1 for a, b in combinations(ids, 2) if db.get(Event, a).city == db.get(Event, b).city)
    assert run.compared <= same_city


def test_a_large_official_feed_is_compared_only_where_a_match_is_possible(db, monkeypatch):
    """1,500 records of one official source over a region and 50 news reports:
    every pair is 1.2 million comparisons; only neighbours and shared names are compared."""
    import time

    official, news = tfl_source(scheduled=False), TELANGANA_TODAY
    rng = random.Random(7)
    ids = []
    for n in range(1550):
        source = official if n < 1500 else news
        position = (78.0 + rng.uniform(0, 1.0), 17.0 + rng.uniform(0, 1.0))
        event_id = f"EVT-LARGE{n:06d}"
        add(
            db, event_id, source, f"Works on street {n}", place=f"Street {n}", kind="area",
            position=position, method="source_provided" if source is official else "named_place",
            event_type="ROAD_WORKS", start=T0, end=T0 + timedelta(days=3), created=T0 + timedelta(seconds=n),
        )  # fmt: skip
        ids.append(event_id)
    monkeypatch.setattr(merge_service, "is_current_row", lambda row, now=None: True)
    started = time.perf_counter()
    run = merge_service.find_candidates(db, event_ids=ids, automatic=False)
    took = time.perf_counter() - started
    assert run.compared < 5_000  # instead of about 1.2 million
    assert took < 30


def test_a_run_compares_its_events_only_with_its_own_city(db, monkeypatch):
    ids = mixed_events(db)
    monkeypatch.setattr(merge_service, "is_current_row", lambda row, now=None: True)
    london = [event_id for event_id in ids if db.get(Event, event_id).city == "London"]
    loaded = []
    original = merge_service._open_events_where
    monkeypatch.setattr(
        merge_service, "_open_events_where",
        lambda session, filters: loaded.extend(original(session, filters)) or loaded,
    )  # fmt: skip
    merge_service.find_candidates(db, event_ids=london, automatic=False)
    assert loaded and {row.city for row in loaded} == {"London"}


def test_a_page_many_events_share_is_not_taken_for_one_article(db, monkeypatch):
    """22 October 2026: every NDW record gave the portal's home page as its
    reference, and all 14,343 Dutch events were compared as "the same article"."""
    monkeypatch.setattr(merge_service, "is_current_row", lambda row, now=None: True)
    shared_page = "https://portal.example/"
    ids = []
    for n in range(2 * (merge_service.SHARED_URL_EVENTS + 1)):
        source = tfl_source(scheduled=False) if n % 2 else TELANGANA_TODAY
        # Far apart (about 11 km between neighbours), different types, same period.
        row = add(
            db, f"EVT-SHARED{n:04d}", source, f"Unrelated works number {n}", place=f"Place {n}",
            position=(KHAJAGUDA[0] + 0.1 * n, KHAJAGUDA[1]), method="source_provided",
            event_type="ROAD_WORKS" if n % 2 else "TRAFFIC_DIVERSION",
            start=T0, end=T0 + timedelta(days=3), city="London",
        )  # fmt: skip
        row.source_reference = shared_page
        ids.append(row.event_id)
    db.commit()
    rows = {row.event_id: row for row in db.scalars(select(Event).where(Event.event_id.in_(ids)))}
    # The trap: compared directly, a shared address makes two unrelated events "one article".
    assert compare(facts(rows[ids[0]]), facts(rows[ids[1]])).classification is not MatchClass.DIFFERENT
    run = merge_service.find_candidates(db, event_ids=ids)
    db.commit()
    assert run.candidates == 0 and run.auto_merged == 0
    assert db.scalars(select(EventMergeCandidate)).first() is None
