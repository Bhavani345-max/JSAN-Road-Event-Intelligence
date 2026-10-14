from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import ResolverDep
from app.schemas.event import PlaceOut
from packages.cities import load_cities
from services.geo_resolution import resolver_for

router = APIRouter(prefix="/places", tags=["places"])


@router.get("", response_model=list[PlaceOut])
def suggest_places(
    resolver: ResolverDep,
    q: Annotated[str, Query(min_length=2, max_length=100)],
    city: Annotated[str | None, Query(description="A configured city id")] = None,
) -> list[PlaceOut]:
    """Known places of the city matching what has been typed, for locating a manual entry."""
    if city is not None:
        configured = load_cities().get(city)
        if configured is None:
            raise HTTPException(status_code=422, detail=f"Unknown city {city!r}")
        resolver = resolver_for(configured)
    return [PlaceOut(name=match.name, kind=match.kind) for match in resolver.suggest(q)]
