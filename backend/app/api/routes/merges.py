from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.auth_deps import CurrentUserDep
from app.api.deps import SessionDep
from app.models import Event, EventMergeCandidate
from app.repositories.events import source_summary, to_event_outs
from app.schemas.event import EventOut, MergeCandidateOut, MergeDecisionIn, MergeGroupDecisionIn
from app.services import merge_service
from packages.cities import load_cities

router = APIRouter(prefix="/merge-candidates", tags=["merging"])


def _out(session, candidate: EventMergeCandidate, side: str) -> MergeCandidateOut:
    """A candidate as seen from one of its events (`side` is event_a's or event_b's id)."""
    other = session.get(Event, candidate.event_b if candidate.event_a == side else candidate.event_a)
    return MergeCandidateOut(
        candidate_id=candidate.id,
        classification=candidate.classification,
        status=candidate.status,
        reasons=candidate.reasons or [],
        conflicts=candidate.conflicts or [],
        other_event_id=other.event_id,
        other_title=other.title,
        other_source=source_summary(other.source),
        decided_by=candidate.decided_by,
        decision_reason=candidate.decision_reason,
    )


@router.get("", response_model=list[MergeCandidateOut])
def list_candidates(
    session: SessionDep,
    status: Annotated[str | None, Query(description="PENDING, AUTO_MERGED, CONFIRMED, REJECTED")] = None,
    city: Annotated[str | None, Query(description="A configured city id")] = None,
) -> list[MergeCandidateOut]:
    """Pairs of events that may be the same, seen from their first event."""
    query = select(EventMergeCandidate).order_by(EventMergeCandidate.id)
    if status:
        query = query.where(EventMergeCandidate.status == status.upper())
    city_name = None
    if city is not None:
        configured = load_cities().get(city)
        if configured is None:
            raise HTTPException(status_code=422, detail=f"Unknown city {city!r}")
        city_name = configured.name
    found = []
    for candidate in session.scalars(query):
        first = session.get(Event, candidate.event_a)
        if city_name and first.city != city_name:
            continue
        found.append(_out(session, candidate, candidate.event_a))
    return found


@router.post("/confirm-all", response_model=EventOut)
def confirm_all(body: MergeGroupDecisionIn, session: SessionDep, user: CurrentUserDep) -> EventOut:
    """A reviewer says all these candidates of one event are the same event: merge them all."""
    try:
        canonical = merge_service.confirm_all(
            session, body.candidate_ids, reviewer=user.email, reason=body.reason
        )
    except merge_service.CandidateNotFound:
        raise HTTPException(status_code=404, detail="Candidate not found") from None
    except merge_service.CandidateDecided as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except merge_service.NotOneGroup as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return to_event_outs(session, [canonical])[0]


@router.post("/{candidate_id}/confirm", response_model=EventOut)
def confirm(
    candidate_id: int, body: MergeDecisionIn, session: SessionDep, user: CurrentUserDep
) -> EventOut:
    """A reviewer says the two are the same event: merge them, keeping all evidence."""
    try:
        canonical = merge_service.confirm(
            session, candidate_id, reviewer=user.email, reason=body.reason
        )
    except merge_service.CandidateNotFound:
        raise HTTPException(status_code=404, detail="Candidate not found") from None
    except merge_service.CandidateDecided as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    return to_event_outs(session, [canonical])[0]


@router.post("/{candidate_id}/reject", response_model=MergeCandidateOut)
def reject(
    candidate_id: int, body: MergeDecisionIn, session: SessionDep, user: CurrentUserDep
) -> MergeCandidateOut:
    """A reviewer says they are different events: they stay apart."""
    try:
        candidate = merge_service.reject(
            session, candidate_id, reviewer=user.email, reason=body.reason
        )
    except merge_service.CandidateNotFound:
        raise HTTPException(status_code=404, detail="Candidate not found") from None
    except merge_service.CandidateDecided as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    return _out(session, candidate, candidate.event_a)
