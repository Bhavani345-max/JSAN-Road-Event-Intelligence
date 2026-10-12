"""GeoJSON geometry models (RFC 7946) for event locations.

Coordinates are [longitude, latitude] in WGS 84. These models validate
structure and coordinate ranges only; matching to the road network is the job
of the future GIS Resolution Engine.
"""

import math
from typing import Annotated, Literal, Union

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def _validate_position(value: tuple[float, float]) -> tuple[float, float]:
    longitude, latitude = value
    if not -180 <= longitude <= 180:
        raise ValueError(f"longitude {longitude} is outside [-180, 180]")
    if not -90 <= latitude <= 90:
        raise ValueError(f"latitude {latitude} is outside [-90, 90]")
    return value


Position = Annotated[tuple[float, float], AfterValidator(_validate_position)]


def _validate_ring(ring: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if len(ring) < 4:
        raise ValueError("a polygon ring needs at least 4 positions")
    if ring[0] != ring[-1]:
        raise ValueError("a polygon ring must be closed (first position == last)")
    return ring


Ring = Annotated[list[Position], AfterValidator(_validate_ring)]


class _GeometryBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Point(_GeometryBase):
    type: Literal["Point"]
    coordinates: Position


class LineString(_GeometryBase):
    type: Literal["LineString"]
    coordinates: list[Position] = Field(min_length=2)


class Polygon(_GeometryBase):
    type: Literal["Polygon"]
    coordinates: list[Ring] = Field(min_length=1)


# Multi-part shapes, as official sources publish them: several street
# segments of one disruption (Transport for London), an area in two parts.
class MultiLineString(_GeometryBase):
    type: Literal["MultiLineString"]
    coordinates: list[Annotated[list[Position], Field(min_length=2)]] = Field(min_length=1)


class MultiPolygon(_GeometryBase):
    type: Literal["MultiPolygon"]
    coordinates: list[Annotated[list[Ring], Field(min_length=1)]] = Field(min_length=1)


Geometry = Annotated[
    Union[Point, LineString, Polygon, MultiLineString, MultiPolygon],
    Field(discriminator="type"),
]


_EARTH_RADIUS_M = 6_371_008.8


def distance_m(a: Position | list[float], b: Position | list[float]) -> float:
    """Great-circle distance between two (longitude, latitude) positions, in metres."""
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(h))


def line_length_m(geometry: dict | None) -> float | None:
    """Length of a GeoJSON LineString or MultiLineString in metres; None for any other shape."""
    if not geometry:
        return None
    kind, coordinates = geometry.get("type"), geometry.get("coordinates") or []
    lines = [coordinates] if kind == "LineString" else coordinates if kind == "MultiLineString" else None
    if lines is None:
        return None
    return sum(distance_m(a, b) for line in lines for a, b in zip(line, line[1:]))


def positions_of(geometry: "Point | LineString | Polygon | MultiLineString | MultiPolygon"):
    """Every position of a geometry, flattened."""
    coordinates = geometry.coordinates
    if geometry.type == "Point":
        return [coordinates]
    if geometry.type == "LineString":
        return list(coordinates)
    if geometry.type in ("Polygon", "MultiLineString"):
        return [position for part in coordinates for position in part]
    return [position for polygon in coordinates for ring in polygon for position in ring]
