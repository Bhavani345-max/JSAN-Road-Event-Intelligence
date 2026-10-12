"""Rule-based detection of road/traffic articles.

No AI is involved: an article is scored against a configurable keyword list
(config/traffic_keywords.json). The result is a candidate for human review,
never a confirmed road event.
"""

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from packages.cities import City
from packages.event_schema import EventType
from packages.source_models import RawSourceRecord
from services.geo_resolution import PlaceResolver

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config" / "traffic_keywords.json"


# The place label that opens a news article, before the first colon:
# "Hyderabad:", "HYDERABAD:", "Jayashankar Bhupalpally:", "Nalgonda, :".
# Only capitalised words qualify, so an ordinary opening sentence that happens
# to contain a colon ("Officials in Hyderabad said: …") is not a dateline.
_DATELINE_WORD = r"[A-Z][A-Za-z./-]*"
_DATELINE = re.compile(rf"\s*((?:{_DATELINE_WORD},?\s+){{0,5}}{_DATELINE_WORD}),?\s*:")


def extract_dateline(body: str | None) -> str | None:
    """The dateline at the very start of an article body, or None if it has none."""
    match = _DATELINE.match(body or "")
    return match.group(1) if match else None


class ArticleRelevance(StrEnum):
    RELEVANT_TRAFFIC_ARTICLE = "RELEVANT_TRAFFIC_ARTICLE"
    NOT_RELEVANT = "NOT_RELEVANT"
    # A structured source states the event itself (an official feed).
    SOURCE_PROVIDED_EVENT = "SOURCE_PROVIDED_EVENT"
    # A road block the source draws shorter than the minimum length
    # (packages/source_models/road_block.py): kept as evidence, not an event.
    BELOW_MINIMUM_LENGTH = "BELOW_MINIMUM_LENGTH"


@dataclass(frozen=True)
class ClassificationResult:
    label: ArticleRelevance
    score: float
    matched_keywords: list[str]
    # Suggested from the strongest typed keyword; None when unclear.
    event_type: EventType | None
    # Set only when the article is within the configured location scope.
    city: str | None
    classifier_version: str

    @property
    def is_relevant(self) -> bool:
        return self.label in (
            ArticleRelevance.RELEVANT_TRAFFIC_ARTICLE,
            ArticleRelevance.SOURCE_PROVIDED_EVENT,
        )

    @property
    def method(self) -> str:
        return (
            "source_provided"
            if self.classifier_version == "source-provided"
            else "keyword_rules"
        )


@dataclass(frozen=True)
class _Rule:
    label: str
    regex: re.Pattern[str]
    weight: float
    event_type: EventType | None
    # Rules in the same group are counted once.
    group: str
    # The rule names what the event is (a marathon, a VIP visit, an accident)
    # rather than the measure on the road (a diversion, a closure). Its type
    # wins over measure types. It never makes an article relevant by itself.
    names_event: bool
    # Longer rules are applied first so "traffic diversion" is not also
    # counted as "traffic" and "diversion".
    specificity: int


def _term_regex(term: str) -> re.Pattern[str]:
    words = [re.escape(word) for word in term.split()]
    return re.compile(r"\b" + r"\s+".join(words) + r"s?\b", re.IGNORECASE)


def _city_regex(city: str) -> re.Pattern[str]:
    """A city's name, except as part of a road's: "Mumbai Highway" is in Hyderabad."""
    words = [re.escape(word) for word in city.split()]
    return re.compile(
        r"\b" + r"\s+".join(words) + r"\b(?!\s+(?:highway|road|rd|expressway|bypass|route|line))",
        re.IGNORECASE,
    )


# Kinds of named place whose name alone puts an article in Hyderabad. A
# hospital or a road may share its name with one in another city; a locality,
# ward or junction written as a name is taken to be the Hyderabad one.
_SCOPE_PLACE_KINDS = ("area", "ward", "junction", "flyover")


class KeywordClassifier:
    def __init__(
        self,
        config: dict,
        place_resolver: PlaceResolver | None = None,
        city: City | None = None,
    ) -> None:
        self.version: str = config["version"]
        # When given, a known locality of the city named in the headline puts
        # the article in scope even if the city itself is not written.
        self._resolver = place_resolver
        # The city the scope is for. Without one, the rules file's own scope
        # (the first city, Hyderabad) applies.
        self.city = city
        self.threshold: float = config["threshold"]
        self.max_supporting_score: float = config.get("max_supporting_score", 1)
        # When set, at least one matched rule must weigh this much: general
        # traffic words cannot add up to a road event without a clear signal.
        self.strong_signal_weight: float | None = config.get("strong_signal_weight")
        self.fields: list[str] = config["fields"]
        scope_terms = list(city.scope_terms) if city else config["scope"]["terms"]
        self.scope_city: str = city.name if city else config["scope"]["city"]
        self._scope_terms = [_term_regex(term) for term in scope_terms]
        # The shared list of cities whose news crowds others out, plus the
        # city's own list, never including the city itself.
        other_cities = set(config["scope"].get("other_cities", []))
        if city:
            other_cities |= set(city.other_cities)
        other_cities -= {term.lower() for term in scope_terms} | set(scope_terms)
        self._other_cities = [
            _city_regex(name)
            for name in sorted(other_cities)
            if name.lower() not in {term.lower() for term in scope_terms}
        ]
        self._excluded = [_term_regex(phrase) for phrase in config.get("exclude_phrases", [])]
        self._rules = sorted(
            (self._build_rule(entry) for entry in config["keywords"]),
            key=lambda rule: rule.specificity,
            reverse=True,
        )

    @classmethod
    def from_file(
        cls,
        path: Path | str = DEFAULT_CONFIG_PATH,
        place_resolver: PlaceResolver | None = None,
        city: City | None = None,
    ) -> "KeywordClassifier":
        with open(path, encoding="utf-8") as file:
            return cls(json.load(file), place_resolver, city)

    @classmethod
    def for_city(
        cls, city: City, place_resolver: PlaceResolver | None = None
    ) -> "KeywordClassifier":
        """The classifier for a configured city: its rules file and its scope."""
        return cls.from_file(DEFAULT_CONFIG_PATH.parent / city.keywords, place_resolver, city)

    @staticmethod
    def _build_rule(entry: dict) -> _Rule:
        event_type = EventType(entry["event_type"]) if entry.get("event_type") else None
        if "pattern" in entry:
            return _Rule(
                label=entry.get("label", entry["pattern"]),
                regex=re.compile(entry["pattern"], re.IGNORECASE),
                weight=entry["weight"],
                event_type=event_type,
                group=entry.get("group", entry.get("label", entry["pattern"])),
                names_event=entry.get("names_event", False),
                # Patterns span several words; treat them as the most specific.
                specificity=1000,
            )
        return _Rule(
            label=entry["term"],
            regex=_term_regex(entry["term"]),
            weight=entry["weight"],
            event_type=event_type,
            group=entry.get("group", entry["term"]),
            names_event=entry.get("names_event", False),
            specificity=len(entry["term"]),
        )

    def classify(self, record: RawSourceRecord) -> ClassificationResult:
        text = " . ".join(
            value for field in self.fields if (value := getattr(record, field, None))
        )
        for excluded in self._excluded:
            text = excluded.sub(" ", text)

        matched: list[_Rule] = []
        for rule in self._rules:
            # Blank out what a rule matched so shorter rules cannot recount it.
            text, count = rule.regex.subn(" ", text)
            if count:
                matched.append(rule)

        score = self._score(matched)
        city = self.scope_city if self._in_scope(record) else None
        has_strong_signal = self.strong_signal_weight is None or any(
            rule.weight >= self.strong_signal_weight for rule in matched
        )
        relevant = score >= self.threshold and has_strong_signal and city is not None
        return ClassificationResult(
            label=(
                ArticleRelevance.RELEVANT_TRAFFIC_ARTICLE
                if relevant
                else ArticleRelevance.NOT_RELEVANT
            ),
            score=score,
            matched_keywords=[rule.label for rule in matched],
            event_type=self._suggest_event_type(matched),
            city=city,
            classifier_version=self.version,
        )

    def _score(self, matched: list[_Rule]) -> float:
        heaviest_per_group: dict[str, float] = {}
        for rule in matched:
            heaviest_per_group[rule.group] = max(
                rule.weight, heaviest_per_group.get(rule.group, 0)
            )
        weights = heaviest_per_group.values()
        main = sum(weight for weight in weights if weight > 1)
        supporting = sum(weight for weight in weights if weight <= 1)
        return main + min(supporting, self.max_supporting_score)

    def names_scope_city(self, text: str | None) -> bool:
        """Whether the text names the city this classifier is for (or one of its scope terms)."""
        return bool(text) and any(term.search(text) for term in self._scope_terms)

    def names_other_city(self, text: str | None) -> bool:
        """Whether the text names one of the other cities whose news is kept out."""
        return bool(text) and any(city.search(text) for city in self._other_cities)

    def _in_scope(self, record: RawSourceRecord) -> bool:
        """Whether the publisher or the text places the article in the scope city.

        Evidence, any of: the publisher's tags, the headline, the summary, or
        the dateline that opens the article body ("Hyderabad: The police…").
        Some publishers (Deccan Chronicle) give the place only in the dateline.
        The rest of the body is deliberately not searched: a passing mention of
        the city further down does not make an article about it.
        """
        dateline = extract_dateline(record.content_text) or ""
        haystack = " . ".join([*record.categories, record.title, record.summary or "", dateline])
        named_in_city = any(term.search(haystack) for term in self._scope_terms)
        # "Traffic diversions in Bengaluru" is about Bengaluru, whatever else
        # the summary mentions.
        if any(city.search(record.title) for city in self._other_cities) and not any(
            term.search(record.title) for term in self._scope_terms
        ):
            return False
        if named_in_city:
            return True
        # "Khajaguda junction restrictions": a known Hyderabad place in the
        # headline, and no other city named anywhere up front.
        if self._resolver is None or any(city.search(haystack) for city in self._other_cities):
            return False
        return any(
            place.kind in _SCOPE_PLACE_KINDS and place.has_position
            for place in self._resolver.find_in(record.title, "title")
        )

    @staticmethod
    def _suggest_event_type(matched: list[_Rule]) -> EventType | None:
        typed = [rule for rule in matched if rule.event_type]
        if not typed:
            return None
        # What the event is (a marathon) beats what is done on the road (a
        # diversion): "Traffic diversions for the marathon" is a marathon.
        naming = [rule for rule in typed if rule.names_event]
        if naming:
            typed = naming
        top_weight = max(rule.weight for rule in typed)
        candidates = {rule.event_type for rule in typed if rule.weight == top_weight}
        if len(candidates) > 1:
            # Road works are the reason for a diversion or closure; the measure
            # on the road is the event.
            candidates.discard(EventType.ROAD_CONSTRUCTION)
        if len(candidates) > 1:
            # "Public event" is the general kind: a VIP visit, a parade or a
            # match named alongside a meeting says more.
            candidates.discard(EventType.SPECIAL_EVENT)
        # Two equally strong but different suggestions: leave it to the reviewer.
        return candidates.pop() if len(candidates) == 1 else None
