from pydantic import BaseModel

from packages.cities import City


class CityOut(BaseModel):
    """A configured city as the console needs it."""

    id: str
    name: str
    country: str
    region: str | None
    timezone: str
    language: str
    # south, west, north, east
    bbox: tuple[float, float, float, float]
    # [longitude, latitude]
    map_center: tuple[float, float]
    map_zoom: float
    scope_terms: list[str]
    official_sources: list[str]
    # The zone each regional source's times are shown in, where it differs.
    source_time_zones: dict[str, str]
    # Whether a place list exists for locating events by name.
    has_gazetteer: bool

    @classmethod
    def from_city(cls, city: City) -> "CityOut":
        from services.geo_resolution import resolver_for

        return cls(
            id=city.id,
            name=city.name,
            country=city.country,
            region=city.region,
            timezone=city.timezone,
            language=city.language,
            bbox=city.bbox,
            map_center=city.map.center,
            map_zoom=city.map.zoom,
            scope_terms=list(city.scope_terms),
            official_sources=list(city.official_sources),
            source_time_zones=dict(city.source_time_zones),
            has_gazetteer=len(resolver_for(city)) > 0,
        )
