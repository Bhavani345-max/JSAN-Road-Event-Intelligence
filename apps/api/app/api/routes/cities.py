from fastapi import APIRouter, HTTPException

from app.schemas.city import CityOut
from packages.cities import load_cities

router = APIRouter(prefix="/cities", tags=["cities"])


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
