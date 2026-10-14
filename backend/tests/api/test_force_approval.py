"""Approving anyway (9 October 2026, decision 0022).

A reviewer may approve an event in QC_PENDING that does not meet the QC
checks, with a reason. The checks overridden are recorded with the approval
and in the version history; an approximate location stays approximate.
"""

from .test_qc_approval import DLF_CLOSURE, client, confirmed, event_titled  # noqa: F401

UNDATED = "Waterlogging at Tolichowki slows traffic in Hyderabad"
WHY = "Confirmed with the traffic police by phone; the spot is right"


def force(client, event, reason=WHY, status="APPROVED"):
    return client.post(
        f"/api/events/{event['event_id']}/status",
        json={"status": status, "reason": reason, "force": True},
    )


def test_an_event_with_unmet_checks_can_be_approved_anyway(client):
    event = confirmed(client, UNDATED)
    blockers = event["approval_blockers"]
    assert any("start time" in b for b in blockers) and any("approximate" in b for b in blockers)
    # The ordinary approval is still refused.
    plain = client.post(f"/api/events/{event['event_id']}/status", json={"status": "APPROVED", "reason": WHY})
    assert plain.status_code == 409

    response = force(client, event)
    assert response.status_code == 200
    approved = event_titled(client, UNDATED)
    assert approved["status"] == "APPROVED"
    approval = approved["detection"]["qc_approval"]
    assert approval["forced"] is True and approval["reason"] == WHY
    assert approval["overridden"] == blockers
    # Still drawn and reported as approximate: overriding does not make it exact.
    assert approved["detection"]["location_class"] == "APPROXIMATE"
    history = client.get(f"/api/events/{event['event_id']}").json()["versions"]
    assert history[-1]["change_reason"].startswith("Approved anyway, overriding:")
    assert WHY in history[-1]["change_reason"]


def test_approving_anyway_needs_a_reason(client):
    event = confirmed(client, UNDATED)
    for reason in (None, "", "ok"):
        response = force(client, event, reason=reason)
        assert response.status_code == 422
    assert event_titled(client, UNDATED)["status"] == "QC_PENDING"


def test_only_an_approval_from_qc_pending_can_be_forced(client):
    in_validation = event_titled(client, DLF_CLOSURE)
    assert force(client, in_validation).status_code == 409
    event = confirmed(client, UNDATED)
    assert force(client, event, status="REJECTED").status_code == 409
    assert event_titled(client, UNDATED)["status"] == "QC_PENDING"


def test_forcing_an_event_that_meets_every_check_is_an_ordinary_approval(client):
    event = confirmed(client, DLF_CLOSURE)
    client.post(
        f"/api/events/{event['event_id']}/location",
        json={"longitude": 78.35223, "latitude": 17.44556, "place_name": "IIIT Junction", "reason": "At this junction"},
    )
    assert event_titled(client, DLF_CLOSURE)["approval_blockers"] == []
    assert force(client, event).status_code == 200
    approval = event_titled(client, DLF_CLOSURE)["detection"]["qc_approval"]
    assert approval["forced"] is False and approval["overridden"] == []
    assert event_titled(client, DLF_CLOSURE)["detection"]["location_class"] == "QC_APPROVED"
