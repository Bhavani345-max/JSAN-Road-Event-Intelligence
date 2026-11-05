"""British National Grid (OSGB36, EPSG:27700) positions to WGS 84 longitude and latitude (5 November 2026).

National Highways' planned roadworks (and the Scottish Road Works Register's
shapes) give positions on the British National Grid: a transverse Mercator
projection of the Airy 1830 ellipsoid (central meridian 2° W, scale
0.9996012717 on it, true origin 49° N, false origin 400 km west and 100 km
north of it), on the OSGB36 datum. Two steps take a grid position to WGS 84,
as the Ordnance Survey describes them in "A Guide to Coordinate Systems in
Great Britain" (v3.6, 2020; sections 6.2 and 6.6, annexes B, C and D):

1. the inverse projection, with the Ordnance Survey's own formulae (annex C.2),
   to OSGB36 latitude and longitude; within Great Britain its error is far
   below a millimetre;
2. the datum change: OSGB36 latitude and longitude to Earth-centred cartesian
   coordinates on Airy 1830 at height 0 (annex B.1), the Ordnance Survey's
   seven-parameter Helmert transformation (equation 3, section 6.2, the
   Position Vector convention) with the parameters of its table 4 (section
   6.6, WGS 84 to OSGB36) with every sign reversed, as section 6.2 says to do
   for the opposite direction, and back to latitude and longitude on the
   WGS 84 ellipsoid (annex B.2).

**Accuracy: a few metres.** OSGB36 was fixed by triangulation and is not a
uniform datum, so one Helmert transformation for all of Britain leaves errors
of "up to 3 m (95%) in plan" (section 6.2; table 4's own note: "up to 3.5
metres (95%)"). The Ordnance Survey's exact transformation is the OSTN15 grid,
which REI does not have. A few metres is well within what a works point on a
motorway map needs; REI never presents it as survey-grade.

tests/unit/test_uk_lu_sources_2026_11_05.py checks each step against the
guide's worked examples: the inverse projection of annex C.2 (E 651409.903,
N 313177.270 -> 52°39′27.2531″ N, 1°43′4.5177″ E) to within a millimetre, the
cartesian conversions of annex B both ways, the Helmert transformation of
annex D (ETRS89 X 3790644.900, Y -110149.210, Z 5111482.970 -> OSGB36
3790269.549, -110038.064, 5111050.261) to within a millimetre and reversed to
within 2 cm, and the whole conversion of annex D's grid position (E 422297.792,
N 412878.741) back to the WGS 84 position it came from (53°36′43.1653″ N,
1°39′51.9920″ W, annex B.1) to within 10 cm. Pure Python: REI adds no
projection library (as for twd97.py).
"""

import math

# Airy 1830 (OSGB36)
_AIRY_A = 6_377_563.396
_AIRY_B = 6_356_256.909
_AIRY_E2 = (_AIRY_A**2 - _AIRY_B**2) / _AIRY_A**2
# WGS 84
_WGS84_A = 6_378_137.0
_WGS84_F = 1 / 298.257223563
_WGS84_E2 = _WGS84_F * (2 - _WGS84_F)
# The National Grid projection (annex A)
SCALE = 0.9996012717
TRUE_ORIGIN_LATITUDE = 49.0
TRUE_ORIGIN_LONGITUDE = -2.0
FALSE_EASTING = 400_000.0
FALSE_NORTHING = -100_000.0

_PHI0 = math.radians(TRUE_ORIGIN_LATITUDE)
_LAMBDA0 = math.radians(TRUE_ORIGIN_LONGITUDE)
_N = (_AIRY_A - _AIRY_B) / (_AIRY_A + _AIRY_B)

# WGS 84 (ETRS89) to OSGB36, as the Ordnance Survey publishes it (table 4,
# section 6.6): translations in metres, scale in parts per million, rotations
# in seconds of arc.
HELMERT_FROM_WGS84 = {
    "tx": -446.448,
    "ty": 125.157,
    "tz": -542.060,
    "s_ppm": 20.4894,
    "rx": -0.1502,
    "ry": -0.2470,
    "rz": -0.8421,
}
# OSGB36 to WGS 84: the same parameters with every sign reversed (section 6.2).
HELMERT_TO_WGS84 = {name: -value for name, value in HELMERT_FROM_WGS84.items()}
# The grid's extent (metres): a value outside is not a National Grid position.
_EASTING_RANGE = (0.0, 700_000.0)
_NORTHING_RANGE = (0.0, 1_300_000.0)
# Decimal places kept in degrees: 1e-6° is about 0.1 m, below the transform's accuracy.
_PLACES = 6


def _meridional_arc(phi: float) -> float:
    """M (equation C3): the distance along the meridian from the true origin's latitude to `phi`, scaled."""
    n = _N
    d, s = phi - _PHI0, phi + _PHI0
    return (
        _AIRY_B
        * SCALE
        * (
            (1 + n + 5 / 4 * n**2 + 5 / 4 * n**3) * d
            - (3 * n + 3 * n**2 + 21 / 8 * n**3) * math.sin(d) * math.cos(s)
            + (15 / 8 * n**2 + 15 / 8 * n**3) * math.sin(2 * d) * math.cos(2 * s)
            - 35 / 24 * n**3 * math.sin(3 * d) * math.cos(3 * s)
        )
    )


def grid_to_osgb36(easting: float, northing: float) -> tuple[float, float]:
    """OSGB36 (latitude, longitude) in radians of a National Grid position
    (the Ordnance Survey's inverse projection, annex C.2)."""
    a_f0 = _AIRY_A * SCALE
    phi = (northing - FALSE_NORTHING) / a_f0 + _PHI0
    arc = _meridional_arc(phi)
    for _ in range(100):
        if abs(northing - FALSE_NORTHING - arc) < 0.00001:  # 0.01 mm
            break
        phi += (northing - FALSE_NORTHING - arc) / a_f0
        arc = _meridional_arc(phi)
    sin_phi = math.sin(phi)
    nu = a_f0 / math.sqrt(1 - _AIRY_E2 * sin_phi**2)
    rho = a_f0 * (1 - _AIRY_E2) / (1 - _AIRY_E2 * sin_phi**2) ** 1.5
    eta2 = nu / rho - 1
    tan_phi, sec_phi = math.tan(phi), 1 / math.cos(phi)
    t2 = tan_phi**2
    vii = tan_phi / (2 * rho * nu)
    viii = tan_phi / (24 * rho * nu**3) * (5 + 3 * t2 + eta2 - 9 * t2 * eta2)
    ix = tan_phi / (720 * rho * nu**5) * (61 + 90 * t2 + 45 * t2**2)
    x = sec_phi / nu
    xi = sec_phi / (6 * nu**3) * (nu / rho + 2 * t2)
    xii = sec_phi / (120 * nu**5) * (5 + 28 * t2 + 24 * t2**2)
    xiia = sec_phi / (5040 * nu**7) * (61 + 662 * t2 + 1320 * t2**2 + 720 * t2**3)
    de = easting - FALSE_EASTING
    latitude = phi - vii * de**2 + viii * de**4 - ix * de**6
    longitude = _LAMBDA0 + x * de - xi * de**3 + xii * de**5 - xiia * de**7
    return latitude, longitude


def to_cartesian(latitude: float, longitude: float, height: float, *, a: float, e2: float) -> tuple[float, float, float]:
    """Earth-centred cartesian coordinates (metres) of a position on an ellipsoid (annex B.1)."""
    sin_phi = math.sin(latitude)
    nu = a / math.sqrt(1 - e2 * sin_phi**2)
    return (
        (nu + height) * math.cos(latitude) * math.cos(longitude),
        (nu + height) * math.cos(latitude) * math.sin(longitude),
        ((1 - e2) * nu + height) * sin_phi,
    )


def from_cartesian(x: float, y: float, z: float, *, a: float, e2: float) -> tuple[float, float, float]:
    """(latitude, longitude) in radians and height in metres of cartesian coordinates (annex B.2)."""
    longitude = math.atan2(y, x)
    p = math.hypot(x, y)
    latitude = math.atan2(z, p * (1 - e2))
    for _ in range(100):
        nu = a / math.sqrt(1 - e2 * math.sin(latitude) ** 2)
        following = math.atan2(z + e2 * nu * math.sin(latitude), p)
        if abs(following - latitude) < 1e-12:
            latitude = following
            break
        latitude = following
    nu = a / math.sqrt(1 - e2 * math.sin(latitude) ** 2)
    return latitude, longitude, p / math.cos(latitude) - nu


def helmert(x: float, y: float, z: float, parameters: dict[str, float]) -> tuple[float, float, float]:
    """A seven-parameter Helmert transformation as the Ordnance Survey writes it
    (equation 3, section 6.2: the Position Vector convention, small rotations)."""
    seconds = math.pi / (180 * 3600)
    s = parameters["s_ppm"] * 1e-6
    rx, ry, rz = (parameters[name] * seconds for name in ("rx", "ry", "rz"))
    return (
        parameters["tx"] + (1 + s) * x - rz * y + ry * z,
        parameters["ty"] + rz * x + (1 + s) * y - rx * z,
        parameters["tz"] - ry * x + rx * y + (1 + s) * z,
    )


def to_lon_lat(easting: float, northing: float) -> tuple[float, float]:
    """The WGS 84 (longitude, latitude) in degrees of a National Grid position (accurate to a few metres)."""
    latitude, longitude = grid_to_osgb36(easting, northing)
    cartesian = to_cartesian(latitude, longitude, 0.0, a=_AIRY_A, e2=_AIRY_E2)
    latitude, longitude, _ = from_cartesian(*helmert(*cartesian, HELMERT_TO_WGS84), a=_WGS84_A, e2=_WGS84_E2)
    return round(math.degrees(longitude), _PLACES), round(math.degrees(latitude), _PLACES)


def grid_position(easting, northing) -> tuple[float, float] | None:
    """A grid position read from a feed's values, or None when it is not one.

    Text or numbers; empty, unreadable or out-of-range values (and 0, 0, a
    missing value rather than the false origin in the sea off Scilly) give
    None: no position is guessed.
    """
    try:
        x, y = float(easting), float(northing)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(x) and math.isfinite(y)) or (x, y) == (0.0, 0.0):
        return None
    if not (_EASTING_RANGE[0] <= x <= _EASTING_RANGE[1] and _NORTHING_RANGE[0] <= y <= _NORTHING_RANGE[1]):
        return None
    return x, y


def point(easting, northing) -> dict | None:
    """A GeoJSON Point in WGS 84 longitude and latitude, or None when the values are not a grid position."""
    position = grid_position(easting, northing)
    if position is None:
        return None
    return {"type": "Point", "coordinates": list(to_lon_lat(*position))}
