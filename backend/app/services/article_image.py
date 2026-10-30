"""The image published with an event's source article, and whether REI may show it.

Decision 0050. Read from the evidence already stored when the API answers:
nothing is fetched, stored or changed. Only the image the publisher itself
published with the article counts: an image in the article's own markup, as
its feed delivered it. Nothing is ever looked up elsewhere (no search engine
copies, no images matched by headline or category).

An image is shown only when the publisher has permitted it (IMAGE_PERMISSIONS)
and the image is on the publisher's own site. Any doubt about permission,
attribution or ownership means it is not shown, and the API says why.
"""

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlsplit

from app.models import Source, SourceArtifact
from app.schemas.event import ArticleImageOut
from packages.common.text import normalise_whitespace


@dataclass(frozen=True)
class ImagePermission:
    """A publisher's permission for REI to show the images published with its articles."""

    # The permission, quoted, with where and when it was read.
    terms: str
    # The credit line the terms require next to the image.
    attribution: str
    # The publisher's own image hosts; an image anywhere else is not shown.
    image_hosts: tuple[str, ...]


# Sources whose publishers permit REI to show their article images, by source id.
#
# Empty since 30 October 2026, when the candidates were checked:
# - Telangana Today: its "Terms & Conditions" page holds no terms, only
#   "© Copyrights 2024 TELANGANA PUBLICATIONS PVT. LTD. All rights reserved."
# - NewsMeter: no terms of use, only a privacy policy; its feed says "NewsMeter"
#   as copyright.
# - SAnews: its user policy lets *media* use its photographs, "sourced to the
#   DOC", while its stories are credited to SAnews: REI is not media, and the
#   credit is unclear.
# - PIB: its copyright policy could not be read again to confirm it covers
#   photographs (the page answers automated readers with HTTP 403).
# A publisher is added once its permission is established, with the words that
# grant it.
IMAGE_PERMISSIONS: dict[str, ImagePermission] = {}

# Statuses of ArticleImageOut.
AVAILABLE = "AVAILABLE"
WITHHELD = "WITHHELD"
NONE = "NONE"

# Markup of the stored article that may hold its images, as connectors store it.
_MARKUP_KEYS = ("summary_html", "content_html")
# A WordPress article's featured image: the one the publisher chose to lead with.
_FEATURED_CLASS = "wp-post-image"


class _ImageFinder(HTMLParser):
    """The <img> elements of an article's markup, with the caption of the figure holding each."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.images: list[dict[str, Any]] = []
        # For each open <figure>: the index of its first image.
        self._figures: list[int] = []
        self._caption: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "figure":
            self._figures.append(len(self.images))
        elif tag == "img":
            self.images.append({"attrs": {k: v or "" for k, v in attrs}, "caption": None})
        elif tag == "figcaption" and self._figures:
            self._caption = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "figcaption" and self._caption is not None:
            caption = normalise_whitespace(" ".join(self._caption)) or None
            for image in self.images[self._figures[-1] :]:
                image["caption"] = image["caption"] or caption
            self._caption = None
        elif tag == "figure" and self._figures:
            self._figures.pop()

    def handle_data(self, data: str) -> None:
        if self._caption is not None:
            self._caption.append(data)


def _is_picture(image: dict[str, Any]) -> bool:
    """Not a tracking pixel, an inline data image or an image without an address."""
    attrs = image["attrs"]
    src = attrs.get("src", "").strip()
    if not src or src.startswith("data:"):
        return False
    for dimension in ("width", "height"):
        value = attrs.get(dimension, "").strip()
        if value.isdigit() and int(value) <= 2:
            return False
    return True


def find_article_image(raw: dict[str, Any]) -> dict[str, Any] | None:
    """The article's lead image in its stored markup: the featured image, else the first."""
    pictures: list[dict[str, Any]] = []
    for key in _MARKUP_KEYS:
        markup = raw.get(key)
        if not isinstance(markup, str) or "<img" not in markup.lower():
            continue
        finder = _ImageFinder()
        finder.feed(markup)
        finder.close()
        pictures += [image for image in finder.images if _is_picture(image)]
    featured = [p for p in pictures if _FEATURED_CLASS in p["attrs"].get("class", "").split()]
    return (featured or pictures or [None])[0]


def _host_in(url: str, hosts: tuple[str, ...]) -> bool:
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return any(host == domain or host.endswith("." + domain) for domain in hosts)


def _not_permitted_by_terms(source: Source) -> bool:
    """The source's terms, as REI's registry records them, rule out REI's use of its content."""
    return source.terms_status == "RESTRICTED" or source.commercial_use == "NOT_PERMITTED"


def article_image(artifact: SourceArtifact | None, source: Source) -> ArticleImageOut:
    """The image published with the event's article, or why none is shown."""
    if artifact is None:
        return ArticleImageOut()
    latest = artifact.latest
    found = find_article_image(latest.raw_content or {})
    if found is None:
        return ArticleImageOut()
    name = source.source_name
    permission = IMAGE_PERMISSIONS.get(source.source_id)
    url = found["attrs"]["src"].strip()
    if _not_permitted_by_terms(source):
        reason = f"{name}'s terms do not permit REI's use of its content."
    elif permission is None:
        reason = f"{name} has not given REI permission to show its images."
    elif urlsplit(url).scheme != "https":
        reason = "The image is not served over a secure connection."
    elif not _host_in(url, permission.image_hosts):
        reason = f"The image is not on {name}'s own site, so its owner is not certain."
    else:
        reason = None
    if reason is not None or permission is None:
        return ArticleImageOut(status=WITHHELD, source_url=latest.url, reason=reason)
    return ArticleImageOut(
        status=AVAILABLE,
        url=url,
        source_url=latest.url,
        found_in="article_markup",
        caption=found["caption"],
        alt_text=normalise_whitespace(found["attrs"].get("alt", "")) or None,
        # No connected feed states a photo credit; none is ever made up.
        credit=None,
        licence=permission.terms,
        attribution=permission.attribution,
    )
