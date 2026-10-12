from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import ResolverDep, SessionDep
from app.repositories.events import EventRepository, to_event_out, to_event_outs
from app.schemas.event import (
    EventDetailOut,
    EventListOut,
    EventOut,
    EventVersionOut,
    ExtendIn,
    LocationIn,
    ManualEventIn,
    SeverityIn,
    StatusUpdateIn,
)
from app.services import review_service
from app.services.manual_event_service import create_manual_event
from packages.cities import load_cities
from packages.event_schema import EventSeverity, EventStatus
from services.lifecycle import InvalidTransition

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=EventListOut)
def list_events(
    session: SessionDep,
    status: EventStatus | None = None,
    severity: Annotated[
        EventSeverity | None, Query(description="REI severity (LOW, MEDIUM, HIGH, CRITICAL), never the source's")
    ] = None,
    source_id: str | None = None,
    city: Annotated[str | None, Query(description="A configured city id, e.g. hyderabad")] = None,
    include_merged: Annotated[
        bool, Query(description="Also list events merged into another (shown as part of it)")
    ] = False,
    q: Annotated[
        str | None,
        Query(
            max_length=200,
            description="Words to find in the event, its source, or the article it came from.",
        ),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EventListOut:
    city_name: str | None = None
    if city is not None:
        configured = load_cities().get(city)
        if configured is None:
            raise HTTPException(status_code=422, detail=f"Unknown city {city!r}")
        city_name = configured.name
    rows, total = EventRepository(session).list(
        status=status,
        severity=severity,
        source_id=source_id,
        city=city_name,
        include_merged=include_merged,
        q=q,
        limit=limit,
        offset=offset,
    )
    return EventListOut(items=to_event_outs(session, rows), total=total)


@router.post("", response_model=EventOut, status_code=201)
def add_event(body: ManualEventIn, session: SessionDep, resolver: ResolverDep) -> EventOut:
    """Enter a road event that no connected source reported.

    The entry is stored as evidence under the "Manual entry" source, with the
    reviewer's stated basis. The event starts as VALIDATION_REQUIRED and is
    located only if `place` is a known Hyderabad place name.
    """
    row = create_manual_event(
        session, resolver, entered_by=review_service.LOCAL_REVIEWER, **body.model_dump()
    )
    return to_event_outs(session, [row])[0]


@router.get("/{event_id}", response_model=EventDetailOut)
def get_event(event_id: str, session: SessionDep) -> EventDetailOut:
    row = EventRepository(session).get(event_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventDetailOut(
        **to_event_outs(session, [row])[0].model_dump(),
        versions=[
            EventVersionOut(
                version=version.version,
                status=EventStatus(version.status),
                change_reason=version.change_reason,
                changed_by=version.changed_by,
                created_at=version.created_at,
            )
            for version in row.versions
        ],
    )


@router.post("/{event_id}/status", response_model=EventOut)
def update_event_status(event_id: str, body: StatusUpdateIn, session: SessionDep) -> EventOut:
    """Record a human review decision, e.g. VALIDATION_REQUIRED -> QC_PENDING or REJECTED."""
    try:
        row = review_service.update_event_status(
            session, event_id, body.status, body.reason, body.severity, force=body.force
        )
    except review_service.EventNotFound:
        raise HTTPException(status_code=404, detail="Event not found") from None
    except review_service.ReasonRequired as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except InvalidTransition as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    return to_event_outs(session, [row])[0]


@router.post("/{event_id}/severity", response_model=EventOut)
def set_event_severity(event_id: str, body: SeverityIn, session: SessionDep) -> EventOut:
    """Record a reviewer's REI severity (LOW, MEDIUM, HIGH or CRITICAL) for an event."""
    try:
        row = review_service.set_event_severity(session, event_id, body.severity, body.reason)
    except review_service.EventNotFound:
        raise HTTPException(status_code=404, detail="Event not found") from None
    except review_service.InvalidSeverity as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    return to_event_outs(session, [row])[0]


@router.post("/{event_id}/extend", response_model=EventOut)
def extend_event(event_id: str, body: ExtendIn, session: SessionDep) -> EventOut:
    """Record that an event runs longer than recorded, on a reviewer's knowledge."""
    try:
        row = review_service.extend_event(session, event_id, body.end_date, body.reason)
    except review_service.EventNotFound:
        raise HTTPException(status_code=404, detail="Event not found") from None
    except review_service.InvalidExtension as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    return to_event_outs(session, [row])[0]


@router.post("/{event_id}/location", response_model=EventOut)
def set_event_location(
    event_id: str, body: LocationIn, session: SessionDep, resolver: ResolverDep
) -> EventOut:
    """Put an event at the spot a reviewer picked on the map."""
    try:
        row = review_service.set_event_location(session, resolver, event_id, **body.model_dump())
    except review_service.EventNotFound:
        raise HTTPException(status_code=404, detail="Event not found") from None
    except review_service.InvalidLocation as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    return to_event_outs(session, [row])[0]
