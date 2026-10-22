"""Málaga traffic cuts (cortes de tráfico), Spain.

    GET https://datosabiertos.malaga.eu/recursos/transporte/trafico/da_cortesTrafico-4326.geojson

Málaga City Council's current and planned traffic cuts on municipal streets,
a GeoJSON FeatureCollection of points in WGS 84, rebuilt daily. Each feature
has an id (`ID`, and `NOMBRE` such as `AFECTACION_0000576_313322`), the
street address (`DIRECCION`), a description in Spanish (`DESCRIPCION`), a
start and an end (`DESDE`, `HASTA`, Málaga time written `dd/mm/yyyy H:MM`),
what is cut (`TIPOAFECTACION`) and why (`TIPOCORTE`), and sometimes a note
naming the company or department doing the work (`NOTAS`). Each point carries
a stray third value (it looks like the UTM northing); it is dropped. Fetched on
22 October 2026: 110 features, 103 with a start and 101 with an end.

The type comes from `TIPOAFECTACION` only: Corte (a cut) is a planned road
closure, Ocupación de calzada (part of the carriageway taken) a lane
restriction. Ocupación de estacionamiento takes parking spaces only and is not
a road event, so it is not kept. Anything else keeps its words with no type.
The description is kept as the summary and never read into a type or a time.

Licence: the dataset page names "CC BY 4.0", but its licence link and its
metadata name CC BY-SA 4.0; both permit commercial use with attribution, and
BY-SA asks that adapted data be shared alike. It is treated as CC BY-SA 4.0
until Málaga confirms. Credit "Ayuntamiento de Málaga"
(docs/data-sources/spain-sources-2026-10-22.md).
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

SOURCE_ID = "malaga-traffic-cuts"
ENDPOINT = "https://datosabiertos.malaga.eu/recursos/transporte/trafico/da_cortesTrafico-4326.geojson"
SOURCE_URL = "https://datosabiertos.malaga.eu/dataset/cortes-de-trafico"
ATTRIBUTION = "Ayuntamiento de Málaga, Cortes de tráfico (datos abiertos), CC BY-SA 4.0"
MALAGA = ZoneInfo("Europe/Madrid")

# What is cut, as the source writes it, and the REI type it is.
CUT = "corte"
CARRIAGEWAY_TAKEN = "ocupación de calzada"
PARKING_ONLY = "ocupación de estacionamiento"


def malaga_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("malaga")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Málaga traffic cuts",
        organization="Ayuntamiento de Málaga (Área de Movilidad)",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region="Andalusia",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="Public GeoJSON file, WGS 84 points, rebuilt daily; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=360,
        language="es",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
        ),
        parser_type="malaga_traffic_cuts",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; robots.txt asks Crawl-delay 10; the file is rebuilt once a day; polled every 6 hours.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=(
            "CC BY-SA 4.0 as the dataset's licence link and metadata state (its page text says "
            "CC BY 4.0); commercial use permitted with attribution, adaptations shared alike"
        ),
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention="Each traffic cut as received.",
        notes=(
            "Current and planned traffic cuts on Málaga's municipal streets, each a point with a "
            "start and an end. Fetched on 22 October 2026: 110 features (60 carriageway "
            "occupations, 34 cuts, 9 parking-only occupations, 7 blank), 103 with a start."
        ),
    )


def _time(value: Any) -> datetime | None:
    """"29/10/2025 9:30" in Málaga time."""
    return local_time(value, MALAGA, ("%d/%m/%Y %H:%M",))


def to_record(item: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = item.get("properties") or {}
    external_id = clean(properties.get("NOMBRE")) or clean(properties.get("ID"))
    coordinates = (item.get("geometry") or {}).get("coordinates") or []
    try:
        longitude, latitude = float(coordinates[0]), float(coordinates[1])
    except (IndexError, TypeError, ValueError):
        return None
    if not external_id or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    affected = clean(properties.get("TIPOAFECTACION"))
    reason = clean(properties.get("TIPOCORTE"))
    if affected.lower() == PARKING_ONLY:
        return None  # parking spaces only: not a road event
    if affected.lower() == CUT:
        event_type, label = EventType.PLANNED_ROAD_CLOSURE.value, "Road closed"
    elif affected.lower() == CARRIAGEWAY_TAKEN:
        event_type, label = EventType.LANE_RESTRICTION.value, "Carriageway partly taken"
    else:
        event_type, label = None, "Traffic cut"
    geometry = {"type": "Point", "coordinates": [longitude, latitude]}
    address = clean(properties.get("DIRECCION"))
    description = clean(properties.get("DESCRIPCION"))
    note = clean(properties.get("NOTAS"))
    start_text, end_text = clean(properties.get("DESDE")), clean(properties.get("HASTA"))
    categories = [part for part in (affected, reason) if part]
    structured = SourceEvent(
        event_type=event_type,
        category=" / ".join(categories) or None,
        start=_time(start_text),
        end=_time(end_text),
        geometry=geometry,
        locations=[SourceLocation(name=address or "Málaga", kind="address point", geometry=geometry)],
        attribution=ATTRIBUTION,
        stated_period=f"{start_text} – {end_text} (Málaga time)" if start_text or end_text else None,
        covers_city=True,
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        title=f"{label}{f' ({reason.lower()})' if reason else ''}: {address or 'Málaga'}",
        summary=". ".join(
            part
            for part in (
                description,
                f"What is cut: {affected}" if affected else "",
                f"Reason: {reason}" if reason else "",
                f"Note: {note}" if note else "",
            )
            if part
        )
        or None,
        categories=categories,
        item=item,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_cuts(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    """Each feature of the traffic cuts layer."""
    body = fetch_json(ENDPOINT, user_agent, client=client)
    if not isinstance(body, dict) or body.get("type") != "FeatureCollection":
        raise ConnectorError(f"{ENDPOINT} did not return a GeoJSON FeatureCollection")
    features = body.get("features")
    if not isinstance(features, list):
        raise ConnectorError(f"{ENDPOINT} did not return a feature list")
    return [feature for feature in features if isinstance(feature, dict)]


class MalagaTrafficCutsConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_cuts)
    to_record = staticmethod(to_record)
