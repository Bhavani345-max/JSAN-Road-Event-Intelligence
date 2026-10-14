"""Asks a language model what each article reports, and checks the answer.

The prompts, the allowed intents, impacts and place roles live in
config/ai_reading.json, not in code. The model's answer is untrusted text:

- an intent, impact or role it may not use is dropped;
- a place is kept only when the article contains its name word for word;
- a quote (evidence, the period's words, the announcing authority) is kept
  only when the article contains it;
- dates are kept only with words the article contains, and REI's own date
  rules read those words first; the model's dates are used only when the
  rules cannot read them.

Whatever is dropped is listed in the reading's `discarded`, so a reviewer
can see what the model said that the article does not support.
"""

import json
import re
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, tzinfo
from pathlib import Path

from packages.cities import City
from packages.common.time import IST, end_of_day, start_of_day
from packages.event_schema import AiPlace, AiReading, EventType
from services.extraction.stated_period import find_stated_period

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config" / "ai_reading.json"

TRIAGE = "triage"
FULL = "full"

# Longest free-text answers kept, in characters.
_MAX_WHY = 240
_MAX_CAUSE = 160
_MAX_SUMMARY = 400
_MAX_CITY = 80
_MAX_PLACES = 12


@dataclass(frozen=True)
class AiConfig:
    version: str
    # The full reading's own prompt version: a change to it re-reads only the
    # articles read in full, not every headline.
    full_version: str
    triage: dict
    full: dict
    intents: dict[str, str]
    impacts: dict[str, str]
    roles: dict[str, str]
    role_priority: tuple[str, ...]

    @classmethod
    def from_file(cls, path: Path | str = DEFAULT_CONFIG_PATH) -> "AiConfig":
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
        known = {member.value for member in EventType}
        unknown = sorted(set(data["intents"]) - known)
        if unknown:
            raise ValueError(f"{path}: intents REI has no event type for: {', '.join(unknown)}")
        return cls(
            version=data["version"],
            full_version=data["full"].get("version", data["version"]),
            triage=data["triage"],
            full=data["full"],
            intents=data["intents"],
            impacts=data["impacts"],
            roles=data["roles"],
            role_priority=tuple(data["role_priority"]),
        )


@dataclass(frozen=True)
class ArticleText:
    """One article as it is sent to the model and checked afterwards."""

    # Short id used in the prompt ("a1").
    key: str
    artifact_id: str
    title: str
    summary: str | None
    body: str | None
    published_at: datetime | None
    city: City

    def fields(self) -> list[tuple[str, str]]:
        return [
            (name, text)
            for name, text in (("title", self.title), ("summary", self.summary), ("body", self.body))
            if text
        ]

    @property
    def zone(self) -> tzinfo:
        return getattr(self.city, "tz", None) or IST


# --- Checking text against the article ------------------------------------------


def normalise(text: str) -> str:
    """Lower case, accents and punctuation removed, single spaces, padded with spaces.

    Letters of any script are kept, so Kannada or Marathi text is compared too.
    """
    text = unicodedata.normalize("NFKC", text).casefold()
    text = "".join(
        char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)
    )
    return " " + " ".join(re.sub(r"[\W_]+", " ", text).split()) + " "


_ELLIPSIS = re.compile(r"\s*(?:\.\.\.|…)\s*")


def contains(normalised_text: str, phrase: str | None) -> bool:
    """Whether the article (already normalised) contains the phrase word for word.

    A quote the model shortened with "..." counts when each of its parts is there.
    """
    if not phrase:
        return False
    parts = [normalise(part) for part in _ELLIPSIS.split(phrase)]
    parts = [part for part in parts if part.strip()]
    return bool(parts) and all(part in normalised_text for part in parts)


def found_in(article: ArticleText, phrase: str) -> str | None:
    """The first field (title, summary, body) containing the phrase."""
    for name, text in article.fields():
        if contains(normalise(text), phrase):
            return name
    return None


# --- Prompts ----------------------------------------------------------------------


def _clip(text: str | None, limit: int) -> str:
    if not text:
        return ""
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " …"


def _choices(options: dict[str, str]) -> str:
    return "\n".join(f"- {name}: {meaning}" for name, meaning in options.items())


def _published(article: ArticleText) -> str | None:
    if article.published_at is None:
        return None
    return article.published_at.astimezone(article.zone).date().isoformat()


def triage_prompt(config: AiConfig, articles: list[ArticleText], today: date) -> str:
    items = [
        {
            "id": article.key,
            "feed_city": article.city.name,
            "published": _published(article),
            "title": article.title,
            "summary": _clip(article.summary, config.triage["summary_chars"]),
            "opening": _clip(article.body, config.triage["body_chars"]),
        }
        for article in articles
    ]
    return "\n".join(
        [
            f"Today is {today.isoformat()}. Each article came from a news feed covering the city in its feed_city.",
            "",
            "Allowed intents (the kind of road event):",
            _choices(config.intents),
            "",
            "Answer with exactly this JSON shape, one entry for every article id:",
            '{"articles": [{"id": "a1", "road_event": true, "intent": "<allowed intent or null>", "why": "<at most 15 words>"}]}',
            "",
            "Articles:",
            json.dumps(items, ensure_ascii=False, indent=1),
        ]
    )


def full_prompt(config: AiConfig, articles: list[ArticleText], today: date) -> str:
    items = [
        {
            "id": article.key,
            "feed_city": article.city.name,
            "published": _published(article),
            "title": article.title,
            "summary": _clip(article.summary, 1500),
            "text": _clip(article.body, config.full["body_chars"]),
        }
        for article in articles
    ]
    shape = {
        "articles": [
            {
                "id": "a1",
                "road_event": True,
                "why": "<why it is or is not a road event, at most 20 words>",
                "city": "<the city the event is in, as the article names it, or null>",
                "intent": "<allowed intent or null>",
                "impact": "<allowed impact or null>",
                "cause": "<why the road is affected, a few words, or null>",
                "summary": "<one plain sentence: what happens on which road and when>",
                "places": [
                    {
                        "name": "<place or road name copied exactly from the article>",
                        "role": "<allowed role>",
                        "quote": "<the article's words showing this, copied exactly>",
                    }
                ],
                "period": {
                    "quote": "<the article's words stating when, copied exactly>",
                    "start_date": "YYYY-MM-DD or null",
                    "end_date": "YYYY-MM-DD or null",
                    "start_time": "HH:MM or null",
                    "end_time": "HH:MM or null",
                },
                "authority": "<who announced it, copied exactly, or null>",
                "evidence": "<the article's sentence stating the road measure, copied exactly>",
            }
        ]
    }
    return "\n".join(
        [
            f"Today is {today.isoformat()}. Each article came from a news feed covering the city in its feed_city.",
            "",
            "Allowed intents (the kind of road event):",
            _choices(config.intents),
            "",
            "Allowed impacts (what happens on the road):",
            _choices(config.impacts),
            "",
            "Allowed place roles:",
            _choices(config.roles),
            "",
            "Use \"period\": null when the article states no date or time for the road measure.",
            "When an article is not a road event, answer road_event false with why, and null or empty for the rest.",
            "Answer with exactly this JSON shape, one entry for every article id:",
            json.dumps(shape, ensure_ascii=False),
            "",
            "Articles:",
            json.dumps(items, ensure_ascii=False, indent=1),
        ]
    )


# --- Reading the answer -------------------------------------------------------------


def _text(value, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    value = " ".join(value.split())
    if not value or value.lower() in {"null", "none", "n/a", "unknown"}:
        return None
    return value[:limit]


def _flag(value) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in {"true", "yes"}:
        return True
    if isinstance(value, str) and value.strip().lower() in {"false", "no"}:
        return False
    return None


def _entries(answer: dict) -> dict[str, dict]:
    entries = answer.get("articles")
    if not isinstance(entries, list):
        return {}
    return {
        str(entry["id"]): entry
        for entry in entries
        if isinstance(entry, dict) and entry.get("id") is not None
    }


def _intent(config: AiConfig, value, discarded: list[str]) -> EventType | None:
    name = _text(value, 60)
    if name is None:
        return None
    name = name.upper().replace(" ", "_")
    if name in config.intents:
        return EventType(name)
    discarded.append(f"intent {name!r} is not one REI uses")
    return None


def read_triage_answer(
    config: AiConfig, answer: dict, articles: list[ArticleText], *, model: str, now: datetime
) -> dict[str, AiReading]:
    """Readings by artifact id, for the articles the answer covers."""
    entries = _entries(answer)
    readings: dict[str, AiReading] = {}
    for article in articles:
        entry = entries.get(article.key)
        if entry is None:
            continue
        is_road_event = _flag(entry.get("road_event"))
        if is_road_event is None:
            continue
        discarded: list[str] = []
        readings[article.artifact_id] = AiReading(
            model=model,
            prompt_version=config.version,
            read_at=now,
            stage=TRIAGE,
            is_road_event=is_road_event,
            why=_text(entry.get("why"), _MAX_WHY),
            intent=_intent(config, entry.get("intent"), discarded) if is_road_event else None,
            discarded=discarded,
        )
    return readings


def _places(config: AiConfig, value, article: ArticleText, discarded: list[str]) -> list[AiPlace]:
    if not isinstance(value, list):
        return []
    text = normalise(" . ".join(text for _, text in article.fields()))
    places: list[AiPlace] = []
    seen: set[tuple[str, str]] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        name = _text(item.get("name"), 120)
        if name is None:
            continue
        if not contains(text, name):
            discarded.append(f"place {name!r} is not in the article")
            continue
        role = (_text(item.get("role"), 40) or "").upper().replace(" ", "_")
        if role not in config.roles:
            role = "AFFECTED"
        key = (normalise(name), role)
        if key in seen:
            continue
        seen.add(key)
        quote = _text(item.get("quote"), 400)
        if quote is not None and not contains(text, quote):
            discarded.append(f"quote for {name!r} is not in the article")
            quote = None
        places.append(AiPlace(name=name, role=role, found_in=found_in(article, name), quote=quote))
        if len(places) >= _MAX_PLACES:
            break
    return places


def _date(value) -> date | None:
    text = _text(value, 20)
    if text is None:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _time(value) -> time | None:
    text = _text(value, 10)
    if text is None:
        return None
    match = re.fullmatch(r"(\d{1,2})[:.](\d{2})", text)
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    return time(hour, minute) if hour < 24 and minute < 60 else None


@dataclass(frozen=True)
class _Period:
    text: str
    read_by: str
    start: datetime | None
    end: datetime | None


def _period(value, article: ArticleText, discarded: list[str]) -> _Period | None:
    if not isinstance(value, dict):
        return None
    quote = _text(value.get("quote"), 300)
    if quote is None:
        return None
    text = normalise(" . ".join(text for _, text in article.fields()))
    if not contains(text, quote):
        discarded.append(f"period words {quote!r} are not in the article")
        return None
    zone = article.zone
    start_day, end_day = _date(value.get("start_date")), _date(value.get("end_date"))
    # REI's own date rules read the words first.
    rules = find_stated_period(
        title=None, summary=quote, published_at=article.published_at, zone=zone
    )
    if rules is not None:
        one_day = (
            rules.start is not None
            and rules.end is not None
            and rules.start.astimezone(zone).date() == rules.end.astimezone(zone).date()
        )
        if one_day and end_day is None and start_day == rules.start.astimezone(zone).date():
            # "shut on August 31" and still shut: the day it began, no end stated.
            return _Period(text=quote, read_by="rules", start=rules.start, end=None)
        return _Period(text=quote, read_by="rules", start=rules.start, end=rules.end)

    start_at, end_at = _time(value.get("start_time")), _time(value.get("end_time"))
    if start_day is None and end_day is None:
        return None
    published = article.published_at.astimezone(zone).date() if article.published_at else None
    for day in (start_day, end_day):
        if day is not None and published is not None and abs((day - published).days) > 730:
            discarded.append(f"date {day.isoformat()} is far from the publication date")
            return None
    start = (
        datetime.combine(start_day, start_at, tzinfo=zone)
        if start_day and start_at
        else start_of_day(start_day, zone)
        if start_day
        else None
    )
    # A single day with times ("on October 12 from 6 am to 11 am").
    end_on = end_day or (start_day if end_at else None)
    end = (
        datetime.combine(end_on, end_at, tzinfo=zone)
        if end_on and end_at
        else end_of_day(end_on, zone)
        if end_on
        else None
    )
    if start and end and end < start:
        discarded.append("the model's end date is before its start date")
        return None
    return _Period(text=quote, read_by="ai", start=start, end=end)


ScopeCheck = Callable[[ArticleText, AiReading], bool]


def read_full_answer(
    config: AiConfig,
    answer: dict,
    articles: list[ArticleText],
    *,
    model: str,
    now: datetime,
    in_scope: ScopeCheck,
) -> dict[str, AiReading]:
    """Checked readings by artifact id, for the articles the answer covers."""
    entries = _entries(answer)
    readings: dict[str, AiReading] = {}
    for article in articles:
        entry = entries.get(article.key)
        if entry is None:
            continue
        is_road_event = _flag(entry.get("road_event"))
        if is_road_event is None:
            continue
        discarded: list[str] = []
        why = _text(entry.get("why"), _MAX_WHY)
        if not is_road_event:
            readings[article.artifact_id] = AiReading(
                model=model,
                prompt_version=config.full_version,
                read_at=now,
                stage=FULL,
                is_road_event=False,
                why=why,
            )
            continue
        text = normalise(" . ".join(text for _, text in article.fields()))
        impact = (_text(entry.get("impact"), 40) or "").upper().replace(" ", "_") or None
        if impact is not None and impact not in config.impacts:
            discarded.append(f"impact {impact!r} is not one REI uses")
            impact = None
        authority = _text(entry.get("authority"), 160)
        if authority is not None and not contains(text, authority):
            discarded.append(f"authority {authority!r} is not in the article")
            authority = None
        evidence = _text(entry.get("evidence"), 600)
        if evidence is not None and not contains(text, evidence):
            discarded.append("the evidence sentence is not in the article")
            evidence = None
        period = _period(entry.get("period"), article, discarded)
        reading = AiReading(
            model=model,
            prompt_version=config.full_version,
            read_at=now,
            stage=FULL,
            is_road_event=True,
            why=why,
            intent=_intent(config, entry.get("intent"), discarded),
            impact=impact,
            cause=_text(entry.get("cause"), _MAX_CAUSE),
            summary=_text(entry.get("summary"), _MAX_SUMMARY),
            city=_text(entry.get("city"), _MAX_CITY),
            places=_places(config, entry.get("places"), article, discarded),
            period_text=period.text if period else None,
            period_read_by=period.read_by if period else None,
            start_time=period.start if period else None,
            end_time=period.end if period else None,
            authority=authority,
            evidence=evidence,
            discarded=discarded,
        )
        reading.in_scope = in_scope(article, reading)
        readings[article.artifact_id] = reading
    return readings


def batches(items: list, size: int) -> Iterable[list]:
    for start in range(0, len(items), max(1, size)):
        yield items[start : start + size]
