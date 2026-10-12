"""Places an event on the map by the names its source states (decision 0021).

Chosen by scoring candidate methods against an answer key of 49 real events
(docs/placement-evaluation-2026-10-09.md). Each name is looked up in turn:

1. The city's OpenStreetMap place list:
   - a same-name place qualified by an area the article names
     ("Holy Trinity Church Road" in an article about Bolarum is at
     "Holy Trinity Church, Bolarum", not at another Holy Trinity Church);
   - the exact name;
   - the name with junction words swapped or added ("Indira Gandhi Rotary"
     is OSM's "Indira Gandhi Statue"; "Old PS Saifabad" is "Old PS Saifabad Jn")
     or with a road or structure word dropped;
   - the longest known name inside it.
   A road or junction found only as a whole locality is a weak match.
2. Google Maps through Serper (/places) when OSM has nothing or only a weak
   match. An answer is used only inside the city and when its name or
   address carries the name's own distinctive words (not the city's name).

Then the places are checked against each other: one more than `outlier_km`
from the article's other places is dropped, or swapped for a same-name
alternative nearer them; a weak match stays only with another place within
`weak_support_km`. When nothing places the event, Google Maps' wider search
(/maps) is tried as a last resort. The event sits at the first place by role
(closed, affected, start of stretch, venue, end of stretch, near), a spot
before a locality, then the order the source names them; never at a
diversion or alternative route.

Every position is a named place's: an OpenStreetMap feature or a Google Maps
place, recorded with its reference. Nothing is computed between places.
"""

import json
import math
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from statistics import median

from .google_maps import GoogleMapsLookup
from .resolver import PlaceMatch, PlaceResolver

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config" / "placement.json"
GOOGLE = "google"
GOOGLE_REFERENCE = "Google Maps (Serper.dev)"


@dataclass(frozen=True)
class PlacementConfig:
    version: str
    junction_words: tuple[str, ...]
    structure_words: tuple[str, ...]
    specific_endings: tuple[str, ...]
    extend_words: tuple[str, ...]
    generic_tokens: frozenset[str]
    organisations: frozenset[str]
    role_priority: tuple[str, ...]
    route_roles: tuple[str, ...]
    outlier_km: float
    weak_support_km: float
    within_km: float

    @classmethod
    def from_file(cls, path: Path | str = DEFAULT_CONFIG_PATH) -> "PlacementConfig":
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
        return cls(
            version=data["version"],
            junction_words=tuple(data["junction_words"]),
            structure_words=tuple(data["structure_words"]),
            specific_endings=tuple(data["specific_endings"]),
            extend_words=tuple(data["extend_words"]),
            generic_tokens=frozenset(data["generic_tokens"]),
            organisations=frozenset(data["organisations"]),
            role_priority=tuple(data["role_priority"]),
            route_roles=tuple(data["route_roles"]),
            outlier_km=float(data["outlier_km"]),
            weak_support_km=float(data["weak_support_km"]),
            within_km=float(data["within_km"]),
        )


@lru_cache(maxsize=1)
def default_config() -> PlacementConfig:
    return PlacementConfig.from_file()


@dataclass(frozen=True)
class Mention:
    """A name the source states, with what it is to the event (None: not said)."""

    name: str
    role: str | None = None
    found_in: str | None = None


@dataclass
class Placed:
    """A mention placed at a named place."""

    mention: Mention
    order: int
    name: str
    kind: str
    latitude: float
    longitude: float
    reference: str
    # qualified, exact, variant, inside, google, google_maps
    how: str
    weak: bool = False
    alternatives: list["Placed"] = field(default_factory=list)

    @property
    def point(self) -> tuple[float, float]:
        return (self.latitude, self.longitude)

    @property
    def precision(self) -> str:
        if self.kind in ("junction", "flyover", "landmark", GOOGLE):
            return "place"
        return "road" if self.kind == "road" else "area"


@dataclass
class Placement:
    best: Placed | None
    placed: list[Placed]
    unplaced: list[Mention]
    # The locality the headline or summary names, when the event sits at a spot within it.
    within: str | None = None


def _km(a: tuple[float, float], b: tuple[float, float]) -> float:
    p = math.pi / 180
    h = (
        math.sin((b[0] - a[0]) * p / 2) ** 2
        + math.cos(a[0] * p) * math.cos(b[0] * p) * math.sin((b[1] - a[1]) * p / 2) ** 2
    )
    return 12742 * math.asin(math.sqrt(h))


def _key(text: str) -> str:
    return " ".join(re.sub(r"[\W_]+", " ", text.casefold()).split())


class Placer:
    def __init__(
        self,
        resolver: PlaceResolver,
        *,
        city_name: str,
        scope_terms: tuple[str, ...] = (),
        bbox: tuple[float, float, float, float] | None = None,
        google: GoogleMapsLookup | None = None,
        config: PlacementConfig | None = None,
    ) -> None:
        self.resolver = resolver
        self.city_name = city_name
        self.google = google
        self.config = config or default_config()
        self.bbox = bbox or getattr(resolver, "bbox", None)
        self._city_words = set(_key(" ".join([city_name, *scope_terms])).split())

    @classmethod
    def for_city(cls, resolver: PlaceResolver, city, google: GoogleMapsLookup | None = None) -> "Placer":
        return cls(
            resolver,
            city_name=city.name if city else "Hyderabad",
            scope_terms=tuple(city.scope_terms) if city else (),
            bbox=tuple(city.bbox) if city else None,
            google=google,
        )

    # --- names -----------------------------------------------------------------------

    def is_organisation(self, name: str) -> bool:
        return _key(name) in self.config.organisations

    def _specific(self, name: str) -> bool:
        base = _key(name)
        endings = self.config.junction_words + self.config.structure_words + self.config.specific_endings
        return any(base.endswith(" " + word) for word in endings)

    def variants(self, name: str) -> list[str]:
        base = _key(name)
        out = [base]
        endings = sorted(self.config.junction_words + self.config.structure_words, key=len, reverse=True)
        for word in endings:
            if base.endswith(" " + word):
                stem = base[: -len(word) - 1].strip()
                if stem:
                    out.append(stem)
                    out += [f"{stem} {other}" for other in self.config.junction_words]
                break
        else:
            out += [f"{base} {word}" for word in self.config.junction_words]
        return list(dict.fromkeys(out))

    def _tokens(self, name: str) -> list[str]:
        return [
            token
            for token in _key(name).split()
            if token not in self.config.generic_tokens and len(token) > 2 and token not in self._city_words
        ]

    # --- candidates ----------------------------------------------------------------------

    def _from_match(self, mention: Mention, order: int, match: PlaceMatch, how: str) -> Placed:
        return Placed(
            mention=mention,
            order=order,
            name=match.name,
            kind=match.kind,
            latitude=match.latitude,
            longitude=match.longitude,
            reference=f"OpenStreetMap {match.osm_ref}" if match.osm_ref else "OpenStreetMap",
            how=how,
        )

    def osm_candidates(self, mention: Mention, order: int, text: str) -> list[Placed]:
        found: list[Placed] = []
        seen: set[str] = set()
        where = mention.found_in or "body"

        def add(placed: Placed) -> None:
            if placed.reference not in seen:
                seen.add(placed.reference)
                found.append(placed)

        for rank, variant in enumerate(self.variants(mention.name)):
            for match, qualifier in self.resolver.qualified(variant, found_in=where):
                if f" {_key(qualifier)} " in text:
                    add(self._from_match(mention, order, match, "qualified"))
            match = self.resolver.lookup(variant, found_in=where)
            if match is not None and match.has_position:
                add(self._from_match(mention, order, match, "exact" if rank == 0 else "variant"))
        if not found:
            inside = [m for m in self.resolver.find_in(mention.name, where, require_capital=False) if m.has_position]
            if inside:
                # A spot before a locality, then the longer name.
                best = max(inside, key=lambda m: (m.kind not in ("area", "ward"), len(m.name)))
                add(self._from_match(mention, order, best, "inside"))
        rank_of = {"qualified": 0, "exact": 1, "variant": 2, "inside": 3}
        found.sort(key=lambda placed: rank_of[placed.how])
        specific = self._specific(mention.name)
        for placed in found:
            placed.weak = placed.how in ("variant", "inside") and placed.kind in ("area", "ward") and specific
        return found

    def _inside(self, point: tuple[float, float]) -> bool:
        if self.bbox is None:
            return True
        south, west, north, east = self.bbox
        return south <= point[0] <= north and west <= point[1] <= east

    def google_candidate(
        self, mention: Mention, order: int, hint: str | None, *, wide: bool = False
    ) -> Placed | None:
        if self.google is None:
            return None
        tokens = self._tokens(mention.name)
        if not tokens:
            return None
        query = ", ".join(part for part in (mention.name, hint, self.city_name) if part)
        if wide:
            south, west, north, east = self.bbox or (0, 0, 0, 0)
            answers = self.google.maps(query, ((south + north) / 2, (west + east) / 2))
        else:
            answers = self.google.places(query)
        for answer in (answers or [])[:3]:
            if answer.get("latitude") is None or answer.get("longitude") is None:
                continue
            point = (float(answer["latitude"]), float(answer["longitude"]))
            if not self._inside(point):
                continue
            said = f" {_key(str(answer.get('title') or '') + ' ' + str(answer.get('address') or ''))} "
            hits = [token for token in tokens if f" {token} " in said]
            if len(hits) < max(1, math.ceil(len(tokens) / 2)):
                continue
            cid = answer.get("cid")
            return Placed(
                mention=mention,
                order=order,
                name=str(answer.get("title") or mention.name),
                kind=GOOGLE,
                latitude=point[0],
                longitude=point[1],
                reference=f"{GOOGLE_REFERENCE}{' place ' + str(cid) if cid else ''}",
                how="google_maps" if wide else "google",
            )
        return None

    # --- the article's own names (articles without an AI reading) ------------------------------

    def whole_mentions(self, text: str | None, found_in: str) -> list[Mention]:
        """Places named in the text, as whole names.

        A match inside a longer proper name is skipped ("City Hospital" in
        "Lake City Hospital"); a match followed by a structure word or, outside
        a headline Written Like This, by more capitalised words is extended
        ("Hitech City railway station", "Ramnagar Gundu").
        """
        from services.extraction.road_mentions import _is_headline_case

        if not text:
            return []
        headline = _is_headline_case(text)
        out: list[Mention] = []
        position = 0
        for match in self.resolver.find_in(text, found_in):
            start = text.find(match.mention, position)
            if start < 0:
                start = text.find(match.mention)
            if start < 0:
                continue
            position = start + len(match.mention)
            before = text[:start].rstrip()
            words_before = before.split()
            previous = words_before[-1] if words_before else ""
            # A capitalised word just before the match that does not start a
            # sentence makes the match part of a longer name.
            sentence_start = len(words_before) <= 1 or words_before[-2].endswith((".", "!", "?", ":"))
            if (
                not headline
                and previous
                and previous[0].isupper()
                and not sentence_start
                and not previous.endswith(("'s", "’s", ":", ".", ",", "-", "–", "/", ")"))
                and previous.lower() not in ("the", "at", "in", "near", "of", "on", "from", "to")
            ):
                continue
            name = match.mention
            rest = text[start + len(match.mention):]
            lowered = rest.lower()
            for word in sorted(self.config.extend_words, key=len, reverse=True):
                end = len(word) + 1
                if lowered.startswith(" " + word) and (len(lowered) == end or not lowered[end].isalnum()):
                    name += rest[:end]
                    break
            else:
                more = None if headline else re.match(r"((?: [A-Z][A-Za-z]+){1,2})", rest)
                if more:
                    name += more.group(1)
            out.append(Mention(name=name, role=None, found_in=found_in))
        return out

    # --- placing ---------------------------------------------------------------------------

    def place(
        self,
        mentions: list[Mention],
        *,
        title: str | None,
        summary: str | None = None,
        body: str | None = None,
    ) -> Placement:
        text = f" {_key(' . '.join(t for t in (title, summary, body) if t))} "
        anchors: list[tuple[float, float]] = []
        hint = None
        hint_place = None
        for found in self.resolver.find_in(title, "title") + self.resolver.find_in(summary, "summary"):
            if found.kind in ("area", "ward") and _key(found.name) not in self._city_words:
                hint = hint or found.name
                if found.has_position:
                    anchors.append((found.latitude, found.longitude))
                    hint_place = hint_place or found
        routes = self.config.route_roles
        resolved: list[Placed] = []
        unplaced: list[Mention] = []
        # Names neither OpenStreetMap nor Google's place search could find (or
        # found only as an unconfirmed locality): the last resort may try them.
        not_found: list[Mention] = []
        for order, mention in enumerate(mentions):
            if self.is_organisation(mention.name):
                continue
            candidates = self.osm_candidates(mention, order, text)
            choice = candidates[0] if candidates else None
            if (choice is None or choice.weak) and mention.role not in routes:
                google = self.google_candidate(mention, order, hint)
                if google is not None:
                    choice = google
            if choice is None:
                unplaced.append(mention)
                not_found.append(mention)
                continue
            choice.alternatives = [c for c in candidates if c is not choice]
            resolved.append(choice)

        # A spot far from the article's other places is another place of the same
        # name. Localities are not tested: an article may name several far apart.
        kept: list[Placed] = []
        for placed in resolved:
            others = anchors + [
                p.point for p in resolved if p is not placed and p.mention.role not in routes
            ]
            others = [point for point in others if point != placed.point]
            if placed.kind in ("area", "ward") or len(others) < 2:
                kept.append(placed)
                continue
            centre = (median(p[0] for p in others), median(p[1] for p in others))
            if _km(placed.point, centre) <= self.config.outlier_km:
                kept.append(placed)
                continue
            nearer = next(
                (a for a in placed.alternatives if _km(a.point, centre) <= self.config.outlier_km), None
            )
            if nearer is not None:
                kept.append(nearer)
            else:
                unplaced.append(placed.mention)
        resolved = kept
        # A road or junction matched only to a whole locality needs another place nearby.
        solid = anchors + [p.point for p in resolved if not p.weak and p.mention.role not in routes]
        kept = []
        for placed in resolved:
            if not placed.weak or any(_km(placed.point, s) <= self.config.weak_support_km for s in solid):
                kept.append(placed)
            else:
                # Found only as a locality nothing confirms: as good as not found.
                unplaced.append(placed.mention)
                not_found.append(placed.mention)
        resolved = kept

        event_places = [p for p in resolved if p.mention.role not in routes]
        if not event_places:
            for order, mention in enumerate(mentions):
                if mention.role in routes or mention not in not_found:
                    continue
                wide = self.google_candidate(mention, order, hint, wide=True)
                if wide is not None:
                    resolved.append(wide)
                    event_places = [wide]
                    unplaced = [m for m in unplaced if m is not mention]
                    break

        priority = self.config.role_priority

        def rank(placed: Placed):
            role = placed.mention.role or "AFFECTED"
            return (
                priority.index(role) if role in priority else len(priority),
                placed.kind in ("area", "ward"),
                placed.order,
            )

        best = min(event_places, key=rank) if event_places else None
        within = None
        if (
            best is not None
            and best.kind not in ("area", "ward")
            and hint_place is not None
            and _km(best.point, (hint_place.latitude, hint_place.longitude)) <= self.config.within_km
        ):
            within = hint_place.name
        return Placement(best=best, placed=resolved, unplaced=unplaced, within=within)
