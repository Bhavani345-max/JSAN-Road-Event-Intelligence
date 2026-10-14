"""Rows an official source lists for one event become one event (14 October 2026).

NYC DOT lists a block's closure once per permit purpose. The fixture holds
real rows for one block of Vanderbilt Avenue (segment 35822): three for
15 September - 15 October 2026 and two for 26 September - 25 December 2026.
They are two closures of the block, not five, and the map showed five markers
on one spot. Every row stays as evidence: merging links, never deletes.
"""

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings
from app.main import create_app
from app.models import Event, EventMergeCandidate
from app.repositories.events import to_rei_event
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from app.services import merge_service
from connectors.official.nyc import nyc_source, same_closure_key, to_record
from packages.cities import get_city
from services.extraction import KeywordClassifier
from services.ingestion import run_ingestion
from tests.support import FakeConnector, sign_in

FIXTURE = Path(__file__).parents[1] / "fixtures" / "nyc_street_closures_2026-10-13.json"
FEATURES = json.loads(FIXTURE.read_text(encoding="utf-8"))["features"]
NOW = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
NYC = get_city("new-york")
SOURCE = nyc_source(scheduled=False)
OCTOBER = "NYC DOT segment 35822, work period 2026-09-15 04:00 to 2026-10-15 04:00 UTC"
DECEMBER = "NYC DOT segment 35822, work period 2026-09-26 04:00 to 2026-12-25 05:00 UTC"


def run(session, features):
    result = run_ingestion(
        FakeConnector([to_record(feature, NOW) for feature in features], source=SOURCE),
        KeywordClassifier.for_city(NYC),
        SqlIngestionStore(session),
        None,
        NYC,
    )
    session.commit()
    return result


@pytest.fixture
def nyc(session):
    SourceRepository(session).sync_registry([SOURCE])
    session.commit()
    run(session, FEATURES)
    return session


def events(session) -> list[Event]:
    session.expire_all()
    return session.scalars(select(Event).order_by(Event.created_at, Event.event_id)).unique().all()


def listed(session) -> list[Event]:
    return [row for row in events(session) if row.merged_into is None]


def merge(session):
    run = merge_service.merge_listed_rows(session, SOURCE.source_id)
    session.commit()
    return run


def test_rows_of_one_closure_share_the_segment_and_work_period(nyc):
    keys = [same_closure_key(to_rei_event(row)) for row in events(nyc)]
    assert sorted(keys) == [OCTOBER, OCTOBER, OCTOBER, DECEMBER, DECEMBER]


def test_rows_of_one_closure_become_one_event_and_every_row_is_kept(nyc):
    run = merge(nyc)
    assert (run.auto_merged, run.candidates) == (3, 0)

    rows = events(nyc)
    assert len(rows) == 5  # nothing deleted
    shown = listed(nyc)
    assert sorted(same_closure_key(to_rei_event(row)) for row in shown) == [OCTOBER, DECEMBER]
    for canonical in shown:
        members = [row for row in rows if row.merged_into == canonical.event_id]
        contributed = {c["event_id"] for c in canonical.detection["contributions"]}
        assert contributed == {member.event_id for member in members}
        assert not canonical.detection.get("merge_conflicts")
    reasons = [c.reasons[0] for c in nyc.scalars(select(EventMergeCandidate)).all()]
    assert len(reasons) == 3
    assert all("lists one event in several rows" in reason for reason in reasons)


def test_merging_again_changes_nothing(nyc):
    merge(nyc)
    again = merge(nyc)
    assert (again.auto_merged, again.candidates) == (0, 0)
    assert len(listed(nyc)) == 2


def test_a_row_a_reviewer_acted_on_is_left_for_a_reviewer(nyc):
    reviewed = next(row for row in events(nyc) if same_closure_key(to_rei_event(row)) == OCTOBER)
    reviewed.status = "QC_PENDING"
    nyc.commit()

    run = merge(nyc)
    # October: the two untouched rows merge; the reviewed one is a candidate.
    # December: its two rows merge.
    assert (run.auto_merged, run.candidates) == (2, 1)
    pending = nyc.scalars(
        select(EventMergeCandidate).where(EventMergeCandidate.status == "PENDING")
    ).one()
    assert reviewed.event_id in (pending.event_a, pending.event_b)
    assert "merged only by a reviewer" in pending.reasons[-1]


def test_another_source_s_rows_are_never_grouped(session):
    assert merge_service.merge_listed_rows(session, "tfl-road-disruptions").compared == 0


def feature_of(row: Event) -> dict:
    return next(f for f in FEATURES if f["properties"]["uniqueid"] == row.artifact.external_id)


def revised_end(feature, end):
    changed = copy.deepcopy(feature)
    changed["properties"]["work_end_date"] = end
    return changed


def test_a_row_whose_period_the_source_revises_is_listed_on_its_own_again(nyc):
    merge(nyc)
    october = [row for row in events(nyc) if same_closure_key(to_rei_event(row)) == OCTOBER]
    member = next(row for row in october if row.merged_into)
    feature = feature_of(member)

    run(nyc, [revised_end(feature, "2026-11-15T00:00:00.000")])
    merge(nyc)

    separated = next(row for row in events(nyc) if row.event_id == member.event_id)
    assert separated.merged_into is None
    assert "listed on its own again" in separated.versions[-1].change_reason
    assert len(listed(nyc)) == 3  # October (2 rows), October-November (1), December (2)


def test_when_the_merged_event_s_own_row_is_revised_the_others_regroup(nyc):
    merge(nyc)
    canonical = next(row for row in listed(nyc) if same_closure_key(to_rei_event(row)) == OCTOBER)
    feature = feature_of(canonical)

    run(nyc, [revised_end(feature, "2026-11-15T00:00:00.000")])
    regrouped = merge(nyc)

    assert regrouped.auto_merged == 1  # the two other October rows, merged again
    shown = listed(nyc)
    assert len(shown) == 3
    assert sorted(same_closure_key(to_rei_event(row)) for row in shown).count(OCTOBER) == 1


def test_an_ingestion_run_merges_the_rows_it_brings(engine, session):
    settings = Settings(
        _env_file=None, database_url="sqlite://", auto_migrate=False,
        ingestion_scheduler_enabled=False, event_matching_after_ingestion=True,
    )  # fmt: skip
    app = create_app(settings, engine=engine)
    records = [to_record(feature, NOW) for feature in FEATURES]
    app.state.ingestion_service.connector_factories = {
        SOURCE.source_id: lambda: FakeConnector(records, source=SOURCE)
    }
    with TestClient(app) as client:
        sign_in(client)
        response = client.post("/api/ingestion/run", params={"source_id": SOURCE.source_id})
        assert response.status_code == 200
    assert len(events(session)) == 5
    assert len(listed(session)) == 2
