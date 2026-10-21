"""Ville de Sherbrooke works ("Travaux", 21 October 2026).

    GET https://services3.arcgis.com/qsNXG7LzoUbR4c1C/arcgis/rest/services/
        Travaux/FeatureServer/0/query

The City's "Travaux en cours sur le territoire de la Ville de Sherbrooke",
updated daily, each at a point with the street (`LOCALISATION`), the cross
streets, the type of works, the effect on traffic (`CIRCULATION`) and the
period. In French. On 21 October 2026: 54 works, keyless.

Only works that state an effect on traffic are taken: "Route fermée" (a road
closure); "Circulation en alternance", "Perte d'une voie dans une
direction", "Deux voies fermées…" (a lane restriction); "Ralentissement à
prévoir" (road works). Works with "Aucun impact sur la circulation" or only
a sidewalk or cycle lane closed ("Trottoir ou voie cyclable fermé") are left
out: 20 of the 54.

`DATE_DEBUT`/`DATE_FIN` are milliseconds since 1970 (UTC); the layer repeats
them as Eastern-time text (`DATEDEBUTHE`, `DATEFINHE`, "AAAA-MM-JJ hh:mm").
One work id can name two works at two places with two periods: a record is
known by its id and its point.

Creative Commons Attribution 4.0 ("Licence Attribution (CC-BY 4.0)", the
Données Québec record of the dataset, read 21 October 2026).
"""

from datetime import datetime
from typing import Any

import httpx

from packages.cities import get_city
from packages.common.text import html_to_text
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

from .feature_feed import FeatureFeedConnector, clean, epoch_ms, fetch_arcgis_features, item_record
from .feed_text import sentences

SOURCE_ID = "sherbrooke-travaux"
LAYER = "https://services3.arcgis.com/qsNXG7LzoUbR4c1C/arcgis/rest/services/Travaux/FeatureServer/0"
SOURCE_URL = "https://www.donneesquebec.ca/recherche/dataset/04880bdf6ffa40ababfa900c2ef45b3c_0"
ATTRIBUTION = (
    "VILLE DE SHERBROOKE - DONNÉES GÉOMATIQUES. Travaux, [Jeu de données], dans Données Québec. "
    "Licence CC BY 4.0."
)
CLOSED = {"route fermée"}
LANES = {
    "circulation en alternance",
    "perte d'une voie dans une direction",
    "deux voies fermées et une seule voie accessible dans chaque direction",
}
# Works that state no effect on road traffic.
NOT_TRAFFIC = {"", "aucun impact sur la circulation", "trottoir ou voie cyclable fermé"}


def sherbrooke_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("canada")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Ville de Sherbrooke travaux (road works)",
        organization="Ville de Sherbrooke, Section de la géomatique",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Québec (Sherbrooke)",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=LAYER,
        access_method="ArcGIS feature service (ArcGIS Online), GeoJSON; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=720,
        language="fr",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.ROAD_WORKS.value,
        ),
        parser_type="sherbrooke_travaux",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0), per Données Québec",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention="Each work as the service returns it and the structured event.",
        notes=(
            "The City's works in progress, each at a point, in French, updated daily. Fetched "
            "without a key on 21 October 2026: 54 works, of which 20 state no effect on road "
            "traffic and are left out. Times are UTC milliseconds."
        ),
    )


def effect(properties: dict[str, Any]) -> str:
    return clean(properties.get("CIRCULATION")).lower()


def closes_traffic(properties: dict[str, Any]) -> bool:
    return effect(properties) not in NOT_TRAFFIC


def _event_type(properties: dict[str, Any]) -> str:
    stated = effect(properties)
    if stated in CLOSED:
        return EventType.PLANNED_ROAD_CLOSURE.value
    if stated in LANES:
        return EventType.LANE_RESTRICTION.value
    return EventType.ROAD_WORKS.value


def record_key(feature: dict[str, Any]) -> str | None:
    """The work's id and its point: one id can name two works at two places."""
    work = clean((feature.get("properties") or {}).get("ID"))
    coordinates = (feature.get("geometry") or {}).get("coordinates")
    if not work or not isinstance(coordinates, list) or len(coordinates) < 2:
        return None
    return f"{work}@{coordinates[0]:.5f},{coordinates[1]:.5f}"


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    external_id = record_key(feature)
    if not external_id or not closes_traffic(properties):
        return None
    street = clean(properties.get("LOCALISATION"))
    start_at, end_at = clean(properties.get("VOIE_DE")), clean(properties.get("VOIE_A"))
    crossing = clean(properties.get("INTERSECTION"))
    place = " ".join(
        part
        for part in (
            street,
            f"entre {start_at} et {end_at}" if start_at and end_at else "",
            f"({crossing})" if crossing else "",
        )
        if part
    )
    stated = clean(properties.get("CIRCULATION"))
    description = clean(properties.get("DESCRIPTION"))
    structured = SourceEvent(
        event_type=_event_type(properties),
        category=" / ".join(
            part
            for part in (clean(properties.get("TYPE")), clean(properties.get("SOUSTYPE")), stated)
            if part
        ),
        start=epoch_ms(properties.get("DATE_DEBUT")),
        end=epoch_ms(properties.get("DATE_FIN")),
        geometry=geometry,
        locations=[
            SourceLocation(name=place, kind="rue", geometry=geometry, closure=stated or None)
        ]
        if place
        else [],
        affected_road=street or None,
        attribution=ATTRIBUTION,
        covers_city=True,
    )
    summary = sentences(
        description,
        # The remark is written with line breaks as HTML ("<br>").
        html_to_text(properties.get("REMARQUE")),
        f"Circulation : {stated}" if stated else "",
        f"Signaleurs : {flaggers}" if (flaggers := clean(properties.get("SIGNALEUR"))) else "",
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        title=f"{stated}: {place or description} (Sherbrooke)",
        summary=summary,
        categories=[part.lower() for part in (clean(properties.get("TYPE")), stated) if part],
        item=feature,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_works(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    # The layer holds the works in progress or about to start only (a few dozen).
    return fetch_arcgis_features(LAYER, user_agent, client=client)


class SherbrookeTravauxConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_works)
    to_record = staticmethod(to_record)
