"""City configuration: everything about a city that the pipeline must not hard-code.

Each city is one JSON file in `data/`. Adding a city means adding a file and
registering its sources; the ingestion framework, detection, location and
console read what they need from here.

A city file states:

- `id`, `name`, `country` (ISO 3166-1 alpha-2), `region`, `timezone` (IANA),
  `language` (BCP 47 primary subtag);
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


class City(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9-]{1,40}$")
    name: str
    # How the covered area is called in messages: "Greater Hyderabad".
    area_name: str | None = None
    country: str = Field(min_length=2, max_length=2)
    region: str | None = None
    timezone: str
    language: str = "en"
    # south, west, north, east
    bbox: tuple[float, float, float, float]
    map: MapView
    scope_terms: tuple[str, ...] = Field(min_length=1)
    other_cities: tuple[str, ...] = ()
    gazetteer: str | None = None
    keywords: str = "traffic_keywords.json"
    discovery: Discovery = Discovery()
    official_sources: tuple[str, ...] = ()
    gis_sources: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _bbox_is_well_formed(self) -> "City":
        south, west, north, east = self.bbox
        if not (-90 <= south < north <= 90 and -180 <= west < east <= 180):
            raise ValueError(f"{self.id}: bbox must be south, west, north, east in WGS 84")
        lon, lat = self.map.center
        if not self.covers(lat, lon):
            raise ValueError(f"{self.id}: the map centre lies outside the bbox")
        try:
            ZoneInfo(self.timezone)
        except (KeyError, ValueError) as error:
            raise ValueError(f"{self.id}: unknown timezone {self.timezone!r}") from error
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
    return cities


def get_city(city_id: str | None) -> City:
    """The city with this id; the default city when none is given."""
    cities = load_cities()
    key = city_id or DEFAULT_CITY_ID
    if key not in cities:
        raise KeyError(f"No city is configured with id {key!r}")
    return cities[key]


def default_city() -> City:
    return get_city(DEFAULT_CITY_ID)


__all__ = ["City", "DEFAULT_CITY_ID", "Discovery", "MapView", "default_city", "get_city", "load_cities"]
