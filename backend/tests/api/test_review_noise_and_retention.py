"""Less to review and less to store (7 October 2026).

- Only current events (upcoming, ongoing, recently reported) are compared and
  asked about as possibly the same event; a candidate involving an event that
  is over stays recorded, but nobody is asked about it.
- One decision can merge all the reports of one story.
- The text of old articles that are not road events is removed; a stub stops
  them being stored again. Events and their evidence are kept.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import Event, EventMergeCandidate, SourceArtifact
from app.repositories.ingestion_store import SqlIngestionStore
from app.services import merge_service
from app.services.reprocess_service import reprocess_stored_evidence
from app.services.retention_service import TEXT_REMOVED, slim_unrelated_articles
from connectors.rss.siasat import SIASAT
from connectors.rss.telangana_today import TELANGANA_TODAY
from connectors.rss.the_hindu import THE_HINDU
from packages.common.time import utc_now
from services.extraction import KeywordClassifier
from services.geo_resolution import default_resolver
from services.ingestion import run_ingestion
from tests.support import TEST_SOURCE, FakeConnector, khajaguda_article

from .test_merging_api import add, by_id, candidates, db  # noqa: F401  (db is a fixture)

KBR = {"place": "KBR Park", "kind": "landmark", "position": (78.4201, 17.4202), "event_type": None}
ENDED = datetime(2026, 9, 27, tzinfo=timezone.utc)


def kbr_reports(db, *ids_sources_titles, **extra):
    for event_id, source, title in ids_sources_titles:
        add(db, event_id, source, title, **KBR, **extra.get(event_id, {}))


THREE_KBR_REPORTS = (
    ("EVT-A", TELANGANA_TODAY, "KBR flyover plan changed due to success of one way traffic"),
    ("EVT-B", SIASAT, "GHMC revises KBR Park flyover plans, mulls permanent one-way"),
    ("EVT-C", THE_HINDU, "KBR Park one-way traffic system to stay, GHMC drops flyover"),
)


# --- only current events are asked about ----------------------------------------------


def test_an_event_that_has_ended_is_not_compared(db):
    kbr_reports(db, *THREE_KBR_REPORTS[:2], **{"EVT-B": {"start": ENDED - timedelta(days=1), "end": ENDED}})
    run = merge_service.find_candidates(db)
    assert run.candidates == 0 and candidates(db) == []


def test_a_candidate_is_not_asked_once_an_event_is_over_and_comes_back_if_extended(db):
    kbr_reports(db, *THREE_KBR_REPORTS[:2])
    merge_service.find_candidates(db, automatic=False)
    db.commit()
    assert set(merge_service.pending_candidates_by_event(db)) == {"EVT-A", "EVT-B"}

    ended = by_id(db, "EVT-B")
    ended.start_time, ended.end_time = ENDED - timedelta(days=1), ENDED
    db.commit()
    assert merge_service.pending_candidates_by_event(db) == {}
    # Still recorded, not decided.
    assert [c.status for c in candidates(db)] == ["PENDING"]

    extended = by_id(db, "EVT-B")
    extended.end_time = utc_now() + timedelta(days=30)
    db.commit()
    assert set(merge_service.pending_candidates_by_event(db)) == {"EVT-A", "EVT-B"}


# --- one decision for the reports of one story ---------------------------------------


def test_all_the_reports_of_one_story_are_merged_by_one_decision(db):
    kbr_reports(db, *THREE_KBR_REPORTS)
    merge_service.find_candidates(db, automatic=False)
    db.commit()
    asked = merge_service.pending_candidates_by_event(db)["EVT-A"]
    assert len(asked) == 2  # A–B and A–C; B–C is asked on B's and C's panels

    canonical = merge_service.confirm_all(
        db, [c.id for c in asked], reviewer="local-reviewer", reason="All report the KBR one-way decision"
    )
    members = {e.event_id for e in db.scalars(select(Event).where(Event.merged_into == canonical.event_id))}
    assert members | {canonical.event_id} == {"EVT-A", "EVT-B", "EVT-C"}
    assert merge_service.pending_candidates_by_event(db) == {}
    statuses = {c.status for c in candidates(db)}
    assert "PENDING" not in statuses and "CONFIRMED" in statuses
    contributions = by_id(db, canonical.event_id).detection["contributions"]
    assert {c["merged_by"] for c in contributions} == {"local-reviewer"}
    assert {c["reason"] for c in contributions} == {"All report the KBR one-way decision"}


def test_one_decision_covers_only_candidates_of_one_event(db):
    kbr_reports(db, *THREE_KBR_REPORTS)
    merge_service.find_candidates(db, automatic=False)
    db.commit()
    every = [c.id for c in candidates(db)]  # A–B, A–C, B–C: no event is in all three
    with pytest.raises(merge_service.NotOneGroup):
        merge_service.confirm_all(db, every, reviewer="local-reviewer", reason="All the same")
    assert all(e.merged_into is None for e in db.scalars(select(Event)))


def test_one_decision_for_several_candidates_through_the_api(client, session):
    for event_id, _source, title in THREE_KBR_REPORTS:
        add(session, event_id, TEST_SOURCE, title, **KBR)
    merge_service.find_candidates(session, automatic=False)
    session.commit()
    event = client.get("/api/events/EVT-A").json()
    ids = [c["candidate_id"] for c in event["merge_candidates"]]
    assert len(ids) == 2

    assert client.post("/api/merge-candidates/confirm-all", json={"candidate_ids": [], "reason": "Same"}).status_code == 422
    response = client.post(
        "/api/merge-candidates/confirm-all", json={"candidate_ids": ids, "reason": "Same KBR story"}
    )
    assert response.status_code == 200
    assert len(response.json()["other_evidence"]) == 2
    again = client.post("/api/merge-candidates/confirm-all", json={"candidate_ids": ids, "reason": "Same KBR story"})
    assert again.status_code == 409


# --- the text of old articles that are not road events --------------------------------


def unrelated_article(published_at):
    title = "Harish Rao praises Marasam's role in Telangana literary activism"
    return khajaguda_article().model_copy(
        update={
            "source_id": TEST_SOURCE.source_id,
            "external_id": "https://news.example.com/literary-activism",
            "url": "https://news.example.com/literary-activism",
            "title": title,
            "summary": "A tribute to a poet's role in the state's literary life.",
            "content_text": "A long article about literature. " * 50,
            "published_at": published_at,
            "raw": {
                "guid": "p=1598006", "link": "https://news.example.com/literary-activism",
                "title": title, "published": "Fri, 02 Oct 2026 11:30:25 +0000",
                "summary_html": "<p>A tribute.</p>", "content_html": "<p>Literature</p>" * 200,
            },
        }
    )  # fmt: skip


def ingest(session, records):
    result = run_ingestion(
        FakeConnector(records), KeywordClassifier.from_file(), SqlIngestionStore(session), default_resolver()
    )
    session.commit()
    return result


def artifact(session, url):
    session.expire_all()
    return session.scalars(select(SourceArtifact).where(SourceArtifact.url == url)).one()


def test_an_old_unrelated_article_keeps_only_a_stub_and_is_not_stored_again(session):
    old = utc_now() - timedelta(days=20)
    road = khajaguda_article().model_copy(update={"source_id": TEST_SOURCE.source_id, "published_at": old})
    unrelated = unrelated_article(old)
    first = ingest(session, [road, unrelated])
    assert first.new_artifacts == 2 and first.events_created == 1

    result = slim_unrelated_articles(session, older_than_days=14)
    assert result.articles == 1 and result.bytes_removed > 3000

    stub = artifact(session, unrelated.url)
    assert set(stub.raw_content) == {"guid", "link", "title", "published", TEXT_REMOVED}
    assert stub.title == unrelated.title and stub.content_hash == unrelated.content_hash
    assert stub.classification == "NOT_RELEVANT"
    # The road event's article and the event are untouched.
    assert "content_html" in artifact(session, road.url).raw_content
    assert session.scalars(select(Event)).one().source_artifact_id == artifact(session, road.url).artifact_id

    # The feed still lists the article: it is recognised, not stored again.
    again = ingest(session, [road, unrelated])
    assert again.new_artifacts == 0 and again.duplicates == 2
    # Running it again changes nothing.
    assert slim_unrelated_articles(session, older_than_days=14).articles == 0


def test_a_recent_unrelated_article_keeps_its_text_and_a_preview_changes_nothing(session):
    # Without a publication time, the retrieval time counts: retrieved now.
    ingest(session, [unrelated_article(utc_now() - timedelta(days=3)), unrelated_article(None).model_copy(
        update={"external_id": "x2", "url": "https://news.example.com/x2", "retrieved_at": utc_now()})])  # fmt: skip
    assert slim_unrelated_articles(session, older_than_days=14).articles == 0

    old = unrelated_article(utc_now() - timedelta(days=20)).model_copy(
        update={"external_id": "x3", "url": "https://news.example.com/x3"}
    )
    ingest(session, [old])
    assert slim_unrelated_articles(session, older_than_days=14, dry_run=True).articles == 1
    assert TEXT_REMOVED not in artifact(session, old.url).raw_content


def test_reprocessing_skips_the_stubs(session):
    ingest(session, [unrelated_article(utc_now() - timedelta(days=20))])
    slim_unrelated_articles(session, older_than_days=14)
    result = reprocess_stored_evidence(session, KeywordClassifier.from_file(), default_resolver())
    assert result.artifacts == 0 and result.created == 0
