from fastapi import APIRouter, HTTPException

from app.api.deps import SessionDep
from app.repositories.sources import SourceRepository
from app.schemas.source import SourceOut
from packages.source_models import IntegrationStatus

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceOut])
def list_sources(
    session: SessionDep, integration_status: IntegrationStatus | None = None
) -> list[SourceOut]:
    """The source registry: connected sources and researched, unconnected ones."""
    sources = SourceRepository(session)
    return [
        sources.to_out(source)
        for source in sources.list()
        if integration_status is None or source.integration_status == integration_status.value
    ]


@router.get("/{source_id}", response_model=SourceOut)
def get_source(source_id: str, session: SessionDep) -> SourceOut:
    sources = SourceRepository(session)
    source = sources.get(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return sources.to_out(source)
