from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from app.api.deps import ResolverDep
from app.schemas.event import PlaceOut
from packages.cities import load_cities
from app.services.place_search import ATTRIBUTION, PlaceSearchFailed, local_results
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


@router.get("/search")
def search_places(
    request: Request,
    q: Annotated[str, Query(min_length=2, max_length=100)],
    city: Annotated[str | None, Query(description="A configured city or country id; none for everywhere")] = None,
    local_only: Annotated[bool, Query(description="Only REI's own place lists (while typing)")] = False,
) -> dict:
    """A place name or postcode in the chosen country or city, for moving the map there (decision 0055).

    While typing, only REI's own OpenStreetMap place lists answer; on Enter,
    OpenStreetMap's geocoder (Nominatim) too, within its usage policy.
    """
    configured = None
    if city is not None:
        configured = load_cities().get(city)
        if configured is None:
            raise HTTPException(status_code=422, detail=f"Unknown city {city!r}")
    if local_only:
        results = local_results(" ".join(q.split()), configured)
    else:
        try:
            results = request.app.state.place_search.search(q, configured)
        except PlaceSearchFailed as error:
            raise HTTPException(status_code=502, detail=str(error)) from None
    return {
        "results": results,
        "scope": configured.name if configured else None,
        "attribution": ATTRIBUTION,
    }
