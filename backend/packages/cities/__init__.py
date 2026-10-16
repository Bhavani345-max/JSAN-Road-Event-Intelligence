"""City configuration: everything about a city that the pipeline must not hard-code.

Each city is one JSON file in `data/`. Adding a city means adding a file and
registering its sources; the ingestion framework, detection, location and
console read what they need from here.

A city file states:

- `id`, `name`, `country` (ISO 3166-1 alpha-2), `region`, `timezone` (IANA),
  `language` (BCP 47 primary subtag);
- `level`: "city" (the default) or "country". A country entry (Canada) holds
  the country's national and regional sources; the cities configured with the
  same `country` code (Toronto) are within it. Choosing the country covers its
  own events and its cities' events; choosing a city covers that city's only
  (decision 0035). A country has at most one country entry;
- `bbox`: south, west, north, east — the area REI covers for the city. An
  event placed outside it is not that city's;
- `map`: where the console's map starts for the city;
- `scope_terms`: words that place an article in the city ("Hyderabad",
  "Secunderabad"); `other_cities`: names that mean an article is about
  somewhere else, over and above the shared list in the keyword rules;
- `gazetteer`: the place file under services/geo_resolution/data, built from
  OpenStreetMap for the city's bbox; `keywords`: the detection rules file;
- `discovery.queries`: the searches a discovery source runs for the city;
- `official_sources`, `gis_sources`: source ids from the registry.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, model_validator

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_CITY_ID = "hyderabad"


class MapView(BaseModel):
    model_config = ConfigDict(frozen=True)

    # [longitude, latitude]
    center: tuple[float, float]
    zoom: float = Field(ge=1, le=20)


class Discovery(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Searches a discovery source runs for the city, in the words the local
    # press uses. Each names the city or an authority of it.
    queries: tuple[str, ...] = ()
    # GDELT DOC searches (connectors/discovery/gdelt.py); empty: the city's
    # name with REI's road phrases.
    gdelt_queries: tuple[str, ...] = ()


class City(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9-]{1,40}$")
    name: str
    # How the covered area is called in messages: "Greater Hyderabad".
    area_name: str | None = None
    country: str = Field(min_length=2, max_length=2)
    # "country": the entry for a whole country, with its cities within it.
    level: Literal["city", "country"] = "city"
    region: str | None = None
    timezone: str
    language: str = "en"
    # south, west, north, east
    bbox: tuple[float, float, float, float]
    map: MapView
    scope_terms: tuple[str, ...] = Field(min_length=1)
    other_cities: tuple[str, ...] = ()
    gazetteer: str | None = None
    # The areas (south, west, north, east) the place list is built from, when
    # not the whole bbox: a country's metro areas, not all of its land.
    gazetteer_areas: tuple[tuple[float, float, float, float], ...] = ()
    keywords: str = "traffic_keywords.json"
    discovery: Discovery = Discovery()
    official_sources: tuple[str, ...] = ()
    gis_sources: tuple[str, ...] = ()
    # A country spanning several time zones: the zone of each source that
    # covers one region ("drivebc-events": "America/Vancouver"). Its events'
    # times are shown there; other events in the city's own `timezone`.
    source_time_zones: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _bbox_is_well_formed(self) -> "City":
        south, west, north, east = self.bbox
        if not (-90 <= south < north <= 90 and -180 <= west < east <= 180):
            raise ValueError(f"{self.id}: bbox must be south, west, north, east in WGS 84")
        lon, lat = self.map.center
        if not self.covers(lat, lon):
            raise ValueError(f"{self.id}: the map centre lies outside the bbox")
        for area_south, area_west, area_north, area_east in self.gazetteer_areas:
            if not (
                south <= area_south < area_north <= north and west <= area_west < area_east <= east
            ):
                raise ValueError(f"{self.id}: each gazetteer area must lie inside the bbox")
        for zone in (self.timezone, *self.source_time_zones.values()):
            try:
                ZoneInfo(zone)
            except (KeyError, ValueError) as error:
                raise ValueError(f"{self.id}: unknown timezone {zone!r}") from error
        return self

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def covers(self, latitude: float, longitude: float) -> bool:
        """Whether a point lies in the area REI covers for the city."""
        south, west, north, east = self.bbox
        return south <= latitude <= north and west <= longitude <= east


@lru_cache(maxsize=1)
def load_cities() -> dict[str, City]:
    """Every configured city, by id: the default city first, then the rest by id."""
    cities: dict[str, City] = {}
    paths = sorted(DATA_DIR.glob("*.json"), key=lambda path: (path.stem != DEFAULT_CITY_ID, path.stem))
    for path in paths:
        city = City.model_validate(json.loads(path.read_text(encoding="utf-8")))
        if city.id != path.stem:
            raise ValueError(f"{path.name}: the file is named for a different city ({city.id})")
        cities[city.id] = city
    if DEFAULT_CITY_ID not in cities:
        raise ValueError(f"The default city {DEFAULT_CITY_ID!r} is not configured")
    countries: dict[str, str] = {}
    for city in cities.values():
        if city.level == "country":
            if city.country in countries:
                raise ValueError(
                    f"{city.id}: {countries[city.country]} is already the country entry for {city.country}"
                )
            countries[city.country] = city.id
    return cities


def country_entry(city: City) -> City | None:
    """The country entry a city lies within (Toronto: Canada); None for a
    country entry itself or a city whose country has none (Delhi)."""
    if city.level == "country":
        return None
    return next(
        (other for other in load_cities().values() if other.level == "country" and other.country == city.country),
        None,
    )


def cities_within(city: City) -> tuple[City, ...]:
    """The configured cities within a country entry (Canada: Toronto); none for a city."""
    if city.level != "country":
        return ()
    return tuple(
        other for other in load_cities().values() if other.level == "city" and other.country == city.country
    )


def area_of(city: City) -> tuple[City, ...]:
    """What choosing this entry covers: a city alone, or a country entry and its cities."""
    return (city, *cities_within(city))


def get_city(city_id: str | None) -> City:
    """The city with this id; the default city when none is given."""
    cities = load_cities()
    key = city_id or DEFAULT_CITY_ID
    if key not in cities:
        raise KeyError(f"No city is configured with id {key!r}")
    return cities[key]


def default_city() -> City:
    return get_city(DEFAULT_CITY_ID)


__all__ = [
    "City",
    "DEFAULT_CITY_ID",
    "Discovery",
    "MapView",
    "area_of",
    "cities_within",
    "country_entry",
    "default_city",
    "get_city",
    "load_cities",
]
