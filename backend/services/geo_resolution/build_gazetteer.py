"""Builds the Hyderabad gazetteer from OpenStreetMap.

    python -m services.geo_resolution.build_gazetteer [--city london]

Downloads, for the configured city (Hyderabad by default), the named junctions, flyovers, underpasses, roads, landmarks
(stations, hospitals, colleges, places of worship, markets, parks, lakes, the
airport), localities and wards of Greater Hyderabad from the Overpass API and
writes
services/geo_resolution/data/hyderabad_places.json. Run it again to refresh
the data; the application itself never calls OpenStreetMap.

Every located entry is a real OpenStreetMap feature and keeps its OSM id. A
name that does not point to one spot (a long road, or a name shared by places
in different parts of the city) is kept as a known name with no position: an
article that uses it names a Hyderabad place, but cannot be located by it.

Data © OpenStreetMap contributors, Open Database Licence (ODbL).
"""

import argparse
import json
import math
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import httpx

from packages.cities import DEFAULT_CITY_ID, get_city

from .names import normalise_name

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# Tried in order when a server is overloaded.
OVERPASS_URLS = (
    OVERPASS_URL,
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
USER_AGENT = "JSAN-REI/1.0 (road event intelligence PoC)"
OUTPUT_PATH = Path(__file__).parent / "data" / "hyderabad_places.json"

# south, west, north, east: Greater Hyderabad out to the Outer Ring Road.
BBOX = (17.18, 78.15, 17.68, 78.75)

_QUERY = """
[out:json][timeout:170];
(
  nwr["place"~"^(suburb|neighbourhood|quarter|locality|village|town|hamlet|city_block|square)$"]["name"]({bbox});
  relation["boundary"="administrative"]["admin_level"~"^(9|10)$"]["name"]({bbox});
  node["highway"~"^(motorway_junction|traffic_signals)$"]["name"]({bbox});
  nwr["junction"]["name"]({bbox});
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link)$"]["name"]({bbox});
  way["bridge"]["highway"]["name"]({bbox});
  way["tunnel"]["highway"]["name"]({bbox});
  way["man_made"="bridge"]["name"]({bbox});
  nwr["man_made"~"^(embankment|dyke|dam)$"]["name"]({bbox});
  nwr["waterway"="dam"]["name"]({bbox});
  nwr["natural"="water"]["name"]({bbox});
  nwr["leisure"~"^(park|stadium|nature_reserve|sports_centre|garden)$"]["name"]({bbox});
  nwr["railway"~"^(station|halt)$"]["name"]({bbox});
  nwr["public_transport"="station"]["name"]({bbox});
  nwr["amenity"~"^(police|bus_station|hospital|university|college|marketplace|place_of_worship|townhall|courthouse)$"]["name"]({bbox});
  nwr["shop"="mall"]["name"]({bbox});
  nwr["aeroway"="aerodrome"]["name"]({bbox});
  nwr["office"="government"]["name"]({bbox});
  nwr["landuse"~"^(military|industrial)$"]["name"]({bbox});
  nwr["tourism"~"^(attraction|museum|zoo|theme_park)$"]["name"]({bbox});
  nwr["historic"]["name"]({bbox});
);
out center tags;
"""

NAME_TAGS = ("name:en", "name", "alt_name", "short_name", "official_name")

# How far apart (km from their centre) features sharing a name may lie and
# still count as one spot.
MAX_RADIUS_KM = {
    "junction": 0.4,
    "flyover": 1.0,
    "landmark": 0.6,
    "road": 1.5,
    "area": 1.0,
    # A ward is an administrative area; its centre stands for the whole of it.
    "ward": 2.5,
}

# What an event located by each kind of place is located to.
PRECISION = {
    "junction": "place",
    "flyover": "place",
    "landmark": "place",
    "road": "road",
    "area": "area",
    "ward": "area",
}

_ROAD_ENDINGS = ("road", "marg", "highway", "expressway", "street", "lane", "avenue")
_FLYOVER_ENDINGS = ("flyover", "bridge", "underpass", "tunnel", "rob", "rub")
_JUNCTION_ENDINGS = ("junction", "x road", "circle", "chowrasta", "chowk", "square")

# Names that are ordinary words or the whole city: never a location by themselves.
GENERIC_NAMES = {
    "hyderabad", "secunderabad", "cyberabad", "telangana", "india", "greater hyderabad",
    "mumbai", "bombay", "greater mumbai", "brihanmumbai", "maharashtra", "navi mumbai", "thane",
    "bengaluru", "bangalore", "greater bengaluru", "karnataka", "bengaluru urban",
    "park", "colony", "temple", "market", "main road", "service road", "police station",
    "market road", "station road", "temple road", "church road", "school road", "mosque road",
    "hospital road", "masjid road", "bazar road", "bazaar road", "colony road", "new road",
    "old road", "main street", "cross road", "x road", "circle road", "bus stand road",
    "railway station road", "lake road", "tank road", "village road", "park road",
    "bus stop", "bus station", "railway station", "flyover", "underpass", "junction",
    "bridge", "lake", "tank", "school", "hospital", "church", "masjid", "mosque",
    "city", "town", "village", "centre", "center", "phase 1", "phase 2", "phase 3",
    "old city", "new city", "ring road", "link road", "bypass road", "high court",
    "secretariat", "stadium", "garden", "gardens", "enclave", "township", "extension",
    "assembly", "local", "paradise", "hanuman temple", "sri krishna",
    # Kinds of place that many localities have one of.
    "government hospital", "area hospital", "district hospital", "general hospital",
    "primary health centre", "community health centre", "urban health centre",
    "government high school", "government junior college", "government degree college",
    "government college", "degree college", "junior college", "metro station",
    "bus depot", "post office", "community hall", "function hall", "petrol pump",
    "police station", "traffic police station", "traffic police", "ward office",
    "shiva temple", "sai baba temple", "ganesh temple", "ram temple", "rama temple",
    "venkateswara temple", "durga temple", "ayyappa temple", "jama masjid", "eidgah",
    "industrial area", "industrial estate", "military area", "cantonment",
    # Organisations that articles name as actors, not as places.
    "ghmc", "hmwssb", "hmda", "hydraa", "nhai", "tgsrtc", "medicover", "apollo",
}  # fmt: skip


_LANDMARK_KEYS = (
    "natural", "leisure", "railway", "public_transport", "amenity", "tourism", "historic",
    "shop", "aeroway", "office", "landuse", "man_made", "waterway",
)  # fmt: skip


_WARD_PREFIX = re.compile(r"^\s*ward\s*(?:no\.?\s*)?\d+\s*[-:.]?\s*", re.IGNORECASE)


def feature_kind(tags: dict) -> str | None:
    if "place" in tags:
        return "area"
    if tags.get("boundary") == "administrative":
        return "ward"
    if "junction" in tags or tags.get("highway") in ("motorway_junction", "traffic_signals"):
        return "junction"
    if "bridge" in tags or "tunnel" in tags or tags.get("man_made") == "bridge":
        return "flyover"
    if "highway" in tags:
        return "road"
    if any(key in tags for key in _LANDMARK_KEYS):
        return "landmark"
    return None


def kind_preference(name: str) -> tuple[str, ...]:
    """Which kinds of feature a name most plausibly refers to, best first."""
    if name.endswith(_ROAD_ENDINGS):
        return ("road", "flyover")
    if name.endswith(_FLYOVER_ENDINGS):
        return ("flyover", "road")
    if name.endswith(_JUNCTION_ENDINGS):
        return ("junction", "landmark", "area", "ward", "road", "flyover")
    # A locality's own node is preferred to the ward that carries its name.
    return ("area", "ward", "landmark", "junction", "flyover", "road")


def _distance_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat = math.radians((a[0] + b[0]) / 2)
    dx = (a[1] - b[1]) * 111.32 * math.cos(lat)
    dy = (a[0] - b[0]) * 110.57
    return math.hypot(dx, dy)


def _usable_name(name: str) -> bool:
    return (
        len(name) >= 4
        and name not in GENERIC_NAMES
        and not name.replace(" ", "").isdigit()
        # A lone short word is too easily an ordinary word or a person's name.
        and (" " in name or len(name) >= 5)
    )


def build_places(elements: list[dict]) -> tuple[list[dict], Counter]:
    """Reduce raw OSM features to one entry per name that points to one spot."""
    # normalised name -> kind -> [(lat, lon, osm ref, spelling)]
    by_name: dict[str, dict[str, list[tuple[float, float, str, str]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for element in elements:
        tags = element.get("tags", {})
        kind = feature_kind(tags)
        position = element.get("center") or element
        if kind is None or "lat" not in position:
            continue
        ref = f"{element['type']}/{element['id']}"
        spellings = {
            spelling.strip()
            for tag in NAME_TAGS
            for spelling in tags.get(tag, "").split(";")
            if spelling.strip().isascii()
        }
        if kind == "ward":
            # "Ward 131 Quthbullapur" is written "Quthbullapur" in an article.
            spellings = {_WARD_PREFIX.sub("", spelling) for spelling in spellings}
        for spelling in spellings:
            name = normalise_name(spelling)
            if _usable_name(name):
                by_name[name][kind].append((position["lat"], position["lon"], ref, spelling))

    places: list[dict] = []
    skipped: Counter = Counter()
    for name, kinds in sorted(by_name.items()):
        kind = next((kind for kind in kind_preference(name) if kind in kinds), None)
        if kind is None:
            skipped["kind does not fit the name"] += 1
            continue
        features = kinds[kind]
        centre = (
            sum(feature[0] for feature in features) / len(features),
            sum(feature[1] for feature in features) / len(features),
        )
        spelling = Counter(feature[3] for feature in features).most_common(1)[0][0]
        if max(_distance_km(centre, feature[:2]) for feature in features) > MAX_RADIUS_KM[kind]:
            skipped[f"{kind} not one spot"] += 1
            places.append({"name": spelling, "key": name, "kind": kind, "precision": "none"})
            continue
        # A real feature, the one nearest the middle, rather than a made-up centre.
        lat, lon, ref, _ = min(features, key=lambda feature: _distance_km(centre, feature[:2]))
        places.append(
            {
                "name": spelling,
                "key": name,
                "kind": kind,
                "precision": PRECISION[kind],
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "osm": ref,
            }
        )
    return places, skipped


def download(bbox: tuple[float, float, float, float] = BBOX) -> dict:
    """The Overpass response for one area, from the first server that answers.

    The public servers are often overloaded (HTTP 429/504 or a timeout); the
    next one is tried, and the whole list twice, before giving up.
    """
    query = _QUERY.format(bbox=",".join(str(value) for value in bbox))
    errors = []
    for attempt in range(2):
        for url in OVERPASS_URLS:
            try:
                response = httpx.post(
                    url, data={"data": query}, headers={"User-Agent": USER_AGENT}, timeout=240
                )
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as error:
                errors.append(f"{url}: {error}")
                print(f"Overpass failed ({url}): {error}")
        if attempt == 0:
            time.sleep(30)
    raise SystemExit("Every Overpass server failed:\n" + "\n".join(errors))


def download_areas(areas: tuple[tuple[float, float, float, float], ...]) -> dict:
    """One Overpass response covering several areas (each feature once)."""
    elements: dict[tuple[str, int], dict] = {}
    timestamp = None
    for area in areas:
        document = download(area)
        timestamp = document.get("osm3s", {}).get("timestamp_osm_base") or timestamp
        for element in document["elements"]:
            elements[(element["type"], element["id"])] = element
    return {"elements": list(elements.values()), "osm3s": {"timestamp_osm_base": timestamp}}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Hyderabad gazetteer from OpenStreetMap")
    parser.add_argument("--from-file", help="Use a saved Overpass response instead of downloading")
    parser.add_argument("--city", default=DEFAULT_CITY_ID, help="City id from packages/cities/data")
    args = parser.parse_args()

    city = get_city(args.city)
    if not city.gazetteer:
        raise SystemExit(f"{city.id}: the city configuration names no gazetteer file")
    bbox = tuple(city.bbox)
    # A country covers its metro areas only (`gazetteer_areas`), not all of its land.
    areas = city.gazetteer_areas or (bbox,)
    output_path = OUTPUT_PATH.parent / city.gazetteer

    if args.from_file:
        document = json.loads(Path(args.from_file).read_text(encoding="utf-8"))
    else:
        document = download_areas(areas)
    places, skipped = build_places(document["elements"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        {
            "source": "OpenStreetMap via the Overpass API",
            "licence": "© OpenStreetMap contributors, ODbL 1.0",
            "osm_data_timestamp": document.get("osm3s", {}).get("timestamp_osm_base"),
            "city": city.id,
            "bbox_south_west_north_east": bbox,
            **({"areas_south_west_north_east": areas} if city.gazetteer_areas else {}),
            "places": places,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    # One place per line keeps the file readable and its diffs small.
    output_path.write_text(text.replace('},{"name"', '},\n{"name"'), encoding="utf-8")
    located = [place for place in places if "lat" in place]
    print(f"{len(places)} names written to {output_path}, {len(located)} with a position")
    print("located, by kind:", dict(Counter(place["kind"] for place in located)))
    print("without a position:", dict(skipped))


if __name__ == "__main__":
    main()
