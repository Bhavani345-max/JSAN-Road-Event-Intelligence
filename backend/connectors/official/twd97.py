"""TWD97 / TM2 zone 121 (EPSG:3826) grid coordinates to longitude and latitude.

Taiwan's city works feeds (Taipei, New Taipei) give positions on the
national grid: a transverse Mercator projection of the GRS 80 ellipsoid with
central meridian 121° E, scale 0.9999 on it, false easting 250,000 m and no
false northing (latitude of origin 0°). TWD97 is a realisation of ITRF94,
within about a metre of WGS 84, so the longitude and latitude it gives are
used as WGS 84, as REI's map needs.

The inverse projection uses Krüger's series in the third flattening n, to
fourth order (as given by Karney, "Transverse Mercator with an accuracy of a
few nanometers", Journal of Geodesy 85, 2011). Within Taiwan (at most 1.5°
from the central meridian) its error is far below a millimetre;
tests/unit/test_twd97.py checks it against published control points to
within a few centimetres. Pure Python: REI adds no projection library.
"""

import math

# GRS 80
_A = 6_378_137.0
_F = 1 / 298.257222101
# TWD97 / TM2 zone 121
CENTRAL_MERIDIAN = 121.0
SCALE = 0.9999
FALSE_EASTING = 250_000.0
FALSE_NORTHING = 0.0

_N = _F / (2 - _F)
# The rectifying radius times the scale on the central meridian.
_RADIUS = SCALE * _A / (1 + _N) * (1 + _N**2 / 4 + _N**4 / 64)
# Grid (ξ, η) to the conformal sphere.
_BETA = (
    _N / 2 - 2 * _N**2 / 3 + 37 * _N**3 / 96 - _N**4 / 360,
    _N**2 / 48 + _N**3 / 15 - 437 * _N**4 / 1440,
    17 * _N**3 / 480 - 37 * _N**4 / 840,
    4397 * _N**4 / 161280,
)
# Conformal latitude to geodetic latitude.
_DELTA = (
    2 * _N - 2 * _N**2 / 3 - 2 * _N**3 + 116 * _N**4 / 45,
    7 * _N**2 / 3 - 8 * _N**3 / 5 - 227 * _N**4 / 45,
    56 * _N**3 / 15 - 136 * _N**4 / 35,
    4279 * _N**4 / 630,
)
# Grid positions Taiwan's main island and its near islands can have (metres):
# a value outside is not a TWD97 / TM2 zone 121 position.
_EASTING_RANGE = (100_000.0, 400_000.0)
_NORTHING_RANGE = (2_400_000.0, 2_850_000.0)
# Decimal places kept in degrees: 1e-7° is about 1 cm.
_PLACES = 7


def to_lon_lat(easting: float, northing: float) -> tuple[float, float]:
    """The (longitude, latitude) in degrees of a TWD97 / TM2 zone 121 position."""
    xi = (northing - FALSE_NORTHING) / _RADIUS
    eta = (easting - FALSE_EASTING) / _RADIUS
    xi_prime, eta_prime = xi, eta
    for j, beta in enumerate(_BETA, start=1):
        xi_prime -= beta * math.sin(2 * j * xi) * math.cosh(2 * j * eta)
        eta_prime -= beta * math.cos(2 * j * xi) * math.sinh(2 * j * eta)
    chi = math.asin(math.sin(xi_prime) / math.cosh(eta_prime))
    latitude = chi + sum(delta * math.sin(2 * j * chi) for j, delta in enumerate(_DELTA, start=1))
    longitude = math.radians(CENTRAL_MERIDIAN) + math.atan2(math.sinh(eta_prime), math.cos(xi_prime))
    return round(math.degrees(longitude), _PLACES), round(math.degrees(latitude), _PLACES)


def grid_position(easting, northing) -> tuple[float, float] | None:
    """A grid position read from a feed's values, or None when it is not one.

    Text or numbers; empty, unreadable or out-of-range values give None (no
    position is guessed).
    """
    try:
        x, y = float(easting), float(northing)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(x) and math.isfinite(y)):
        return None
    if not (_EASTING_RANGE[0] <= x <= _EASTING_RANGE[1] and _NORTHING_RANGE[0] <= y <= _NORTHING_RANGE[1]):
        return None
    return x, y


def point(easting, northing) -> dict | None:
    """A GeoJSON Point in longitude and latitude, or None when the values are not a grid position."""
    position = grid_position(easting, northing)
    if position is None:
        return None
    return {"type": "Point", "coordinates": list(to_lon_lat(*position))}


def _convert(coordinates, depth: int):
    """Nested grid positions (depth 0 = one position) in longitude and latitude; None if any is not one."""
    if depth == 0:
        if not isinstance(coordinates, (list, tuple)) or len(coordinates) < 2:
            return None
        position = grid_position(coordinates[0], coordinates[1])
        return list(to_lon_lat(*position)) if position else None
    if not isinstance(coordinates, (list, tuple)) or not coordinates:
        return None
    converted = [_convert(part, depth - 1) for part in coordinates]
    return None if any(part is None for part in converted) else converted


_DEPTH = {"Point": 0, "LineString": 1, "MultiLineString": 2, "Polygon": 2, "MultiPolygon": 3}


def geometry(kind: str, coordinates) -> dict | None:
    """A GeoJSON geometry of this kind in longitude and latitude, from grid coordinates.

    None when the kind is not one REI reads or any position is not a grid
    position: a shape is converted whole or not at all.
    """
    depth = _DEPTH.get(kind)
    if depth is None:
        return None
    converted = _convert(coordinates, depth)
    return {"type": kind, "coordinates": converted} if converted is not None else None
