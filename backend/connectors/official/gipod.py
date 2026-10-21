"""GIPOD planned mobility hindrance, Flanders, Belgium (21 October 2026).

    GET https://geo.api.vlaanderen.be/GIPOD/ogc/features/v1/collections/HINDER/items
        ?f=application/geo+json&limit=1000&crs=http://www.opengis.net/def/crs/OGC/1.3/CRS84
        &filter=<the motor-traffic consequences below>&filter-lang=cql-text

GIPOD, the Flemish register of works and events on the public domain, lists
the mobility hindrance each one causes, today and in the coming six months
(OGC API Features, GeoJSON): one feature per hindrance zone and period, a
WGS 84 MultiPolygon, the consequences in Dutch ("Versmalde rijstroken;
Parkeerverbod"), whether the hindrance is severe, its owner, and a start and an
end in UTC. Fetched without a key on 21 October 2026.

Most zones are parking bans or footway and cycle-path restrictions. Only zones
whose consequences state an effect on motor traffic are asked for (the filter
runs on the server, in the source's own words) and taken:

- "Geen doorgang voor gemotoriseerd verkeer" (no passage for motor traffic,
  also "… uitgezonderd plaatselijk verkeer", local traffic excepted) and
  "Afgesloten in 1 rijrichting" (closed in one direction) are a planned road
  closure;
- "Vermindering van rijstroken", "Versmalde rijstroken" (fewer, narrower
  lanes) and "Wisselend verkeer via verkeersborden/verkeerslichten"
  (alternating traffic) are a lane restriction;
- "Snelheidsbeperking" (speed limit), "Rijrichting omgekeerd" (direction
  reversed) and "Tijdelijk tweerichtingsverkeer" (temporary two-way traffic)
  keep their words with no type.

On 21 October 2026 the register held 18,035 such zones (more than the WFS
count cap of 10,000; 19 pages), so the connector follows the API's `next`
links, a page of 1,000 at a time, one after another.

Each zone carries the contact people of its organisations
(`HindranceContactOrganisations`: names, e-mail addresses, telephone numbers);
that field is not kept.

Licence: Modellicentie voor gratis hergebruik v1.0 (Flanders), named by the
dataset's metadata record 2b4b3bb7-cadc-41a0-b5ae-796a84a20b52; Art. 3 allows
commercial exploitation; Art. 4 asks for credit to the licensor and forbids
suggesting official status (docs/data-sources/belgium-germany-austria-connectors-2026-10-21.md).
"""

import re
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

import httpx

from connectors.base import ConnectorError
from packages.cities import get_city
from packages.event_schema import EventType
from packages.source_models import (
    CommercialUse,
    CostCategory,
    IntegrationStatus,
    RawSourceRecord,
    SourceClass,
    SourceDefinition,
    SourceEvent,
    SourceLocation,
    SourceType,
    TermsStatus,
)

from . import common
from .common import content_key, fetch_json
from .feature_feed import FeatureFeedConnector, clean, item_record

SOURCE_ID = "flanders-gipod-hindrance"
ENDPOINT = "https://geo.api.vlaanderen.be/GIPOD/ogc/features/v1/collections/HINDER/items"
SOURCE_URL = "https://geo.api.vlaanderen.be/GIPOD/ogc/features/v1/collections/HINDER"
LICENCE_URL = "https://data.vlaanderen.be/id/licentie/modellicentie-gratis-hergebruik/v1.0"
ATTRIBUTION = (
    "GIPOD: Athumi (Vlaams Datanutsbedrijf), distributed by Digitaal Vlaanderen; "
    f"Modellicentie voor gratis hergebruik v1.0 ({LICENCE_URL})"
)
CRS84 = "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
PAGE_SIZE = 1000
# More pages than this is not the register REI read on 21 October 2026; stop
# rather than loop (or fetch far more than a run can store).
MAX_PAGES = 40
# A pause between pages, so the register is never asked twice at once.
PAGE_PAUSE_SECONDS = 1.0

# The consequence words that say motor traffic is affected, as the register writes them.
TRAFFIC_WORDS = (
    "gemotoriseerd verkeer",
    "Afgesloten",
    "rijstroken",
    "Wisselend verkeer",
    "Snelheidsbeperking",
    "Rijrichting",
    "tweerichtingsverkeer",
)
TRAFFIC_FILTER = " OR ".join(f"Consequences LIKE '%{words}%'" for words in TRAFFIC_WORDS)
PARAMS = {
    "f": "application/geo+json",
    "limit": str(PAGE_SIZE),
    "crs": CRS84,
    "filter": TRAFFIC_FILTER,
    "filter-lang": "cql-text",
}
# Contact people of the hindrance's organisations: personal data, not kept.
PERSONAL_FIELDS = frozenset({"HindranceContactOrganisations"})
# Bookkeeping: a new modification time alone is not a revision.
BOOKKEEPING_FIELDS = frozenset({"HindranceLastModifiedOn"})
CAUSES = {"works": "works", "groundworks": "groundworks", "events": "event"}
# "2980 Zoersel, Oostmallebaan 10: parkeerverbod …": where, as a description may begin.
ADDRESS = re.compile(r"^(?P<postcode>\d{4}) (?P<municipality>[^,:]+), (?P<street>[^:]+):")
CLOSURE, LANES, OTHER = "closure", "lanes", "other"
LABELS = {
    CLOSURE: (EventType.PLANNED_ROAD_CLOSURE.value, "Road closed"),
    LANES: (EventType.LANE_RESTRICTION.value, "Lane restriction"),
    OTHER: (None, "Traffic hindrance"),
}


def gipod_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("belgium")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="GIPOD planned mobility hindrance (Flanders)",
        organization="Athumi (Vlaams Datanutsbedrijf), GIPOD; distributed by Digitaal Vlaanderen",
        authority_type="REGIONAL_GOVERNMENT",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Flanders",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="OGC API Features (GeoJSON, CRS84), paged; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=480,
        language="nl",
        events_supported=(EventType.PLANNED_ROAD_CLOSURE.value, EventType.LANE_RESTRICTION.value),
        parser_type="gipod_hindrance",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit=(
            "None published; polled three times a day, pages of 1,000 fetched one after "
            "another with a pause."
        ),
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=f"Modellicentie voor gratis hergebruik v1.0 (Flanders), {LICENCE_URL}",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention="Each hindrance zone as received, less its organisations' contact people.",
        notes=(
            "Planned mobility hindrance on Flanders' public domain (GIPOD), today and six months "
            "ahead: only zones whose consequences affect motor traffic (closures, fewer or narrower "
            "lanes, alternating traffic, speed limits). Each zone a MultiPolygon with a start and an "
            "end. 18,035 such zones on 21 October 2026. The licence forbids suggesting official "
            "status."
        ),
    )


def traffic_effect(consequence: str) -> str | None:
    """What one stated consequence does to motor traffic, if anything."""
    if consequence.startswith(("Geen doorgang voor gemotoriseerd verkeer", "Afgesloten")):
        return CLOSURE
    if "rijstroken" in consequence or consequence.startswith("Wisselend verkeer"):
        return LANES
    if any(words in consequence for words in TRAFFIC_WORDS):
        return OTHER
    return None


def utc_time(value: Any) -> datetime | None:
    """GIPOD's times: ISO 8601 in UTC ('2026-10-23T06:00:00Z')."""
    text = clean(value)
    if not text:
        return None
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else None


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    if geometry.get("type") not in ("Polygon", "MultiPolygon"):
        return None
    external_id = clean(feature.get("id"))
    if not external_id:
        return None
    consequences = [clean(part) for part in str(properties.get("Consequences") or "").split(";") if clean(part)]
    traffic = [(part, effect) for part in consequences if (effect := traffic_effect(part))]
    if not traffic:
        return None  # parking, footway or cycle path only: not a road event
    effects = {effect for _, effect in traffic}
    kind = next(effect for effect in (CLOSURE, LANES, OTHER) if effect in effects)
    event_type, label = LABELS[kind]
    traffic_words = "; ".join(part for part, _ in traffic)

    description = clean(properties.get("HindranceDescription"))
    if description in ("HinderZone", "WerfZone"):
        description = ""  # the zone's type repeated, nothing more
    address = ADDRESS.match(description)
    street = clean(address["street"]) if address else ""
    place = f"{street}, {address['postcode']} {clean(address['municipality'])}" if address else ""
    owner = clean(properties.get("HindranceOwner"))
    zone_type = clean(properties.get("ZoneType"))
    cause_link = clean(properties.get("HindranceConsequenceOf"))
    cause = next((name for key, name in CAUSES.items() if f"/{key}/" in cause_link), "")
    start_text, end_text = clean(properties.get("HindranceStart")), clean(properties.get("HindranceEnd"))
    structured = SourceEvent(
        event_type=event_type,
        category=" / ".join(part for part in (zone_type, cause, "; ".join(consequences)) if part),
        severity="Severe hindrance" if properties.get("SevereHindrance") is True else None,
        status=clean(properties.get("HindranceStatus")) or None,
        start=utc_time(start_text),
        end=utc_time(end_text),
        geometry=geometry,
        locations=[SourceLocation(name=place, kind="zone", geometry=geometry, closure=traffic_words)]
        if place
        else [],
        affected_road=street or None,
        attribution=ATTRIBUTION,
        stated_period=f"{start_text} – {end_text} (UTC)" if start_text or end_text else None,
    )
    hindrance = clean(properties.get("HindranceGipodId"))
    if place:
        where = place
    elif hindrance:
        where = f"GIPOD hindrance {hindrance}"
    else:
        where = "Flanders"
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=f"{ENDPOINT}/{external_id}",
        title=f"{label}: {where}{f' ({owner})' if owner else ''}",
        summary=". ".join(part for part in (traffic_words, description) if part) or None,
        categories=[part for part in (label.lower(), zone_type, cause) if part],
        item=_without_personal_data(feature),
        structured=structured,
        retrieved_at=retrieved_at,
    )


def _without_personal_data(feature: dict[str, Any]) -> dict[str, Any]:
    properties = {k: v for k, v in feature["properties"].items() if k not in PERSONAL_FIELDS}
    return {**feature, "properties": properties}


def _check_axis_order(feature: dict[str, Any]) -> None:
    """Flanders lies at about 3-6° E, 50-51.5° N: a first number above the second is a latitude."""
    position: Any = (feature.get("geometry") or {}).get("coordinates")
    while isinstance(position, list) and position and isinstance(position[0], list):
        position = position[0]
    if isinstance(position, list) and len(position) >= 2 and position[0] > position[1]:
        raise ConnectorError(f"{ENDPOINT} returned coordinates in latitude-longitude order")


def _next_page(body: dict[str, Any]) -> str | None:
    """The API's own link to the next page, only on its own host."""
    for link in body.get("links") or ():
        if isinstance(link, dict) and link.get("rel") == "next" and isinstance(link.get("href"), str):
            if urlsplit(link["href"]).netloc == urlsplit(ENDPOINT).netloc:
                return link["href"]
            raise ConnectorError(f"{ENDPOINT} pointed its next page to another host")
    return None


def fetch_zones(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    zones: dict[str, dict] = {}
    url, params = ENDPOINT, PARAMS
    for page in range(MAX_PAGES):
        if page:
            common._sleep(PAGE_PAUSE_SECONDS)
        body = fetch_json(url, user_agent, client=client, params=params)
        features = body.get("features") if isinstance(body, dict) else None
        if not isinstance(features, list):
            raise ConnectorError(f"{ENDPOINT} did not return a GeoJSON feature collection")
        for feature in features:
            if isinstance(feature, dict):
                _check_axis_order(feature)
                # A zone moved between pages while they were read is listed once.
                zones.setdefault(str(feature.get("id")), _drop_personal(feature))
        url, params = _next_page(body), None
        if not url or not features:
            return list(zones.values())
    raise ConnectorError(f"{ENDPOINT} lists more than {MAX_PAGES} pages of {PAGE_SIZE} zones")


def _drop_personal(feature: dict[str, Any]) -> dict[str, Any]:
    """The zone without its contact people, as soon as it is read."""
    if isinstance(feature.get("properties"), dict):
        return _without_personal_data(feature)
    return feature


class GipodHindranceConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_zones)
    to_record = staticmethod(to_record)

    @staticmethod
    def revision_key(raw: dict) -> str:
        """The zone's content: a new modification time alone is not a revision."""
        item = raw.get("item", {})
        properties = {
            key: value for key, value in (item.get("properties") or {}).items() if key not in BOOKKEEPING_FIELDS
        }
        return content_key({**item, "properties": properties}, frozenset())
