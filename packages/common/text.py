import html
import re
from html.parser import HTMLParser

_WHITESPACE = re.compile(r"\s+")
_SKIPPED_TAGS = {"script", "style"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIPPED_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIPPED_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)


def normalise_whitespace(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()


def html_to_text(markup: str | None) -> str:
    """Plain text of an HTML fragment, with tags removed and entities decoded."""
    if not markup:
        return ""
    extractor = _TextExtractor()
    extractor.feed(markup)
    extractor.close()
    return normalise_whitespace(html.unescape(" ".join(extractor.parts)))


def truncate(text: str, limit: int) -> str:
    """Cut `text` to at most `limit` characters, on a word boundary."""
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:.") + "…"
