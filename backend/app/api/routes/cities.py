from fastapi import APIRouter, HTTPException

from app.schemas.city import CityOut
from packages.cities import area_of, load_cities

router = APIRouter(prefix="/cities", tags=["cities"])


def area_names(city_id: str | None) -> list[str] | None:
    """The city names events record for a configured id: the city's own, or a
    country entry's and those of the cities within it (decision 0035)."""
    if city_id is None:
        return None
    configured = load_cities().get(city_id)
    if configured is None:
        raise HTTPException(status_code=422, detail=f"Unknown city {city_id!r}")
    return [city.name for city in area_of(configured)]


@router.get("", response_model=list[CityOut])
def list_cities() -> list[CityOut]:
    """Every configured city, the default first."""
    return [CityOut.from_city(city) for city in load_cities().values()]


@router.get("/{city_id}", response_model=CityOut)
def get_city_out(city_id: str) -> CityOut:
    city = load_cities().get(city_id)
    if city is None:
        raise HTTPException(status_code=404, detail="City not found")
    return CityOut.from_city(city)
