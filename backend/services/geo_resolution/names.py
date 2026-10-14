"""Normalising place names so that an article's wording and a map's wording meet.

"Khajaguda junction", "Khajaguda Jn" and "KHAJAGUDA JUNCTION" are the same
place; so are "RTC X Roads" and "RTC Cross Road".
"""

import re

_WORD = re.compile(r"[A-Za-z0-9]+")

# Abbreviations and spelling variants, applied word by word.
_VARIANTS = {
    "jn": "junction",
    "jct": "junction",
    "jnc": "junction",
    "rd": "road",
    "roads": "road",
    "cross": "x",
    "ps": "police station",
    "stn": "station",
    "rly": "railway",
    "twp": "township",
}


def name_tokens(text: str) -> list[tuple[str, int]]:
    """The normalised words of `text`, each with the position it started at.

    A possessive "'s" is dropped: "Gachibowli's" reads as "gachibowli".
    """
    tokens: list[tuple[str, int]] = []
    for match in _WORD.finditer(text):
        word = match.group().lower()
        if word == "s" and match.start() > 0 and text[match.start() - 1] in "'’":
            continue
        for part in _VARIANTS.get(word, word).split():
            tokens.append((part, match.start()))
    return tokens


def normalise_name(name: str) -> str:
    return " ".join(token for token, _ in name_tokens(name))


# Words a place name ends in that are written joined to the word before as
# often as apart: "Dilsukh Nagar" and "Dilsukhnagar", "Basheer Bagh" and
# "Basheerbagh", "Lakdi-ka-pul" and "Lakdikapul".
_JOINABLE_ENDINGS = (
    "nagar", "bagh", "pet", "peta", "pally", "palli", "palle", "guda", "gudem",
    "puram", "pur", "pura", "abad", "gunj", "bund", "pul", "pool", "cheruvu", "kunta",
    "konda", "tanda", "thanda", "bazar", "bazaar", "bowli", "pahad", "khana",
)  # fmt: skip


def spelling_variants(key: str) -> list[str]:
    """Other normalised spellings the same name is commonly written in.

    A two- or three-word name ending in a joinable word is also known joined
    ("lakdi ka pul" → "lakdikapul"); a single word ending in one is also known
    split at it ("dilsukhnagar" → "dilsukh nagar"). Nothing else is varied.
    """
    words = key.split()
    if 2 <= len(words) <= 3 and words[-1] in _JOINABLE_ENDINGS:
        return ["".join(words)]
    if len(words) == 1:
        word = words[0]
        for ending in sorted(_JOINABLE_ENDINGS, key=len, reverse=True):
            stem = word[: -len(ending)]
            if word.endswith(ending) and len(stem) >= 3:
                return [f"{stem} {ending}"]
    return []
