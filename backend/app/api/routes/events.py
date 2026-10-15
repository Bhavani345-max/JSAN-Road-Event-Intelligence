from collections import Counter
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.auth_deps import CurrentUserDep
from app.api.deps import ResolverDep, SessionDep
from app.repositories.events import EventRepository, to_event_out, to_event_outs
from app.schemas.event import (
    CityEventCountOut,
    EventSummaryOut,
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
from packages.cities import default_city, load_cities
from packages.event_schema import EventSeverity, EventStatus
from services.lifecycle.current import EventListView
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
    include_hidden: Annotated[
        bool,
        Query(
            description=(
                "Also list the events the console hides: without a location, without a "
                "stated start and end, or ended (for audit and tools)."
            )
        ),
    ] = False,
    view: Annotated[
        EventListView,
        Query(
            description=(
                "Server-side view: current_upcoming (default), current, upcoming, "
                "validation, history, or rejected."
            )
        ),
    ] = EventListView.CURRENT_UPCOMING,
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
        include_hidden=include_hidden,
        view=view,
        q=q,
        limit=limit,
        offset=offset,
    )
    return EventListOut(items=to_event_outs(session, rows), total=total)


@router.post("", response_model=EventOut, status_code=201)
def add_event(
    body: ManualEventIn, session: SessionDep, resolver: ResolverDep, user: CurrentUserDep
) -> EventOut:
    """Enter a road event that no connected source reported.

    The entry is stored as evidence under the "Manual entry" source, with the
    reviewer's stated basis. The event starts as VALIDATION_REQUIRED and is
    located only if `place` is a known Hyderabad place name.
    """
    row = create_manual_event(
        session, resolver, entered_by=user.email, **body.model_dump()
    )
    return to_event_outs(session, [row])[0]


@router.get("/summary", response_model=EventSummaryOut)
def summarize_events(
    session: SessionDep,
    view: Annotated[
        EventListView,
        Query(description="current_upcoming (default) or validation: the console view counted"),
    ] = EventListView.CURRENT_UPCOMING,
) -> EventSummaryOut:
    """Per configured city, how many events the console's view lists, by status and type.

    For the overview of all cities: no event is loaded or returned.
    """
    if view not in (EventListView.CURRENT_UPCOMING, EventListView.VALIDATION):
        raise HTTPException(status_code=422, detail="Only current_upcoming and validation are counted")
    counts = EventRepository(session).count_shown_by_city(view)
    # Events stored before cities existed are Hyderabad's (as the list treats them).
    legacy = counts.pop(None, None)
    cities = []
    for city in load_cities().values():
        found = counts.get(city.name) or {"status": Counter(), "type": Counter()}
        if legacy and city.name == default_city().name:
            found = {key: found[key] + legacy[key] for key in ("status", "type")}
        cities.append(
            CityEventCountOut(
                city_id=city.id,
                city_name=city.name,
                total=sum(found["status"].values()),
                by_status=dict(found["status"]),
                by_type=dict(found["type"]),
            )
        )
    return EventSummaryOut(view=view.value, cities=cities)


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
def update_event_status(
    event_id: str, body: StatusUpdateIn, session: SessionDep, user: CurrentUserDep
) -> EventOut:
    """Record a human review decision, e.g. VALIDATION_REQUIRED -> QC_PENDING or REJECTED."""
    try:
        row = review_service.update_event_status(
            session, event_id, body.status, body.reason, body.severity,
            reviewer=user.email, force=body.force
        )
    except review_service.EventNotFound:
        raise HTTPException(status_code=404, detail="Event not found") from None
    except review_service.ReasonRequired as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except InvalidTransition as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    return to_event_outs(session, [row])[0]


@router.post("/{event_id}/severity", response_model=EventOut)
def set_event_severity(
    event_id: str, body: SeverityIn, session: SessionDep, user: CurrentUserDep
) -> EventOut:
    """Record a reviewer's REI severity (LOW, MEDIUM, HIGH or CRITICAL) for an event."""
    try:
        row = review_service.set_event_severity(
            session, event_id, body.severity, body.reason, reviewer=user.email
        )
    except review_service.EventNotFound:
        raise HTTPException(status_code=404, detail="Event not found") from None
    except review_service.InvalidSeverity as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    return to_event_outs(session, [row])[0]


@router.post("/{event_id}/extend", response_model=EventOut)
def extend_event(event_id: str, body: ExtendIn, session: SessionDep, user: CurrentUserDep) -> EventOut:
    """Record that an event runs longer than recorded, on a reviewer's knowledge."""
    try:
        row = review_service.extend_event(
            session, event_id, body.end_date, body.reason, reviewer=user.email
        )
    except review_service.EventNotFound:
        raise HTTPException(status_code=404, detail="Event not found") from None
    except review_service.InvalidExtension as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    return to_event_outs(session, [row])[0]


@router.post("/{event_id}/location", response_model=EventOut)
def set_event_location(
    event_id: str, body: LocationIn, session: SessionDep, resolver: ResolverDep,
    user: CurrentUserDep,
) -> EventOut:
    """Put an event at the spot a reviewer picked on the map."""
    try:
        row = review_service.set_event_location(
            session, resolver, event_id, reviewer=user.email, **body.model_dump()
        )
    except review_service.EventNotFound:
        raise HTTPException(status_code=404, detail="Event not found") from None
    except review_service.InvalidLocation as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    return to_event_outs(session, [row])[0]
