from datetime import date

from sqlalchemy.orm import Session

from app.models import Event
from app.repositories.events import EventRepository, to_rei_event
from packages.common.time import end_of_day, ensure_utc, utc_now
from packages.cities import default_city, load_cities
from packages.event_schema import (
    EventLocation,
    EventSeverity,
    EventStatus,
    LocationClass,
    LocationRevision,
    PeriodRevision,
    QcApproval,
    SeverityAssessment,
)
from packages.geo_models import Point
from services.geo_resolution import PlaceResolver, resolver_for
from services.lifecycle import check_transition
from services.lifecycle.transitions import (
    REQUIRES_LOCATION_AND_TIME,
    InvalidTransition,
    approval_blockers,
)

# There is no authentication yet, so every change is attributed to this name.
LOCAL_REVIEWER = "local-reviewer"


# An event in one of these is over or was never one; it is reopened, not extended.
_NOT_EXTENDABLE = {
    EventStatus.REJECTED, EventStatus.CANCELLED, EventStatus.SUPERSEDED, EventStatus.EXPIRED,
}  # fmt: skip


class EventNotFound(Exception):
    pass


class InvalidExtension(Exception):
    pass


class InvalidLocation(Exception):
    pass


class InvalidSeverity(Exception):
    pass


def _assess_severity(row: Event, severity: EventSeverity, reason: str | None, now) -> None:
    """Put a reviewer's REI severity on the event, with who, when and why.

    The value is the reviewer's own judgment. The source's severity words
    (detection.source_severity) are not touched. The caller records the version.
    """
    row.severity = severity.value
    row.detection = {
        **(row.detection or {}),
        "severity_assessment": SeverityAssessment(
            severity=severity,
            assessed_by=LOCAL_REVIEWER,
            assessed_at=now,
            reason=reason,
            version=row.version + 1,
        ).model_dump(mode="json"),
    }


def set_event_severity(
    session: Session, event_id: str, severity: EventSeverity, reason: str | None
) -> Event:
    """Record a reviewer's REI severity for an event as a new version.

    Raises EventNotFound or InvalidSeverity (the event is over or rejected).
    """
    events = EventRepository(session)
    row = events.get(event_id)
    if row is None:
        raise EventNotFound(event_id)
    if EventStatus(row.status) in _NOT_EXTENDABLE:
        raise InvalidSeverity(f"An event that is {row.status} cannot be given a severity.")
    now = utc_now()
    _assess_severity(row, severity, reason, now)
    row.version += 1
    row.updated_at = now
    events.record_version(
        row,
        change_reason=f"REI severity set to {severity.value} by a reviewer."
        + (f" {reason}" if reason else ""),
        changed_by=LOCAL_REVIEWER,
    )
    session.commit()
    return row


REVIEWER_PLACED = "reviewer_placed"


class ReasonRequired(ValueError):
    """Approving anyway needs the reviewer's reason."""


# The words of the location checks in approval_blockers(): overriding one of
# these keeps the location's own class (it does not become QC_APPROVED).
_LOCATION_CHECKS = ("no resolved location", "location is approximate", "GIS proposal")


def update_event_status(
    session: Session,
    event_id: str,
    new_status: EventStatus,
    reason: str | None,
    severity: EventSeverity | None = None,
    force: bool = False,
) -> Event:
    """Apply a human review decision and record it as a new event version.

    `severity`, when the reviewer gives one with the decision, is REI's own
    severity and is recorded in the same version.

    `force`: approve anyway, overriding the QC checks the event does not meet
    (decision 0022). Only an approval can be forced, only from QC_PENDING, and
    only with a reason. The overridden checks are recorded with the approval
    and in the version history; an approximate location stays approximate.

    Raises EventNotFound, ReasonRequired or services.lifecycle.InvalidTransition.
    """
    events = EventRepository(session)
    row = events.get(event_id)
    if row is None:
        raise EventNotFound(event_id)

    event = to_rei_event(row)
    overridden: list[str] = []
    if force:
        if new_status is not EventStatus.APPROVED:
            raise InvalidTransition("Only an approval can be made anyway.")
        if not reason or len(reason.strip()) < 5:
            raise ReasonRequired("Give a reason for approving despite the unmet checks.")
        overridden = [b for b in approval_blockers(event) if not b.startswith("Only an event in")]
    check_transition(event, new_status, override_checks=force)

    now = utc_now()
    if severity is not None:
        _assess_severity(row, severity, reason, now)
        reason = (
            f"{reason} REI severity {severity.value}." if reason else f"REI severity {severity.value}."
        )
    if new_status is EventStatus.APPROVED and (row.geometry is not None or overridden):
        # The reviewer accepts the event with this location. How it was
        # obtained stays in detection.location (source, reviewer, GIS). A
        # location check the reviewer overrode keeps the location's own class:
        # an approximate position is still drawn and reported as approximate.
        detection = dict(row.detection or {})
        location_overridden = any(
            check in blocker for blocker in overridden for check in _LOCATION_CHECKS
        )
        if row.geometry is not None and not location_overridden:
            detection["location_class"] = LocationClass.QC_APPROVED.value
        detection["qc_approval"] = QcApproval(
            approved_by=LOCAL_REVIEWER,
            approved_at=now,
            reason=reason,
            version=row.version + 1,
            forced=bool(overridden),
            overridden=overridden,
        ).model_dump(mode="json")
        row.detection = detection
        if overridden:
            reason = f"Approved anyway, overriding: {' '.join(overridden)} Reason: {reason}"
    row.status = new_status.value
    row.version += 1
    row.updated_at = now
    events.record_version(row, change_reason=reason, changed_by=LOCAL_REVIEWER)
    session.commit()
    return row


def _city_of(row: Event):
    """The configured city of an event; the default city (Hyderabad) when it has none."""
    return next((c for c in load_cities().values() if c.name == row.city), None) or default_city()


def extend_event(session: Session, event_id: str, end_date: date | None, reason: str) -> Event:
    """Record a reviewer's knowledge that an event runs longer than recorded.

    `end_date` is the new last day (a whole day in the event's city's time zone;
    India Standard Time for an event with no city), or None for "until
    further notice". The previous end, the reviewer's reason and the time of
    the change are kept with the event, and the change is a new version.

    Raises EventNotFound or InvalidExtension.
    """
    events = EventRepository(session)
    row = events.get(event_id)
    if row is None:
        raise EventNotFound(event_id)
    if EventStatus(row.status) in _NOT_EXTENDABLE:
        raise InvalidExtension(f"An event that is {row.status} cannot be extended.")

    event = to_rei_event(row)
    zone = _city_of(row).tz
    # Held in UTC like every stored time; it is the last second of that day in the city.
    new_end = ensure_utc(end_of_day(end_date, zone)) if end_date else None
    if new_end is None:
        if event.start_time is None:
            raise InvalidExtension(
                "This event has no start date, so give the day it runs until."
            )
        if event.end_time is None:
            raise InvalidExtension("This event already runs until further notice.")
    else:
        if event.start_time and new_end < event.start_time:
            raise InvalidExtension("The new end date is before the event starts.")
        if event.end_time and new_end <= event.end_time:
            raise InvalidExtension(
                "The new end date must be later than the current one "
                f"({event.end_time.astimezone(zone).date().isoformat()})."
            )

    now = utc_now()
    revision = PeriodRevision(
        previous_end=event.end_time, reason=reason, revised_by=LOCAL_REVIEWER, revised_at=now
    )
    # A new dict, so the JSON column is seen to have changed.
    row.detection = {**(row.detection or {}), "period_revision": revision.model_dump(mode="json")}
    row.end_time = new_end
    row.version += 1
    row.updated_at = now
    until = end_date.isoformat() if end_date else "further notice"
    events.record_version(
        row, change_reason=f"Extended until {until}. {reason}", changed_by=LOCAL_REVIEWER
    )
    session.commit()
    return row


def set_event_location(
    session: Session,
    resolver: PlaceResolver,
    event_id: str,
    *,
    longitude: float,
    latitude: float,
    place_name: str,
    reason: str,
) -> Event:
    """Put an event at the spot a reviewer picked on the map.

    For an event the automatic lookup placed only roughly (at a locality's
    label, say) or not at all. The point is the reviewer's, and is recorded as
    such with the name they gave the spot and their reason; where the event
    was located before stays in the history.

    Raises EventNotFound or InvalidLocation.
    """
    events = EventRepository(session)
    row = events.get(event_id)
    if row is None:
        raise EventNotFound(event_id)
    if EventStatus(row.status) in _NOT_EXTENDABLE:
        raise InvalidLocation(f"An event that is {row.status} cannot be relocated.")
    if EventStatus(row.status) in REQUIRES_LOCATION_AND_TIME:
        raise InvalidLocation(
            f"An event that is {row.status} was approved with its location; "
            "send it back to review to move it."
        )
    # The area of the event's own city; Hyderabad's for events with no city.
    city = next(
        (c for c in load_cities().values() if c.name == row.city), None
    ) or default_city()
    area = resolver if city.id == default_city().id and resolver is not None else resolver_for(city)
    if not area.covers(latitude, longitude):
        raise InvalidLocation(
            f"That spot is outside {city.area_name or city.name}, the area REI covers."
        )

    now = utc_now()
    detection = dict(row.detection or {})
    previous = detection.get("location") or {}
    detection["location"] = EventLocation(
        method=REVIEWER_PLACED,
        place_name=place_name,
        place_kind="spot",
        precision="place",
        mention=place_name,
        found_in="review",
        reference=f"placed on the map by {LOCAL_REVIEWER}",
    ).model_dump(mode="json")
    detection["location_class"] = LocationClass.HUMAN_CORRECTED.value
    # A reviewer's own placement outranks any GIS proposal.
    from app.services.gis_service import supersede_on_correction

    detection = supersede_on_correction(detection)
    detection["location_revision"] = LocationRevision(
        previous_place_name=previous.get("place_name"),
        reason=reason,
        revised_by=LOCAL_REVIEWER,
        revised_at=now,
    ).model_dump(mode="json")
    row.detection = detection
    row.geometry = Point(type="Point", coordinates=(longitude, latitude)).model_dump(mode="json")
    row.version += 1
    row.updated_at = now
    events.record_version(
        row,
        change_reason=(
            f"Located at {place_name} ({latitude:.5f}, {longitude:.5f}) by a reviewer. {reason}"
        ),
        changed_by=LOCAL_REVIEWER,
    )
    session.commit()
    return row
