"""Which lifecycle status changes are allowed.

Fail-safe rule: an event can only reach a status in which it would be treated
as a real, located road event (APPROVED and beyond) once it has geometry and a
start time. An unlocated or undated event stays in review.
"""

from packages.event_schema import EventStatus, LocationClass, ReiEvent

S = EventStatus

ALLOWED_TRANSITIONS: dict[EventStatus, set[EventStatus]] = {
    S.DISCOVERED: {S.EXTRACTED, S.VALIDATION_REQUIRED, S.REJECTED},
    S.EXTRACTED: {S.GEO_RESOLVED, S.VALIDATION_REQUIRED, S.REJECTED},
    S.GEO_RESOLVED: {S.VALIDATION_REQUIRED, S.QC_PENDING, S.REJECTED},
    S.VALIDATION_REQUIRED: {S.QC_PENDING, S.REJECTED},
    S.QC_PENDING: {S.APPROVED, S.VALIDATION_REQUIRED, S.REJECTED},
    S.APPROVED: {S.SCHEDULED, S.ACTIVE, S.CANCELLED, S.SUPERSEDED},
    S.SCHEDULED: {S.ACTIVE, S.CANCELLED, S.MODIFIED, S.SUPERSEDED},
    S.ACTIVE: {S.MONITORING, S.EXTENDED, S.MODIFIED, S.EXPIRED, S.CANCELLED, S.SUPERSEDED},
    S.MONITORING: {S.ACTIVE, S.EXTENDED, S.EXPIRED, S.SUPERSEDED},
    S.EXTENDED: {S.ACTIVE, S.MONITORING, S.EXPIRED, S.SUPERSEDED},
    S.MODIFIED: {S.SCHEDULED, S.ACTIVE, S.CANCELLED, S.SUPERSEDED},
    S.EXPIRED: {S.REOPENED},
    S.REOPENED: {S.ACTIVE, S.MONITORING, S.EXPIRED},
    S.REJECTED: {S.VALIDATION_REQUIRED},
    S.CANCELLED: set(),
    S.SUPERSEDED: set(),
}

# Statuses that assert the event is real and located.
REQUIRES_LOCATION_AND_TIME = {
    S.APPROVED, S.SCHEDULED, S.ACTIVE, S.MONITORING, S.EXTENDED, S.MODIFIED, S.REOPENED,
}


class InvalidTransition(Exception):
    pass


def check_transition(
    event: ReiEvent, new_status: EventStatus, *, override_checks: bool = False
) -> None:
    """Raise InvalidTransition unless `event` may move to `new_status`.

    `override_checks`: a reviewer approves anyway (decision 0022). The
    location and start-time checks are skipped; which statuses may follow
    which is never overridden.
    """
    if new_status not in ALLOWED_TRANSITIONS[event.status]:
        raise InvalidTransition(f"An event cannot go from {event.status} to {new_status}.")
    if override_checks:
        return
    if new_status in REQUIRES_LOCATION_AND_TIME and (
        event.geometry is None or event.start_time is None
    ):
        raise InvalidTransition(
            f"An event needs a resolved location and a start time before it can be {new_status}."
        )
    # A named place's position (a locality, a junction looked up by name) is
    # where the place is, not where the event is. It cannot be approved as the
    # event's location: a reviewer corrects it first ("Correct location").
    location_class = event.detection.location_class if event.detection else None
    gis = event.detection.gis if event.detection else None
    if (
        new_status in REQUIRES_LOCATION_AND_TIME
        and location_class is LocationClass.GIS_RESOLVED
        and (gis is None or gis.review_status != "APPROVED")
    ):
        raise InvalidTransition(
            "The location is a GIS proposal that no reviewer has approved yet. Approve or "
            f"correct the location before the event can be {new_status}."
        )
    if new_status in REQUIRES_LOCATION_AND_TIME and location_class is LocationClass.APPROXIMATE:
        raise InvalidTransition(
            "The location is approximate (the position of a place the source names). "
            "Correct the location on the map before the event can be "
            f"{new_status}."
        )


def approval_blockers(event: ReiEvent) -> list[str]:
    """Every QC requirement `event` does not yet meet for approval, in plain words.

    Empty exactly when check_transition(event, APPROVED) would pass. It applies
    the same rules as check_transition, but lists all unmet ones instead of
    stopping at the first, so a reviewer sees everything that is missing.
    """
    blockers: list[str] = []
    if S.APPROVED not in ALLOWED_TRANSITIONS[event.status]:
        blockers.append(f"Only an event in QC_PENDING can be approved; this one is {event.status}.")
    if event.geometry is None:
        blockers.append("It has no resolved location.")
    if event.start_time is None:
        blockers.append("It has no start time.")
    location_class = event.detection.location_class if event.detection else None
    gis = event.detection.gis if event.detection else None
    if location_class is LocationClass.GIS_RESOLVED and (
        gis is None or gis.review_status != "APPROVED"
    ):
        blockers.append(
            "The location is a GIS proposal that no reviewer has approved yet: "
            "approve or correct the location first."
        )
    if location_class is LocationClass.APPROXIMATE:
        blockers.append(
            "The location is approximate (the position of a place the source names): "
            "correct the location on the map first."
        )
    return blockers
