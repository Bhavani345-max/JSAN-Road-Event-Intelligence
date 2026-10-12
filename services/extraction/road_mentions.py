"""Finds road names that an article states verbatim.

This is pattern matching on the source text, not GIS resolution: the result is
an unverified mention for a reviewer to check. Nothing is inferred — if the
text does not name a road, no road is returned.
"""

import re

# A proper-noun word: capitalised, or an all-caps/number token such as "RTC" or "65".
_NAME_WORD = r"(?:[A-Z][A-Za-z0-9'’.]*|[0-9]+)"
_NAME = rf"{_NAME_WORD}(?:[ -]{_NAME_WORD}){{0,3}}"

# Suffixes that are part of a road's name only when capitalised ("Necklace Road"),
# and ones that also name a place in lower case ("Khajaguda junction").
_CAPITALISED_SUFFIXES = r"Road|Roads|Marg|Highway|Expressway|Bridge|Circle|Chowrasta"
_ANY_CASE_SUFFIXES = r"[Jj]unction|[Ff]lyover|[Uu]nderpass|X [Rr]oads?|[Cc]ross [Rr]oads?"

_NAMED_ROAD = re.compile(rf"\b({_NAME}) ({_CAPITALISED_SUFFIXES}|{_ANY_CASE_SUFFIXES})\b")
_ROAD_NUMBER = re.compile(r"\b(NH|SH)[- ]?(\d{1,3}[A-Z]?)\b")
_ABBREVIATION = re.compile(r"\b(ORR|PVNR Expressway)\b")

# Capitalised words that start a sentence or describe a road rather than name it.
_NOT_A_NAME = {
    "a", "an", "the", "this", "that", "these", "those", "new", "old", "main", "major",
    "busy", "key", "arterial", "service", "link", "every", "each", "several", "many",
    "some", "all", "both", "another", "other", "proposed", "damaged", "flooded",
    "closed", "hyderabad", "telangana", "city", "state", "national", "internal",
    "inner", "outer", "ring", "radial", "elevated", "steel", "traffic", "on", "at",
    "in", "near", "from", "to", "and", "of", "for", "with", "after", "as",
}

MAX_MENTIONS = 3


def _clean_name(name: str) -> str | None:
    """Drop leading non-name words; None if nothing that looks like a name is left."""
    words = name.split(" ")
    while words and re.sub(r"['’]s$|[:.,]+$", "", words[0].lower()) in _NOT_A_NAME:
        words.pop(0)
    if not words or all(word.isdigit() for word in words):
        return None
    return " ".join(words)


# Long enough to exclude the small words ("at", "for", "with") that headline
# styles treat inconsistently.
_LONG_WORD = re.compile(r"[A-Za-z]{5,}")


def _is_headline_case(text: str) -> bool:
    """Whether the text Is Written Like This, as some publishers style headlines.

    True when every longer word is capitalised. Ordinary sentences, even ones
    full of place names, still contain a lower-case verb or noun.
    """
    words = _LONG_WORD.findall(text)
    return len(words) >= 4 and all(word[0].isupper() for word in words)


def find_road_mentions(*texts: str | None) -> list[str]:
    """Road names stated in the given texts, in order of first appearance."""
    mentions: list[str] = []

    def add(mention: str) -> None:
        if mention.lower() not in (existing.lower() for existing in mentions):
            mentions.append(mention)

    for text in texts:
        if not text:
            continue
        found: list[tuple[int, str]] = []
        # Named roads are recognised by their capital letters, which mean
        # nothing in a headline where every word is capitalised.
        for match in () if _is_headline_case(text) else _NAMED_ROAD.finditer(text):
            name = _clean_name(match.group(1))
            if name:
                found.append((match.start(), f"{name} {match.group(2)}"))
        for match in _ROAD_NUMBER.finditer(text):
            found.append((match.start(), f"{match.group(1)}-{match.group(2)}"))
        for match in _ABBREVIATION.finditer(text):
            found.append((match.start(), match.group(1)))
        for _, mention in sorted(found):
            add(mention)

    return mentions[:MAX_MENTIONS]
