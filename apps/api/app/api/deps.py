from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.services.ingestion_service import IngestionService
from services.geo_resolution import PlaceResolver, default_resolver


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


def get_ingestion_service(request: Request) -> IngestionService:
    return request.app.state.ingestion_service


SessionDep = Annotated[Session, Depends(get_session)]
IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]
ResolverDep = Annotated[PlaceResolver, Depends(default_resolver)]
