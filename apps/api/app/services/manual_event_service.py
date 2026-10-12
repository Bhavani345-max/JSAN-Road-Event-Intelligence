"""Events entered by a reviewer, for road events no connected source reported.

A manual entry is treated like any other source item: what the reviewer typed
is stored as evidence first, and the event is derived from it. The event
records who entered it and on what basis, starts as VALIDATION_REQUIRED like
every event, and is located the same way as an article's, by a known place
name; nothing is filled in that the reviewer did not state.
"""

import json
import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.models import Event, SourceArtifact
from app.repositories.events import EventRepository
from connectors.manual import MANUAL_ENTRY
from packages.common.hashing import sha256_hex
from packages.common.time import end_of_day_ist, ensure_utc, start_of_day_ist, utc_now
from packages.event_schema import (
    EventDetection,
    EventLocation,
    EventStatus,
    EventType,
    ReiEvent,
)
from packages.geo_models import Point
from services.extraction.event_factory import LOCATION_METHOD, event_id_for
from services.geo_resolution import PlaceMatch, PlaceResolver

DETECTION_METHOD = "manual_entry"
CLASSIFICATION = "MANUAL_ENTRY"
# Where a manual entry's place was named: in the entry itself.
FOUND_IN = "entry"


def _locate(resolver: PlaceResolver, place: str | None) -> PlaceMatch | None:
    """The known place the reviewer named, if it points to one spot."""
    if not place:
        return None
    exact = resolver.lookup(place, found_in=FOUND_IN)
    candidates = [exact] if exact else resolver.find_in(place, FOUND_IN, require_capital=False)
    return next((match for match in candidates if match.has_position), None)


def create_manual_event(
    session: Session,
    resolver: PlaceResolver,
    *,
    title: str,
    basis: str,
    entered_by: str,
    event_type: EventType | None = None,
    description: str | None = None,
    place: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    reference_url: str | None = None,
) -> Event:
    now = utc_now()
    entry = {
        "title": title,
        "event_type": event_type.value if event_type else None,
        "description": description,
        "place": place,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "reference_url": reference_url,
        "basis": basis,
        "entered_by": entered_by,
        "entered_at": now.isoformat(),
        "acquired_from": "manual entry by a reviewer",
    }
    external_id = str(uuid.uuid4())
    artifact = SourceArtifact(
        artifact_id=str(uuid.uuid4()),
        source_id=MANUAL_ENTRY.source_id,
        external_id=external_id,
        url=reference_url,
        title=title,
        published_at=None,
        retrieved_at=now,
        raw_content=entry,
        content_hash=sha256_hex(json.dumps(entry, sort_keys=True)),
        classification=CLASSIFICATION,
        classification_details={"method": DETECTION_METHOD, "entered_by": entered_by},
        created_at=now,
    )
    session.add(artifact)
    # Evidence must exist in the database before an event refers to it.
    session.flush()

    located_by = _locate(resolver, place)
    event = ReiEvent(
        event_id=event_id_for(MANUAL_ENTRY.source_id, external_id),
        source_id=MANUAL_ENTRY.source_id,
        source_reference=reference_url,
        title=title,
        event_type=event_type,
        description=description,
        city="Hyderabad",
        affected_road=place,
        # Whole days in IST, held in UTC like every stored time.
        start_time=ensure_utc(start_of_day_ist(start_date)) if start_date else None,
        end_time=ensure_utc(end_of_day_ist(end_date)) if end_date else None,
        status=EventStatus.VALIDATION_REQUIRED,
        geometry=(
            Point(type="Point", coordinates=(located_by.longitude, located_by.latitude))
            if located_by
            else None
        ),
        detection=EventDetection(
            method=DETECTION_METHOD,
            score=0,
            matched_keywords=[],
            places=[located_by.name] if located_by else [],
            location=(
                EventLocation(
                    method=LOCATION_METHOD,
                    place_name=located_by.name,
                    place_kind=located_by.kind,
                    precision=located_by.precision,
                    mention=located_by.mention,
                    found_in=FOUND_IN,
                    reference=f"OpenStreetMap {located_by.osm_ref}",
                )
                if located_by
                else None
            ),
            basis=basis,
        ),
        created_at=now,
        updated_at=now,
    )
    row = EventRepository(session).add(
        event,
        artifact_id=artifact.artifact_id,
        change_reason=f"Entered manually. Basis: {basis}",
        changed_by=entered_by,
    )
    session.commit()
    return row
