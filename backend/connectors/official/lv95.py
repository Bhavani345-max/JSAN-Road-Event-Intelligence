"""Swiss LV95 (CH1903+, EPSG:2056) grid coordinates to WGS 84 longitude and latitude.

Some Swiss cantonal feeds (Kanton Schwyz's roadworks, 5 November 2026) give
positions only on the national grid LV95: easting E about 2,600,000 m and
northing N about 1,200,000 m at the old observatory in Bern.

The conversion uses swisstopo's published approximate formulas for the
direct transformation of Swiss projection coordinates to WGS 84 ("Approximate
formulas for the transformation between Swiss projection coordinates and
WGS84", Federal Office of Topography swisstopo, version of December 2016,
section 2; derived by U. Marti, May 1999, after Bolliger 1967), read from
swisstopo's own PDF on 5 November 2026:

    y' = (E - 2,600,000 m) / 1,000,000        x' = (N - 1,200,000 m) / 1,000,000
    λ' = 2.6779094 + 4.728982 y' + 0.791484 y' x' + 0.1306 y' x'² - 0.0436 y'³
    φ' = 16.9023892 + 3.238272 x' - 0.270978 y'² - 0.002528 x'² - 0.0447 y'² x' - 0.0140 x'³
    λ = λ' × 100 / 36,  φ = φ' × 100 / 36   (λ', φ' in units of 10,000"; λ, φ in degrees)

swisstopo states their precision as better than 0.12" in longitude and 0.08"
in latitude everywhere in Switzerland (about 2.5 m), enough to place a road
works site. tests/unit/test_ch_sources_2026_11_05.py checks the formulas
against swisstopo's worked example (E 2,700,000 m, N 1,100,000 m: λ' 3.14297976,
φ' 16.57588564, λ 8° 43' 49.80", φ 46° 02' 38.86"; rigorous reference 8° 43'
49.79", 46° 02' 38.87") and against the Schwyz server's own WGS 84 output for
the same features: on 5 November 2026 the two agreed within 0.7 m at every
position of all 27 works lines. Heights are not converted: REI keeps positions
in two dimensions. Pure Python: REI adds no projection library.
"""

import math

FALSE_EASTING = 2_600_000.0
FALSE_NORTHING = 1_200_000.0
# Grid positions Switzerland and Liechtenstein can have (metres), with a
# margin: a value outside is not an LV95 position.
_EASTING_RANGE = (2_450_000.0, 2_850_000.0)
_NORTHING_RANGE = (1_050_000.0, 1_320_000.0)
# Decimal places kept in degrees: 1e-6° is about 0.1 m, finer than the formulas.
_PLACES = 6


def to_lon_lat(easting: float, northing: float) -> tuple[float, float]:
    """The (longitude, latitude) in degrees of an LV95 position."""
    y = (easting - FALSE_EASTING) / 1_000_000
    x = (northing - FALSE_NORTHING) / 1_000_000
    longitude = 2.6779094 + 4.728982 * y + 0.791484 * y * x + 0.1306 * y * x**2 - 0.0436 * y**3
    latitude = (
        16.9023892
        + 3.238272 * x
        - 0.270978 * y**2
        - 0.002528 * x**2
        - 0.0447 * y**2 * x
        - 0.0140 * x**3
    )
    return round(longitude * 100 / 36, _PLACES), round(latitude * 100 / 36, _PLACES)


def grid_position(easting, northing) -> tuple[float, float] | None:
    """An LV95 position read from a feed's values, or None when it is not one.

    Text or numbers; empty, unreadable or out-of-range values give None (no
    position is guessed).
    """
    try:
        e, n = float(easting), float(northing)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(e) and math.isfinite(n)):
        return None
    if not (_EASTING_RANGE[0] <= e <= _EASTING_RANGE[1] and _NORTHING_RANGE[0] <= n <= _NORTHING_RANGE[1]):
        return None
    return e, n


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
    """A GeoJSON geometry of this kind in longitude and latitude, from LV95 coordinates.

    None when the kind is not one REI reads or any position is not an LV95
    position: a shape is converted whole or not at all.
    """
    depth = _DEPTH.get(kind)
    if depth is None:
        return None
    converted = _convert(coordinates, depth)
    return {"type": kind, "coordinates": converted} if converted is not None else None
