"""Scores ways of placing events on the map against the answer key (gold.py).

    python tools/placement_eval/placement_eval.py PROD          # the app's placer
    python tools/placement_eval/placement_eval.py S1 S6 S12 PROD

PROD is the app's own placer (services/geo_resolution/placement.py); the
other strategies are the rounds of docs/placement-evaluation-2026-10-09.md.
Google Maps answers are cached (apps/api/.data/placement_eval_google_cache.json
and, for PROD, the app's own cache), so re-running costs nothing; new
queries are counted. Reads the events of the database configured in .env and
writes nothing to it.
"""

import json
import math
import re
import sys
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "apps" / "api"), str(HERE)]

import httpx  # noqa: E402
from sqlalchemy import select  # noqa: E402

import gold  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.database import create_db_engine, create_session_factory  # noqa: E402
from app.models import Event, SourceArtifact  # noqa: E402
from app.services.reprocess_service import ai_reading_of, record_from_artifact  # noqa: E402
from packages.cities import load_cities  # noqa: E402
from services.ai_reading import normalise  # noqa: E402
from services.extraction import KeywordClassifier  # noqa: E402
from services.extraction.ai_event import is_ai_road_event  # noqa: E402
from services.extraction.road_mentions import find_road_mentions  # noqa: E402
from services.geo_resolution import resolver_for  # noqa: E402
from services.ingestion import event_for_record  # noqa: E402
from packages.common.time import utc_now  # noqa: E402


def km(a, b):
    p = math.pi / 180
    h = math.sin((b[0] - a[0]) * p / 2) ** 2 + math.cos(a[0] * p) * math.cos(b[0] * p) * math.sin((b[1] - a[1]) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


# --- loading ------------------------------------------------------------------------------

settings = get_settings()
factory = create_session_factory(create_db_engine(settings.database_url))
CITIES = {city.name: city for city in load_cities().values()}
RESOLVERS = {name: resolver_for(city) for name, city in CITIES.items()}
CLASSIFIERS = {name: KeywordClassifier.for_city(city, RESOLVERS[name]) for name, city in CITIES.items()}
GAZETTEERS = {
    name: json.load(open(ROOT / "services" / "geo_resolution" / "data" / city.gazetteer, encoding="utf-8"))["places"]
    for name, city in CITIES.items()
    if city.gazetteer
}


def load_cases():
    cases = []
    with factory() as session:
        rows = session.scalars(select(Event).where(Event.merged_into.is_(None))).unique()
        for event in rows:
            method = (event.detection or {}).get("method")
            if method not in ("keyword_rules", "ai_reading") or event.status == "REJECTED":
                continue
            artifact = session.get(SourceArtifact, event.source_artifact_id)
            record = record_from_artifact(artifact)
            cases.append(
                {
                    "title": event.title,
                    "city": event.city,
                    "record": record,
                    "ai": ai_reading_of(artifact),
                    "stored_point": (event.geometry or {}).get("coordinates") if event.geometry else None,
                }
            )
    return sorted(cases, key=lambda case: case["title"])


# --- Google Maps through Serper, cached -----------------------------------------------------------

CACHE_PATH = ROOT / "apps" / "api" / ".data" / "placement_eval_google_cache.json"
CACHE = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}
NEW_QUERIES = [0]
_KEY = re.search(r"^SERPER_API_KEY=(.+)$", (ROOT / ".env").read_text(encoding="utf-8"), re.M).group(1).strip()


def google(query: str) -> list[dict]:
    if query not in CACHE:
        data = httpx.post(
            "https://google.serper.dev/places", headers={"X-API-KEY": _KEY}, json={"q": query, "gl": "in"}, timeout=60
        ).json()
        CACHE[query] = data.get("places") or []
        NEW_QUERIES[0] += 1
        CACHE_PATH.write_text(json.dumps(CACHE, indent=1, ensure_ascii=False), encoding="utf-8")
    return CACHE[query]


# --- names ----------------------------------------------------------------------------------

JUNCTION_WORDS = ["junction", "jn", "x road", "x roads", "cross road", "cross roads", "crossroads", "circle", "rotary", "chowrasta", "statue", "crossing"]
STRUCTURE_WORDS = ["road", "rd", "main road", "underpass", "rub", "railway underpass", "flyover", "bridge", "stretch", "lane"]
GENERIC = set("road rd main the a of to near junction jn x cross roads circle rotary statue flyover underpass rub railway lane street colony nagar area stretch".split())


def key_of(text: str) -> str:
    return normalise(text).strip()


def variants(name: str) -> list[str]:
    """The name, with junction words swapped and road or structure words dropped."""
    base = key_of(name)
    out = [base]
    words = JUNCTION_WORDS + STRUCTURE_WORDS
    for word in sorted(words, key=len, reverse=True):
        if base.endswith(" " + word):
            stem = base[: -len(word) - 1].strip()
            if stem:
                out.append(stem)
                out += [f"{stem} {other}" for other in JUNCTION_WORDS]
            break
    else:
        # "Old PS Saifabad" is the junction OSM calls "Old PS Saifabad Jn".
        out += [f"{base} {word}" for word in JUNCTION_WORDS]
    return list(dict.fromkeys(out))


ORGANISATIONS = {
    "mmrda", "mumbai metropolitan region development authority", "ghmc", "greater hyderabad municipal corporation",
    "hmwssb", "hmda", "hydraa", "cmc", "cyberabad municipal corporation", "nhai", "bbmp", "gba", "bmc",
    "brihanmumbai municipal corporation", "msrdc", "mmrcl", "bmrcl", "bda", "bwssb", "tgsrtc", "bmtc", "best",
}


def is_organisation(name: str) -> bool:
    return key_of(name) in ORGANISATIONS


def specific(name: str) -> bool:
    """Whether the name says more than a locality: a road, junction, structure, colony or a longer name."""
    base = key_of(name)
    return any(base.endswith(" " + w) for w in JUNCTION_WORDS + STRUCTURE_WORDS + ["colony", "nagar", "gundu", "station", "market"])


def significant_tokens(name: str) -> list[str]:
    return [token for token in key_of(name).split() if token not in GENERIC and len(token) > 2]


# --- candidates ----------------------------------------------------------------------------------


class Ctx:
    def __init__(self, case):
        self.case = case
        self.city = case["city"]
        self.resolver = RESOLVERS[self.city]
        record = case["record"]
        self.text = normalise(" . ".join(t for t in (record.title, record.summary or "", record.content_text or "") if t))
        self.front = normalise(" . ".join(t for t in (record.title, record.summary or "") if t))
        self.bbox = CITIES[self.city].bbox
        self.anchor_points = []
        # Localities the headline or summary names: where the article is.
        for place in self.resolver.find_in(record.title, "title") + self.resolver.find_in(record.summary or "", "summary"):
            if place.kind in ("area", "ward") and place.has_position and key_of(place.name) not in {key_of(self.city)}:
                self.anchor_points.append((place.latitude, place.longitude))

    def inside(self, point) -> bool:
        south, west, north, east = self.bbox
        return south <= point[0] <= north and west <= point[1] <= east

    def anchor(self):
        if not self.anchor_points:
            return None
        return (median(p[0] for p in self.anchor_points), median(p[1] for p in self.anchor_points))


def osm_candidates(name: str, ctx: Ctx, improved: bool) -> list[dict]:
    """OpenStreetMap places for a name, best first."""
    found = []
    if not improved:
        match = ctx.resolver.lookup(name, found_in="x") or max(
            ctx.resolver.find_in(name, "x", require_capital=False), key=lambda m: len(m.name), default=None
        )
        if match and match.has_position:
            found.append({"src": "osm", "how": "lookup", "name": match.name, "kind": match.kind, "pt": (match.latitude, match.longitude)})
        return found
    gaz = GAZETTEERS[ctx.city]
    for rank, variant in enumerate(variants(name)):
        # A same-name place qualified by an area the article names: "Holy Trinity Church, Bolarum".
        for place in gaz:
            if place.get("lat") and place["key"].startswith(variant + " ") and "," in place["name"]:
                qualifier = key_of(place["name"].split(",", 1)[1])
                if qualifier and f" {qualifier} " in ctx.text:
                    found.append({"src": "osm", "how": "qualified", "rank": rank, "name": place["name"], "kind": place["kind"], "pt": (place["lat"], place["lon"])})
        match = ctx.resolver.lookup(variant, found_in="x")
        if match and match.has_position:
            found.append({"src": "osm", "how": "exact" if rank == 0 else "variant", "rank": rank, "name": match.name, "kind": match.kind, "pt": (match.latitude, match.longitude)})
    if not found:
        inside = [m for m in ctx.resolver.find_in(name, "x", require_capital=False) if m.has_position]
        if inside:
            match = max(inside, key=lambda m: len(m.name))
            found.append({"src": "osm", "how": "inside", "rank": 9, "name": match.name, "kind": match.kind, "pt": (match.latitude, match.longitude)})
    order = {"qualified": 0, "exact": 1, "variant": 2, "inside": 3}
    found.sort(key=lambda c: (order[c["how"]], c.get("rank", 0)))
    # A road or junction matched only to a whole locality says less than the article does.
    for c in found:
        c["weak"] = c["how"] in ("variant", "inside") and c["kind"] in ("area", "ward") and specific(name)
    return found


MAPS_FALLBACK = [False]


def google_maps(query: str, centre) -> list[dict]:
    key = "MAPS|" + query
    if key not in CACHE:
        data = httpx.post(
            "https://google.serper.dev/maps", headers={"X-API-KEY": _KEY},
            json={"q": query, "ll": f"@{centre[0]},{centre[1]},12z", "gl": "in"}, timeout=60,
        ).json()
        CACHE[key] = data.get("places") or []
        NEW_QUERIES[0] += 3
        CACHE_PATH.write_text(json.dumps(CACHE, indent=1, ensure_ascii=False), encoding="utf-8")
    return CACHE[key]


def google_candidate(name: str, ctx: Ctx, hint: str | None) -> dict | None:
    query = ", ".join(part for part in (name, hint, ctx.city) if part)
    # The city's own name says nothing about where in the city.
    city_words = set(key_of(" ".join([ctx.city, *CITIES[ctx.city].scope_terms])).split())
    tokens = [token for token in significant_tokens(name) if token not in city_words]
    if not tokens:
        return None
    results = google(query)[:3]
    if not results and MAPS_FALLBACK[0]:
        south, west, north, east = ctx.bbox
        results = google_maps(query, ((south + north) / 2, (west + east) / 2))[:3]
    for result in results:
        if result.get("latitude") is None:
            continue
        point = (result["latitude"], result["longitude"])
        if not ctx.inside(point):
            continue
        said = key_of(f"{result.get('title', '')} {result.get('address', '')}")
        hits = [t for t in tokens if f" {t} " in f" {said} "]
        if not tokens or len(hits) < max(1, math.ceil(len(tokens) / 2)):
            continue
        return {"src": "google", "how": "google", "name": result.get("title"), "kind": "google", "pt": point}
    return None


ROUTE = ("DIVERSION_ROUTE", "ALTERNATE_ROUTE")
PRIORITY = ("CLOSED", "AFFECTED", "STRETCH_FROM", "VENUE", "STRETCH_TO", "NEAR")
KIND_ORDER = ("junction", "flyover", "landmark", "google", "road", "area", "ward")


EXTEND_WORDS = ("railway station", "metro station", "railway underpass", "underpass", "flyover", "junction", "x road", "x roads", "cross roads", "road", "bus stop", "rub", "rob", "circle")
EXTENDED = [False]


def whole_mentions(resolver, field_text: str, field: str) -> list[str]:
    """Places named in a field, as whole names: a match inside a longer proper name is skipped,
    and a match followed by a structure word ("railway station") or more capitalised words is extended."""
    out = []
    from services.extraction.road_mentions import _is_headline_case
    headline_case = _is_headline_case(field_text)
    for match in resolver.find_in(field_text, field):
        start = field_text.find(match.mention)
        if start < 0:
            continue
        before = field_text[:start].rstrip()
        prev = before.split()[-1] if before.split() else ""
        if not headline_case and prev and prev[0].isupper() and not prev.endswith(("'s", "’s", ":", ".", ",", "-", "–", "/")) and prev.lower() not in ("the", "at", "in", "near", "of"):
            # "Lake City Hospital": "City Hospital" is not the place.
            if start > 0 and not before.endswith((".", ":")):
                continue
        name = match.mention
        rest = field_text[start + len(match.mention):]
        low = rest.lower()
        for word in sorted(EXTEND_WORDS, key=len, reverse=True):
            if low.startswith(" " + word) and (len(low) == len(word) + 1 or not low[len(word) + 1].isalnum()):
                name = name + rest[: len(word) + 1]
                break
        else:
            # More capitalised words continue the name, except in a headline Written Like This.
            from services.extraction.road_mentions import _is_headline_case
            more = None if _is_headline_case(field_text) else re.match(r"((?: [A-Z][A-Za-z]+){1,2})", rest)
            if more:
                name = name + more.group(1)
        out.append(name)
    return out


def mentions(case) -> list[tuple[str, str]]:
    """(name, role) the event is placed by: the checked AI reading's, else the keywords' places and roads up front."""
    ai = case["ai"]
    if ai is not None and is_ai_road_event(ai):
        return [(p.name, p.role) for p in ai.places]
    record = case["record"]
    resolver = RESOLVERS[case["city"]]
    if EXTENDED[0]:
        names = whole_mentions(resolver, record.title, "title") + whole_mentions(resolver, record.summary or "", "summary")
    else:
        names = [m.mention for m in resolver.find_places(title=record.title, summary=record.summary) if m.found_in in ("title", "summary")]
    names += find_road_mentions(record.title, record.summary)
    return [(n, "AFFECTED") for n in dict.fromkeys(names)]


LAST_RESORT = [False]


def place_event(case, *, improved: bool, use_google: str | None, outlier_km: float | None, rank_mode: str = "kind", weak_rule: bool = False, orgs: bool = False):
    """The event's point and its drawn places under one strategy."""
    ctx = Ctx(case)
    hint = None
    record = case["record"]
    for place in ctx.resolver.find_in(record.title, "title") + ctx.resolver.find_in(record.summary or "", "summary"):
        if place.kind in ("area", "ward") and key_of(place.name) != key_of(ctx.city):
            hint = place.name
            break
    resolved = []
    for order, (name, role) in enumerate(mentions(case)):
        if orgs and is_organisation(name):
            continue
        osm = osm_candidates(name, ctx, improved)
        weak = bool(osm) and osm[0].get("weak") and weak_rule
        wants_google = use_google in ("first", "consensus") and role not in ROUTE
        wants_google |= use_google == "fallback" and (not osm or weak) and role not in ROUTE
        g = google_candidate(name, ctx, hint) if wants_google else None
        choice = None
        if use_google == "fallback":
            if weak and g:
                choice = g
            elif weak:
                choice = {**osm[0], "unconfirmed": True}
            else:
                choice = osm[0] if osm else g
        elif use_google == "first":
            choice = g or (osm[0] if osm else None)
        elif use_google == "consensus":
            if osm and g:
                choice = osm[0] if km(osm[0]["pt"], g["pt"]) <= 1.0 else None
                if choice is None:
                    anchor = ctx.anchor()
                    choice = min((osm[0], g), key=lambda c: km(c["pt"], anchor)) if anchor else g
            else:
                choice = (osm[0] if osm else None) or g
        else:
            choice = osm[0] if osm else None
            if choice and weak:
                choice = {**choice, "unconfirmed": True}
        if choice:
            resolved.append({"name": name, "role": role, "order": order, **choice, "alts": osm[1:]})
    # Where the article is: its named localities, and places only one way to read.
    if outlier_km and resolved:
        support = list(ctx.anchor_points) + [r["pt"] for r in resolved if r["role"] not in ROUTE]
        if len(support) >= 2:
            centre = (median(p[0] for p in support), median(p[1] for p in support))
            kept = []
            for r in resolved:
                if km(r["pt"], centre) <= outlier_km:
                    kept.append(r)
                    continue
                # A same-name alternative nearer the rest of the article, if there is one.
                alt = next((a for a in r["alts"] if km(a["pt"], centre) <= outlier_km), None)
                if alt:
                    kept.append({**r, **alt})
            resolved = kept
    if weak_rule:
        # A weak match stays only when another place of the article lies within 3 km.
        solid = [r for r in resolved if not r.get("unconfirmed") and r["role"] not in ROUTE] + [{"pt": p} for p in ctx.anchor_points]
        resolved = [r for r in resolved if not r.get("unconfirmed") or any(km(r["pt"], s["pt"]) <= 3 for s in solid)]
    eventish = [r for r in resolved if r["role"] not in ROUTE]
    if not eventish and LAST_RESORT[0]:
        # Nothing places the event: Google Maps' wider search, for the first name it can check.
        MAPS_FALLBACK[0] = True
        for order, (name, role) in enumerate(mentions(case)):
            if role in ROUTE or (orgs and is_organisation(name)):
                continue
            g = google_candidate(name, ctx, hint)
            if g:
                eventish = [{"name": name, "role": role, "order": order, **g}]
                resolved = resolved + eventish
                break
        MAPS_FALLBACK[0] = False
    if not eventish:
        return None, resolved
    def rank(r):
        role = PRIORITY.index(r["role"]) if r["role"] in PRIORITY else len(PRIORITY)
        kind = KIND_ORDER.index(r["kind"]) if r["kind"] in KIND_ORDER else len(KIND_ORDER)
        if rank_mode == "order":
            return (role, r["kind"] in ("area", "ward"), r["order"])
        return (role, kind, r["order"])
    best = min(eventish, key=rank)
    return best["pt"], resolved


def s0(case):
    """As the app does it today."""
    record = case["record"]
    classifier = CLASSIFIERS[case["city"]]
    event = event_for_record(record, classifier.classify(record), RESOLVERS[case["city"]], now=utc_now(), city=CITIES[case["city"]], ai=case["ai"])
    if event is None or event.geometry is None:
        point = case["stored_point"]
        return ((point[1], point[0]) if point else None), []
    lon, lat = event.geometry.coordinates
    places = [
        {"name": l.name, "role": l.role, "pt": (l.geometry.coordinates[1], l.geometry.coordinates[0])}
        for l in event.detection.affected_locations
        if l.geometry is not None and l.geometry.type == "Point"
    ]
    return (lat, lon), places


def prod(case):
    """The app's own placer (services/geo_resolution/placement.py) with the shared Google cache."""
    from services.ingestion import event_for_record as derive
    from services.geo_resolution.google_maps import GoogleMapsLookup
    from services.geo_resolution.placement import Placer
    global _PROD_GOOGLE
    try:
        _PROD_GOOGLE
    except NameError:
        _PROD_GOOGLE = GoogleMapsLookup(_KEY, ROOT / "apps" / "api" / ".data" / "google_places_cache.json", daily_credits=40)
    city = CITIES[case["city"]]
    placer = Placer.for_city(RESOLVERS[case["city"]], city, _PROD_GOOGLE)
    record = case["record"]
    event = derive(record, CLASSIFIERS[case["city"]].classify(record), RESOLVERS[case["city"]], now=utc_now(), city=city, ai=case["ai"], placer=placer)
    if event is None or event.geometry is None:
        return None, []
    lon, lat = event.geometry.coordinates
    places = [{"name": l.name, "role": l.role, "pt": (l.geometry.coordinates[1], l.geometry.coordinates[0])}
              for l in event.detection.affected_locations if l.geometry is not None]
    return (lat, lon), places


def with_flags(extended=False, maps=False, last_resort=False, **kwargs):
    def strategy(case):
        EXTENDED[0], MAPS_FALLBACK[0], LAST_RESORT[0] = extended, maps, last_resort
        return place_event(case, **kwargs)
    return strategy


BASE = dict(improved=True, outlier_km=5, rank_mode="order", weak_rule=True, orgs=True)
STRATEGIES = {
    "S0": ("today's app", s0),
    "S1": ("OSM: name variants + same-name places qualified by the article's area", with_flags(improved=True, use_google=None, outlier_km=None)),
    "S1b": ("S1 + reject places far from the article's other places", with_flags(improved=True, use_google=None, outlier_km=5)),
    "S5": ("S1b, first-named place first, weak matches need support, no agencies", with_flags(use_google=None, **BASE)),
    "S6": ("S5 + Google when OSM has nothing or only a weak match", with_flags(use_google="fallback", **BASE)),
    "S9": ("S6 + whole names in keyword articles", with_flags(extended=True, use_google="fallback", **BASE)),
    "S10": ("S9 + Google /maps when /places finds nothing", with_flags(extended=True, maps=True, use_google="fallback", **BASE)),
    "S12": ("S9 + Google /maps only when nothing else places the event", with_flags(extended=True, last_resort=True, use_google="fallback", **BASE)),
    "PROD": ("the app's placer as built", prod),
    "S8": ("Google first (checked), then OSM; whole names", with_flags(extended=True, use_google="first", **BASE)),
    "S11": ("both; nearer the article's area when they disagree; whole names", with_flags(extended=True, use_google="consensus", **BASE)),
}


def grade(point, targets):
    if targets == "NONE":
        return ("RIGHTLY_NONE" if point is None else "SHOULD_BE_NONE"), None
    if point is None:
        return "MISSED", None
    best = min(((km(point, gold.T[t][:2]), gold.T[t][2]) for t in targets), key=lambda x: x[0] - x[1])
    distance, exact = best
    if distance <= exact:
        return "EXACT", distance
    if distance <= max(gold.CLOSE_KM, exact + 0.5):
        return "CLOSE", distance
    if distance <= gold.AREA_KM + exact:
        return "AREA", distance
    return "WRONG", distance


def run(names):
    cases = load_cases()
    report = {}
    for name in names:
        label, strategy = STRATEGIES[name]
        tally, score, rows, far_places = {}, 0, [], 0
        for case in cases:
            targets = gold.targets_for(case["title"])
            if targets == "DIFFUSE":
                continue
            point, places = strategy(case)
            verdict, distance = grade(point, targets)
            tally[verdict] = tally.get(verdict, 0) + 1
            score += gold.SCORES[verdict]
            if targets != "NONE":
                centre = gold.T[targets[0]][:2]
                far_places += sum(1 for p in places if p.get("role") not in ROUTE and km(p["pt"], centre) > 5)
            rows.append((verdict, round(distance, 2) if distance is not None else None, case["title"][:70]))
        report[name] = {"label": label, "score": score, "tally": tally, "far_event_places": far_places, "rows": rows}
        print(f"{name:4} score {score:4} | {tally} | far drawn places {far_places} | {label}")
    return report


if __name__ == "__main__":
    names = sys.argv[1:] or list(STRATEGIES)
    report = run(names)
    (ROOT / "apps" / "api" / ".data" / "placement_report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print("new Google queries:", NEW_QUERIES[0])
