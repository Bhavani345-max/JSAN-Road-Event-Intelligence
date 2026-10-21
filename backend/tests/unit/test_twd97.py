"""TWD97 / TM2 zone 121 grid to longitude and latitude (connectors/official/twd97.py).

Checked against published coordinates of the same points on the grid and in
longitude and latitude (read 21 October 2026):

- first-order satellite control points N001 七星山 (Qixingshan, Beitou,
  Taipei), N364 劍潭山 (Jiantanshan, Zhongshan, Taipei) and N324 紅淡山
  (Hongdanshan, Keelung): the control-point list with columns 點號, 點名,
  行政區, WGS84緯度, WGS84經度, TWD97橫座標, TWD97縱座標 reproduced on the
  OSGeo wiki, https://wiki.osgeo.org/wiki/Taiwan_datums/Test_points;
- the class II satellite control point 頂山 (Dingshan, S567), TWD97[2010]:
  120°19′15.34385″ E, 23°00′17.89564″ N and TM2 E 180388.275, N 2544994.802,
  in 「座標系統轉換與格式換算之研究」, Ministry of National Defense
  (https://www.mnd.gov.tw/NewUpload/201804/P52-70座標系統轉換與格式換算之研究_132529.pdf),
  pp. 60-63, from the National Land Surveying and Mapping Center's results;
- PROJ's own projection of 120°51′58.2″ E, 24°10′54.2″ N with the EPSG:3826
  parameters, quoted on https://wiki.osgeo.org/wiki/Taiwan_datums.

Each must agree within 1 m (REI's requirement); they agree within 1 cm.
"""

import math

import pytest

from connectors.official import twd97


def _dms(degrees: int, minutes: int, seconds: float) -> float:
    return degrees + minutes / 60 + seconds / 3600


def _metres_apart(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((phi2 - phi1) / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6_371_008.8 * math.asin(math.sqrt(h))


# name, easting, northing, longitude, latitude
REFERENCE_POINTS = [
    ("N001 七星山 (Taipei)", 305787.783, 2784799.355, 121.55344419, 25.17069939),
    ("N364 劍潭山 (Taipei)", 303391.398, 2775216.428, 121.52929869, 25.08427325),
    ("N324 紅淡山 (Keelung)", 325828.298, 2779155.412, 121.75193272, 25.11887233),
    ("S567 頂山 (southern Taiwan)", 180388.275, 2544994.802, _dms(120, 19, 15.34385), _dms(23, 0, 17.89564)),
    ("PROJ example (central Taiwan)", 236402.76293, 2675155.08596, _dms(120, 51, 58.2), _dms(24, 10, 54.2)),
]


@pytest.mark.parametrize("name, easting, northing, longitude, latitude", REFERENCE_POINTS, ids=[p[0] for p in REFERENCE_POINTS])
def test_published_points_are_found_within_a_metre(name, easting, northing, longitude, latitude):
    found_lon, found_lat = twd97.to_lon_lat(easting, northing)
    assert _metres_apart(found_lon, found_lat, longitude, latitude) < 1.0
    # In fact within a centimetre (the output keeps 7 decimal places, about 1 cm).
    assert _metres_apart(found_lon, found_lat, longitude, latitude) < 0.02


def test_the_central_meridian_and_the_equator_are_where_the_grid_says():
    assert twd97.to_lon_lat(250_000.0, 0.0) == (121.0, 0.0)
    longitude, _ = twd97.to_lon_lat(250_000.0, 2_770_000.0)
    assert longitude == 121.0


def test_values_that_are_not_a_grid_position_give_no_point():
    for easting, northing in (("", ""), (None, None), ("abc", "2770000"), (121.5, 25.0), ("nan", "nan"), (309050.6, 25.04)):
        assert twd97.point(easting, northing) is None
    assert twd97.point("309050.617", "2770535.957") == {"type": "Point", "coordinates": list(twd97.to_lon_lat(309050.617, 2770535.957))}


def test_a_shape_is_converted_whole_and_its_rings_stay_closed():
    ring = [[301394.357, 2769272.52], [301890.805, 2769412.224], [302272.646, 2769507.359], [301394.357, 2769272.52]]
    area = twd97.geometry("MultiPolygon", [[ring]])
    converted = area["coordinates"][0][0]
    assert area["type"] == "MultiPolygon" and converted[0] == converted[-1] and len(converted) == 4
    assert all(121.4 < lon < 121.7 and 24.9 < lat < 25.3 for lon, lat in converted)
    lines = twd97.geometry("MultiLineString", [[[308455.837, 2769935.321], [308575.897, 2769986.585]]])
    assert lines["type"] == "MultiLineString" and len(lines["coordinates"][0]) == 2
    # One position that is not on the grid: no shape at all, rather than part of one.
    assert twd97.geometry("MultiLineString", [[[308455.837, 2769935.321], [0, 0]]]) is None
    assert twd97.geometry("GeometryCollection", []) is None and twd97.geometry("MultiPolygon", []) is None
