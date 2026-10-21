"""Hamburg roadworks (Bauweiser), Germany (21 October 2026).

    GET https://api.hamburg.de/datasets/v1/baustellen/collections/baustelle/items
        ?f=json&limit=10000&crs=http://www.opengis.net/def/crs/OGC/1.3/CRS84

The construction-site profiles of Hamburg's "Bauweiser" platform (OGC API
Features, GeoJSON), written and kept by the bodies carrying out the works
(Hamburg's road agency, utilities, the Hochbahn, the districts): each a WGS 84
point with a title, the organisation, the reason, the extent of the works and
its closures in German, a detour when there is one, and a first and a last
day (`baubeginn`, `bauende`, written dd.mm.yyyy). Fetched without a key on
21 October 2026: 154 works, all with both days.

Every profile is a works site, so each is road works; the closures it causes
are stated in its German text (`umfang`), kept in the summary. A period
stated in days runs from the start of the first day to the end of the last,
Hamburg time.

Licence: Datenlizenz Deutschland – Namensnennung – Version 2.0 (dl-de/by-2-0),
the API's `license` link; credit "Freie und Hansestadt Hamburg, Behörde für
Verkehr und Mobilitätswende" (its `attribution` field), the licence with its
link, the dataset's address, and a note that the data were changed (§ 2, § 3)
(docs/data-sources/belgium-germany-austria-connectors-2026-10-21.md).
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

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

from .common import content_key, fetch_json
from .feature_feed import FeatureFeedConnector, clean, item_record, whole_days

SOURCE_ID = "hamburg-roadworks"
ENDPOINT = "https://api.hamburg.de/datasets/v1/baustellen/collections/baustelle/items"
CRS84 = "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
PARAMS = {"f": "json", "limit": "10000", "crs": CRS84}
SOURCE_URL = "https://api.hamburg.de/datasets/v1/baustellen"
ATTRIBUTION = (
    "Freie und Hansestadt Hamburg, Behörde für Verkehr und Mobilitätswende; Datenlizenz "
    "Deutschland – Namensnennung – Version 2.0 (www.govdata.de/dl-de/by-2-0); "
    f"{SOURCE_URL}; data changed (read into REI events)"
)
BERLIN = ZoneInfo("Europe/Berlin")
# Bookkeeping: a new "last updated" time alone is not a revision.
BOOKKEEPING_FIELDS = frozenset({"letzteaktualisierung"})


def hamburg_roadworks_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("hamburg")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Hamburg roadworks (Bauweiser)",
        organization="Freie und Hansestadt Hamburg, Behörde für Verkehr und Mobilitätswende",
        authority_type="MUNICIPAL_TRANSPORT_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region="Hamburg",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="OGC API Features (GeoJSON, WGS 84); no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=180,
        language="de",
        events_supported=(EventType.ROAD_WORKS.value,),
        parser_type="hamburg_roadworks",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; polled every three hours.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Datenlizenz Deutschland – Namensnennung – Version 2.0 (dl-de/by-2-0)",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention="Each works profile as received.",
        notes=(
            "Hamburg's larger works sites (Bauweiser), each a point with a first and a last day and "
            "its closures and detours in German. Fetched without a key on 21 October 2026: 154 works."
        ),
    )


def _day(value: Any):
    """A day written dd.mm.yyyy ('31.12.2026')."""
    try:
        return datetime.strptime(clean(value), "%d.%m.%Y").date()
    except ValueError:
        return None


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict) or geometry.get("type") != "Point":
        return None
    external_id = clean(feature.get("id"))
    if not external_id:
        return None
    title = clean(properties.get("titel"))
    first, last = clean(properties.get("baubeginn")), clean(properties.get("bauende"))
    start, end = whole_days(_day(first), _day(last), BERLIN)
    hotspot = properties.get("isthotspot") is True
    structured = SourceEvent(
        event_type=EventType.ROAD_WORKS.value,
        category=" / ".join(part for part in ("Baustelle", "Hotspot" if hotspot else "") if part),
        start=start,
        end=end,
        geometry=geometry,
        locations=[SourceLocation(name=title, kind="works site", geometry=geometry)] if title else [],
        attribution=ATTRIBUTION,
        stated_period=f"{first} – {last}" if first or last else None,
        covers_city=True,
    )
    detour = clean(properties.get("umleitungsbeschreibung"))
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=f"{ENDPOINT}/{external_id}",
        title=f"Road works: {title or 'Hamburg'} (Hamburg)",
        summary=". ".join(
            part.rstrip(".")
            for part in (
                clean(properties.get("anlass")),
                clean(properties.get("umfang")),
                f"Umleitung: {detour}" if detour else "",
                clean(properties.get("organisation")),
            )
            if part
        )
        or None,
        categories=[part for part in ("road works", "hotspot" if hotspot else "") if part],
        item=feature,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_works(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    body = fetch_json(ENDPOINT, user_agent, client=client, params=PARAMS)
    features = body.get("features") if isinstance(body, dict) else None
    if not isinstance(features, list):
        raise ConnectorError(f"{ENDPOINT} did not return a GeoJSON feature collection")
    if isinstance(body.get("numberMatched"), int) and body["numberMatched"] > len(features):
        raise ConnectorError(f"{ENDPOINT} lists {body['numberMatched']} works, more than one page")
    works = [feature for feature in features if isinstance(feature, dict)]
    for feature in works:
        # Hamburg lies at about 10° E, 53.5° N: a first number above the second is a latitude.
        position = (feature.get("geometry") or {}).get("coordinates")
        if isinstance(position, list) and len(position) >= 2 and position[0] > position[1]:
            raise ConnectorError(f"{ENDPOINT} returned coordinates in latitude-longitude order")
    return works


class HamburgRoadworksConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_works)
    to_record = staticmethod(to_record)

    @staticmethod
    def revision_key(raw: dict) -> str:
        """The profile's content: a new "last updated" time alone is not a revision."""
        item = raw.get("item", {})
        properties = {
            key: value for key, value in (item.get("properties") or {}).items() if key not in BOOKKEEPING_FIELDS
        }
        return content_key({**item, "properties": properties}, frozenset())
