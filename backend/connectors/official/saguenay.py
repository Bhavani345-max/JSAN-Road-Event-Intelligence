"""Ville de Saguenay worksites ("Chantiers - 511", 5 November 2026).

    GET https://www.donneesquebec.ca/recherche/dataset/221d146e-f285-4eb4-9f47-09b4b36cc429/
        resource/6df36e69-fdfd-43ea-bcea-ec41525b6c86/download/sag_chantiers511.geojson

The City's list of obstructions to traffic ("Liste des entraves à la
circulation", Données Québec dataset sag_entrave_a_la_circulation, update
frequency "Horaire"), a GeoJSON file in WGS 84: one line (or multi-line) per
worksite with its id, its effect on traffic (`etat`: "Fermeture complète",
"Circulation locale", "Circulation en alternance avec feu ou signaleur",
"Restriction de voies", "Circulation à contresens"), whether the works are
planned or emergency works (`type`), the street (`localisation`), the
borough (`arrondissement`), a French description and the period. On 5
November 2026 at 04:02 Eastern time: 20 worksites, every one with an effect
on traffic: 17 current (3 of them state no end: "pour une durée
indéterminée", "jusqu'à nouvel ordre"), 1 starting later that day and 2
ended the day before (the file keeps them a while; the run window drops
them).

`date_debut`/`date_fin` are local times without an offset
("2026-11-05T07:30:00", sometimes with fractions of a second): read in
Eastern time (America/Toronto, Saguenay's zone). An empty `date_fin` stays
unstated. Two ids can name works at one place (35141 and 35142, Chemin
Saint-Wilbrod, 16 minutes apart, the second without a description): the
City lists them as two worksites, so they are two records.

No personal data. Licence: "Licence Attribution (CC-BY 4.0)", the Données
Québec record (read 5 November 2026), which recommends the citation used as
the attribution below. Données Québec's robots.txt sets Crawl-Delay 10 and
does not disallow resource downloads; one request a run.
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

from .common import fetch_json
from .feature_feed import FeatureFeedConnector, clean, item_record, local_time
from .feed_text import sentences

SOURCE_ID = "ca-saguenay-chantiers-511"
ENDPOINT = (
    "https://www.donneesquebec.ca/recherche/dataset/221d146e-f285-4eb4-9f47-09b4b36cc429/"
    "resource/6df36e69-fdfd-43ea-bcea-ec41525b6c86/download/sag_chantiers511.geojson"
)
SOURCE_URL = "https://www.donneesquebec.ca/recherche/dataset/sag_entrave_a_la_circulation"
ATTRIBUTION = (
    "VILLE DE SAGUENAY. Chantiers - 511, [Jeu de données], dans Données Québec. Licence CC BY 4.0."
)
EASTERN = ZoneInfo("America/Toronto")
FORMATS = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f")
CLOSED = {"fermeture complète", "circulation locale"}
LANES = {
    "circulation en alternance avec feu ou signaleur",
    "restriction de voies",
    "circulation à contresens",
}
EMERGENCY = "travaux d'urgence"


def saguenay_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("canada")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Ville de Saguenay chantiers 511 (worksites)",
        organization="Ville de Saguenay",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Québec (Saguenay)",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="GeoJSON file on Données Québec (WGS 84), refreshed hourly; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=60,
        language="fr",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.EMERGENCY_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.ROAD_WORKS.value,
        ),
        parser_type="saguenay_chantiers_511",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="robots.txt Crawl-Delay 10; updated hourly; polled hourly (one request).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0), per Données Québec",
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention="Each worksite as the file gives it and the structured event.",
        notes=(
            "The City's worksites with their effect on traffic, one line each, in French, updated "
            "hourly. Fetched without a key on 5 November 2026: 20 worksites (17 current, 3 of them "
            "without an end; 1 upcoming; 2 ended). Times are local Eastern time."
        ),
    )


def _event_type(state: str, kind: str) -> str:
    if state in CLOSED:
        if kind == EMERGENCY:
            return EventType.EMERGENCY_ROAD_CLOSURE.value
        return EventType.PLANNED_ROAD_CLOSURE.value
    if state in LANES:
        return EventType.LANE_RESTRICTION.value
    return EventType.ROAD_WORKS.value


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    external_id = clean(properties.get("id"))
    if not external_id:
        return None
    state = clean(properties.get("etat"))
    kind = clean(properties.get("type"))
    street = clean(properties.get("localisation"))
    borough = clean(properties.get("arrondissement"))
    first, last = clean(properties.get("date_debut")), clean(properties.get("date_fin"))
    structured = SourceEvent(
        event_type=_event_type(state.lower(), kind.lower()),
        category=" / ".join(part for part in (kind, state) if part) or None,
        start=local_time(first, EASTERN, FORMATS),
        end=local_time(last, EASTERN, FORMATS),
        geometry=geometry,
        locations=[
            SourceLocation(
                name=", ".join(part for part in (street, borough) if part),
                kind="rue",
                geometry=geometry,
                closure=state or None,
            )
        ]
        if street
        else [],
        affected_road=street or None,
        attribution=ATTRIBUTION,
        stated_period=" – ".join((first or "?", last or "?")) if first or last else None,
        covers_city=True,
    )
    place = ", ".join(part for part in (street, borough) if part)
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        title=f"{state or 'Chantier'}: {place or 'Saguenay'} (Saguenay)",
        summary=sentences(
            clean(properties.get("description")),
            f"Circulation : {state}" if state else "",
            f"Type : {kind}" if kind else "",
        ),
        categories=[part.lower() for part in (kind, state) if part],
        item=feature,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_worksites(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    body = fetch_json(ENDPOINT, user_agent, client=client)
    features = body.get("features") if isinstance(body, dict) else None
    if not isinstance(features, list):
        raise ConnectorError(f"{ENDPOINT} did not return a GeoJSON feature collection")
    return [feature for feature in features if isinstance(feature, dict)]


class SaguenayChantiersConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_worksites)
    to_record = staticmethod(to_record)
