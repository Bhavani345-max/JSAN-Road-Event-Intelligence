from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select

from app.api.auth_deps import CurrentUserDep
from app.api.deps import SessionDep
from app.models import JunctionReference
from app.repositories.events import EventRepository, to_event_outs
from app.schemas.event import EventOut, GisChoiceIn, GisDecisionIn, JunctionOut
from app.services import gis_service

router = APIRouter(tags=["gis"])


def _junction_out(row: JunctionReference) -> JunctionOut:
    return JunctionOut.model_validate(row, from_attributes=True)


@router.get("/junctions", response_model=list[JunctionOut])
def list_junctions(
    session: SessionDep, city: Annotated[str | None, Query(description="A configured city id")] = None
) -> list[JunctionOut]:
    """Junction references: names the resolver may use once a reviewer has confirmed them."""
    query = select(JunctionReference).order_by(JunctionReference.junction_id)
    if city:
        query = query.where(JunctionReference.city == city)
    return [_junction_out(row) for row in session.scalars(query)]


def _decide_junction(
    session, junction_id: int, body: GisDecisionIn, confirm: bool, reviewer: str
) -> JunctionOut:
    try:
        row = gis_service.decide_junction(
            session, junction_id, confirm=confirm, reviewer=reviewer, reason=body.reason,
            method="reviewer, in the REI console",
        )  # fmt: skip
    except gis_service.JunctionNotFound:
        raise HTTPException(status_code=404, detail="Junction reference not found") from None
    except gis_service.GisActionRefused as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    return _junction_out(row)


@router.post("/junctions/{junction_id}/confirm", response_model=JunctionOut)
def confirm_junction(
    junction_id: int, body: GisDecisionIn, session: SessionDep, user: CurrentUserDep
) -> JunctionOut:
    return _decide_junction(session, junction_id, body, True, user.email)


@router.post("/junctions/{junction_id}/reject", response_model=JunctionOut)
def reject_junction(
    junction_id: int, body: GisDecisionIn, session: SessionDep, user: CurrentUserDep
) -> JunctionOut:
    return _decide_junction(session, junction_id, body, False, user.email)


def _gis_action(session, action) -> EventOut:
    try:
        row = action()
    except LookupError:
        raise HTTPException(status_code=404, detail="Event not found") from None
    except gis_service.GisActionRefused as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    return to_event_outs(session, [row])[0]


@router.post("/events/{event_id}/gis/approve", response_model=EventOut)
def approve_gis(
    event_id: str, body: GisDecisionIn, session: SessionDep, user: CurrentUserDep
) -> EventOut:
    """A reviewer accepts the GIS location proposed for the event."""
    return _gis_action(session, lambda: gis_service.approve(session, event_id, reviewer=user.email, reason=body.reason))


@router.post("/events/{event_id}/gis/reject", response_model=EventOut)
def reject_gis(
    event_id: str, body: GisDecisionIn, session: SessionDep, user: CurrentUserDep
) -> EventOut:
    """A reviewer rejects the GIS location; the previous location is restored."""
    return _gis_action(session, lambda: gis_service.reject(session, event_id, reviewer=user.email, reason=body.reason))


@router.post("/events/{event_id}/gis/choose", response_model=EventOut)
def choose_gis(
    event_id: str, body: GisChoiceIn, session: SessionDep, user: CurrentUserDep
) -> EventOut:
    """A reviewer picks one GIS candidate (e.g. of an ambiguous result) as the location."""
    return _gis_action(session, lambda: gis_service.choose(
        session, event_id, result_index=body.result_index, alternative_index=body.alternative_index,
        reviewer=user.email, reason=body.reason,
    ))  # fmt: skip


@router.post("/events/{event_id}/gis/resolve", response_model=EventOut)
def resolve_gis(
    event_id: str, request: Request, session: SessionDep
) -> EventOut:
    """Run the GIS resolver on one event now (needs the road network database)."""
    row = EventRepository(session).get(event_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Event not found")
    city = gis_service.get_network_city(row)
    if city is None:
        raise HTTPException(status_code=409, detail="There is no road network for this event's city.")
    url = request.app.state.settings.gis_database_url
    if not url:
        raise HTTPException(status_code=503, detail="GIS resolution is not configured (GIS_DATABASE_URL).")
    from services.gis_resolution.postgis import PostGISRoadNetwork, connect

    try:
        with connect(url) as conn:
            network = PostGISRoadNetwork(conn, city.id)
            gis_service.resolve_event(session, row, gis_service.engine_for(session, city, network))
    except (OSError, LookupError, Exception) as error:  # noqa: BLE001 - a missing database is a 503
        if isinstance(error, HTTPException):
            raise
        session.rollback()
        raise HTTPException(status_code=503, detail=f"The road network is not available: {error}") from None
    session.commit()
    return to_event_outs(session, [row])[0]
