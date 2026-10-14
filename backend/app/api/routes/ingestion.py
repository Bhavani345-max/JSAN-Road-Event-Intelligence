from fastapi import APIRouter, HTTPException

from app.api.deps import IngestionServiceDep
from app.schemas.source import IngestionRunOut
from app.services.ingestion_service import UnknownSource

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/run", response_model=IngestionRunOut)
def run_ingestion(service: IngestionServiceDep, source_id: str | None = None) -> IngestionRunOut:
    """Fetch sources now instead of waiting for the next scheduled poll.

    Without `source_id`, every active source is fetched. A source that cannot
    be reached is reported as failed in the result rather than as an HTTP error.
    """
    if source_id is None:
        return IngestionRunOut(results=service.run_all_active())
    try:
        return IngestionRunOut(results=[service.run_source(source_id)])
    except UnknownSource:
        raise HTTPException(
            status_code=404, detail="No ingestable source with that id"
        ) from None
