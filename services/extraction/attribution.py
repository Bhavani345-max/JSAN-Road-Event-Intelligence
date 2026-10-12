"""Finds the authority an article attributes a road measure to.

"The Cyberabad Police have issued a traffic advisory…" attributes the measure
to the Cyberabad Police. This is what the *article* says: it is a second-hand
report of an official announcement, not the announcement itself, and is shown
to reviewers as such.
"""

import re

# Canonical name -> how articles write it. Specific names come first so that
# "Cyberabad Traffic Police" is not also counted as "Traffic Police".
_AUTHORITIES: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(pattern, re.IGNORECASE))
    for name, pattern in (
        ("Cyberabad Police", r"\bCyberabad\s+(?:Traffic\s+)?Police\b"),
        ("Hyderabad Police", r"\bHyderabad\s+(?:City\s+)?(?:Traffic\s+)?Police\b"),
        ("Rachakonda Police", r"\bRachakonda\s+(?:Traffic\s+)?Police\b"),
        ("Malkajgiri Police", r"\bMalkajgiri\s+(?:Traffic\s+)?Police\b"),
        # Not "Gachibowli Traffic Police Station", which is a place.
        ("Traffic Police", r"\bTraffic\s+Police\b(?!\s+Station)"),
        ("GHMC", r"\bGHMC\b|\bGreater\s+Hyderabad\s+Municipal\s+Corporation\b"),
        ("Cyberabad Municipal Corporation", r"\bCyberabad\s+Municipal\s+Corporation\b"),
        ("HYDRAA", r"\bHYDRAA\b"),
        ("NHAI", r"\bNHAI\b|\bNational\s+Highways\s+Authority\b"),
        ("HMDA", r"\bHMDA\b"),
        ("HMWSSB", r"\bHMWSSB\b|\bWater\s+Board\b"),
    )
)

# Wording that makes the authority the origin of the measure, in the same sentence.
_ANNOUNCES = re.compile(
    r"\b(?:announc|issu|impos|advis|notif|restrict|divert|clos|urg|request|warn)\w*", re.IGNORECASE
)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

MAX_AUTHORITIES = 3


def find_attributions(*texts: str | None) -> list[str]:
    """Authorities the texts name as announcing a measure, in order of appearance."""
    found: list[str] = []
    for text in texts:
        for sentence in _SENTENCE_END.split(text or ""):
            if not _ANNOUNCES.search(sentence):
                continue
            remaining = sentence
            for name, pattern in _AUTHORITIES:
                remaining, count = pattern.subn(" ", remaining)
                if count and name not in found:
                    found.append(name)
    # "The traffic police" adds nothing once the article has named which force.
    generic = "Traffic Police"
    if any(name != generic and name.endswith(" Police") for name in found):
        found = [name for name in found if name != generic]
    return found[:MAX_AUTHORITIES]
