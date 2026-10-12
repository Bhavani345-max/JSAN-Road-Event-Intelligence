"""QC approval blockers (7 October 2026).

`approval_blockers` lists every QC requirement an event does not meet for
approval. It must agree with `check_transition`, which enforces the rules:
no blockers exactly when approval is allowed.
"""

from datetime import datetime, timezone
from itertools import product

import pytest

from packages.event_schema import (
    EventDetection,
    EventStatus,
    GisResolution,
    LocationClass,
    ReiEvent,
)
from packages.geo_models import Point
from services.lifecycle import InvalidTransition, approval_blockers, check_transition

NOW = datetime(2026, 10, 7, tzinfo=timezone.utc)


def event(*, status=EventStatus.QC_PENDING, located=True, dated=True, location_class=None, gis_review=None):
    detection = None
    if location_class is not None:
        gis = (
            GisResolution(engine="test", network="test", resolved_at=NOW, review_status=gis_review)
            if gis_review
            else None
        )
        detection = EventDetection(
            method="keyword_rules", matched_keywords=[], location_class=location_class, gis=gis
        )
    return ReiEvent(
        event_id="EVT-QC0000000001", source_id="test", title="Test closure", status=status,
        geometry=Point(type="Point", coordinates=[78.35, 17.44]) if located else None,
        start_time=NOW if dated else None, detection=detection, created_at=NOW, updated_at=NOW,
    )  # fmt: skip


def approvable(e: ReiEvent) -> bool:
    try:
        check_transition(e, EventStatus.APPROVED)
    except InvalidTransition:
        return False
    return True


def test_an_event_meeting_every_requirement_has_no_blockers():
    for location_class in (
        LocationClass.HUMAN_CORRECTED, LocationClass.SOURCE_PROVIDED, None,
    ):  # fmt: skip
        assert approval_blockers(event(location_class=location_class)) == []
    assert approval_blockers(event(location_class=LocationClass.GIS_RESOLVED, gis_review="APPROVED")) == []


def test_every_unmet_requirement_is_listed_not_only_the_first():
    blockers = approval_blockers(
        event(located=False, dated=False, location_class=LocationClass.APPROXIMATE)
    )
    assert len(blockers) == 3
    assert any("no resolved location" in b for b in blockers)
    assert any("no start time" in b for b in blockers)
    assert any("approximate" in b for b in blockers)


@pytest.mark.parametrize("review", [None, "PENDING", "REJECTED"])
def test_an_unapproved_gis_proposal_blocks_approval(review):
    blockers = approval_blockers(event(location_class=LocationClass.GIS_RESOLVED, gis_review=review))
    assert blockers == [
        "The location is a GIS proposal that no reviewer has approved yet: "
        "approve or correct the location first."
    ]


@pytest.mark.parametrize("status", [EventStatus.VALIDATION_REQUIRED, EventStatus.REJECTED, EventStatus.APPROVED])
def test_only_an_event_in_qc_pending_can_be_approved(status):
    assert any("QC_PENDING" in b for b in approval_blockers(event(status=status)))


def test_blockers_agree_with_the_enforced_rules_in_every_combination():
    classes = [None, *LocationClass]
    statuses = [EventStatus.QC_PENDING, EventStatus.VALIDATION_REQUIRED]
    for status, located, dated, location_class, gis_review in product(
        statuses, [True, False], [True, False], classes, [None, "PENDING", "APPROVED"]
    ):
        e = event(
            status=status, located=located, dated=dated,
            location_class=location_class, gis_review=gis_review,
        )  # fmt: skip
        assert (approval_blockers(e) == []) == approvable(e), (status, located, dated, location_class, gis_review)
