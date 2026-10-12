"""GIS resolution of events, junction references, and the reviewer's decisions.

Location precedence, highest first; a lower method never replaces a higher:

    1. SOURCE_PROVIDED   an authority's own geometry (TfL, Toronto)
    2. HUMAN_CORRECTED / QC_APPROVED   a reviewer's decision
    3. GIS_RESOLVED      this engine, a proposal until a reviewer approves it
    4. APPROXIMATE       a named place's position
    5. UNRESOLVED        not located

The resolver runs per affected location; each keeps its own result. The
event's own geometry becomes GIS_RESOLVED only from an unambiguous HIGH
result found in the headline or summary (a place named only in the body may
be a diversion route). The location it replaces is kept, and restored if a
reviewer rejects the proposal. Running the resolver again with the same
result changes nothing.
"""

from datetime import datetime

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Event, JunctionReference
from app.repositories.events import EventRepository
from packages.cities import City, get_city, load_cities
from packages.common.text import html_to_text
from packages.common.time import utc_now
from packages.event_schema import (
    GIS_RESOLVED,
    AffectedLocation,
    EventLocation,
    GisLocationResult,
    GisResolution,
    LocationClass,
)
from packages.geo_models import Geometry
from services.geo_resolution import resolver_for
from services.gis_resolution.network import name_key
from services.gis_resolution.resolver import (
    ENGINE,
    Confidence,
    GisRequest,
    JunctionRef,
    LocationResult,
    MatchMethod,
    OsmGisEngine,
)

ACTOR = "gis-resolver"
PROTECTED = {
    LocationClass.SOURCE_PROVIDED.value,
    LocationClass.HUMAN_CORRECTED.value,
    LocationClass.QC_APPROVED.value,
}
_PRIMARY_FIELDS = ("title", "summary")
_GEOMETRY = TypeAdapter(Geometry)


class GisNotAvailable(Exception):
    pass


class GisActionRefused(Exception):
    pass


class JunctionNotFound(Exception):
    pass


# --- junction references ----------------------------------------------------------------


def junction_refs(session: Session, city_id: str) -> list[JunctionRef]:
    rows = session.scalars(select(JunctionReference).where(JunctionReference.city == city_id))
    return [
        JunctionRef(
            ref_id=row.junction_id,
            name=row.canonical_name,
            aliases=tuple(row.aliases or ()),
            status=row.status,
            position=(row.longitude, row.latitude) if row.latitude is not None else None,
            osm_node_id=row.osm_node_id,
            related_roads=tuple(row.related_roads or ()),
        )
        for row in rows
    ]


def propose_junction(
    session: Session,
    *,
    city_id: str,
    name: str,
    source: str,
    aliases: list[str] | None = None,
    position: tuple[float, float] | None = None,
    osm_node_id: int | None = None,
    related_roads: list[str] | None = None,
) -> JunctionReference:
    """Record a junction name as UNCONFIRMED. A position only from a real feature."""
    key = name_key(name)
    existing = session.scalars(
        select(JunctionReference).where(JunctionReference.city == city_id, JunctionReference.name_key == key)
    ).first()
    if existing is not None:
        return existing
    now = utc_now()
    row = JunctionReference(
        city=city_id, canonical_name=name, name_key=key, aliases=aliases or [],
        latitude=position[1] if position else None, longitude=position[0] if position else None,
        osm_node_id=osm_node_id, related_roads=related_roads or [], source=source,
        status="UNCONFIRMED", created_at=now, updated_at=now,
    )  # fmt: skip
    session.add(row)
    session.commit()
    return row


def decide_junction(
    session: Session, junction_id: int, *, confirm: bool, reviewer: str, reason: str, method: str
) -> JunctionReference:
    row = session.get(JunctionReference, junction_id)
    if row is None:
        raise JunctionNotFound(junction_id)
    if row.status != "UNCONFIRMED":
        raise GisActionRefused(f"This junction reference is already {row.status.lower()}.")
    if confirm and row.latitude is None:
        raise GisActionRefused("A junction without a position cannot be confirmed; place it first.")
    now = utc_now()
    row.status = "CONFIRMED" if confirm else "REJECTED"
    row.reviewer = reviewer
    row.confirmed_at = now if confirm else None
    row.confirmation_method = method
    row.decision_reason = reason
    row.updated_at = now
    session.commit()
    return row


# --- resolving --------------------------------------------------------------------------


def city_of(row: Event) -> City | None:
    return next((c for c in load_cities().values() if c.name == row.city), None)


def build_request(row: Event) -> GisRequest:
    """What the resolver reads: the headline, summary and body, and names REI already found."""
    latest = row.artifact.latest if row.artifact else None
    raw = (latest.raw_content if latest else None) or {}
    detection = row.detection or {}
    known: list[tuple[str, str]] = []
    for mention in detection.get("road_mentions") or []:
        known.append((mention, "summary"))
    for location in detection.get("affected_locations") or []:
        if location.get("found_in") in _PRIMARY_FIELDS:
            known.append((location["name"], location["found_in"]))
    city = city_of(row)
    return GisRequest(
        event_id=row.event_id,
        city_id=city.id if city else "",
        title=row.title,
        summary=html_to_text(raw.get("summary_html")) or row.description,
        body=html_to_text(raw.get("content_html")) or None,
        known=tuple(known),
    )


def engine_for(session: Session, city: City, network) -> OsmGisEngine:
    return OsmGisEngine(
        network, junction_refs(session, city.id), places=resolver_for(city), bbox=tuple(city.bbox)
    )


def _model(result: LocationResult, applied: bool) -> GisLocationResult:
    def candidate(c):
        if c is None:
            return None
        return {
            "matched_name": c.matched_name, "method": c.method.value, "geometry": c.geometry,
            "osm_ids": list(c.osm_ids), "reasons": list(c.reasons),
        }  # fmt: skip

    return GisLocationResult(
        mention=result.mention.text,
        found_in=result.mention.found_in,
        kind=result.mention.kind,
        confidence=result.confidence.value,
        ambiguous=result.ambiguous,
        chosen=candidate(result.chosen),
        alternatives=[candidate(c) for c in result.alternatives],
        reasons=list(result.reasons),
        applied=applied,
    )


def _location_class(detection: dict) -> str:
    if detection.get("location_class"):
        return detection["location_class"]
    location = detection.get("location") or {}
    return {
        "named_place": "APPROXIMATE", "reviewer_placed": "HUMAN_CORRECTED",
        "source_provided": "SOURCE_PROVIDED", "gis_resolved": "GIS_RESOLVED",
    }.get(location.get("method"), "UNRESOLVED")  # fmt: skip


def _comparable(gis: dict | None) -> tuple:
    if not gis:
        return ()
    return (gis.get("network"), gis.get("applied"), [
        {k: v for k, v in r.items()} for r in gis.get("results") or []
    ])  # fmt: skip


def _apply_location(detection: dict, row: Event, result: GisLocationResult, network: str, method: str | None = None) -> None:
    chosen = result.chosen
    row.geometry = _GEOMETRY.validate_python(chosen.geometry).model_dump(mode="json")
    detection["location"] = EventLocation(
        method=GIS_RESOLVED,
        place_name=chosen.matched_name,
        place_kind=result.kind,
        precision="road" if chosen.geometry["type"] != "Point" else "place",
        mention=result.mention,
        found_in=result.found_in,
        reference=f"{network}: {', '.join(chosen.osm_ids[:6])}"
        + (f" ({method})" if method else f" ({chosen.method})"),
    ).model_dump(mode="json")
    detection["location_class"] = LocationClass.GIS_RESOLVED.value


def _update_affected(detection: dict, results: list[GisLocationResult], *, protected: bool) -> None:
    locations = [AffectedLocation.model_validate(loc) for loc in detection.get("affected_locations") or []]
    # Positions, not objects: an entry is replaced by an updated copy below.
    by_key = {name_key(loc.name): i for i, loc in enumerate(locations)}
    for result in results:
        keys = {name_key(result.mention)}
        if result.chosen:
            keys.add(name_key(result.chosen.matched_name))
        index = next((by_key[k] for k in keys if k in by_key), None)
        defensible = result.confidence == "HIGH" and not result.ambiguous and result.chosen is not None
        if index is None:
            if result.confidence == "LOW":
                continue
            target = AffectedLocation(name=result.mention, kind=result.kind, resolution=LocationClass.UNRESOLVED,
                                      mention=result.mention, found_in=result.found_in)  # fmt: skip
            locations.append(target)
            index = len(locations) - 1
            by_key[name_key(result.mention)] = index
        target = locations[index]
        update = {"gis": result}
        if defensible and not protected and target.resolution.value not in PROTECTED:
            update |= {
                "resolution": LocationClass.GIS_RESOLVED,
                "geometry": _GEOMETRY.validate_python(result.chosen.geometry),
                "reference": ", ".join(result.chosen.osm_ids[:6]),
            }
        locations[index] = target.model_copy(update=update)
    detection["affected_locations"] = [loc.model_dump(mode="json") for loc in locations]


def resolve_event(session: Session, row: Event, engine: OsmGisEngine, *, now: datetime | None = None) -> dict:
    """Run the resolver on one event and record the outcome. Returns a short report."""
    now = now or utc_now()
    results = engine.resolve_request(build_request(row))
    detection = dict(row.detection or {})
    before_gis = detection.get("gis") or {}
    current_class = _location_class(detection)
    was_applied = bool(before_gis.get("applied"))
    if was_applied:
        # Judge precedence against the location GIS replaced, not its own proposal.
        current_class = (before_gis.get("previous") or {}).get("location_class") or "UNRESOLVED"
    protected = current_class in PROTECTED or before_gis.get("review_status") == "SUPERSEDED"

    primary = next(
        (r for r in results if r.applicable and r.mention.found_in in _PRIMARY_FIELDS), None
    )
    rejected_before = before_gis.get("review_status") == "REJECTED"
    previous_choice = next(
        ((r.get("chosen") or {}) for r in before_gis.get("results") or [] if r.get("applied")), {}
    )
    # A candidate a reviewer rejected is not proposed again.
    if rejected_before and primary is not None and list(primary.chosen.osm_ids) == (
        before_gis.get("rejected_osm_ids") or []
    ):
        primary = None
    apply = primary is not None and not protected

    models = [_model(r, applied=(apply and r is primary)) for r in results]
    reason = None
    if not apply:
        if protected:
            reason = f"the event already has a higher-precedence location ({current_class})"
        elif rejected_before and any(r.applicable for r in results):
            reason = "a reviewer rejected this GIS location before"
        elif any(r.applicable for r in results):
            reason = "the only defensible result is named in the article text, not its headline or summary"
        else:
            reason = "no unambiguous HIGH-confidence result"
    if apply:
        same_choice = was_applied and previous_choice.get("osm_ids") == list(primary.chosen.osm_ids)
        status = before_gis.get("review_status", "PENDING") if same_choice else "PENDING"
    elif before_gis.get("review_status") in ("REJECTED", "SUPERSEDED"):
        status = before_gis["review_status"]
    else:
        status = "NOT_APPLIED"
    gis = GisResolution(
        engine=ENGINE, network=engine.network.version, resolved_at=now, results=models,
        applied=apply, not_applied_reason=reason,
        review_status=status,
        reviewed_by=before_gis.get("reviewed_by"), reviewed_at=before_gis.get("reviewed_at"),
        review_reason=before_gis.get("review_reason"),
        previous=before_gis.get("previous") if was_applied else (
            {"geometry": row.geometry, "location": detection.get("location"), "location_class": current_class,
             "affected_locations": detection.get("affected_locations") or []}
            if apply else before_gis.get("previous")
        ),
    ).model_dump(mode="json")  # fmt: skip
    if rejected_before:
        gis["rejected_osm_ids"] = before_gis.get("rejected_osm_ids")

    if _comparable(before_gis) == _comparable(gis):
        return {"event_id": row.event_id, "changed": False, "applied": apply, "results": models}

    if was_applied and not apply:
        # The proposal no longer stands: put the location back as it was.
        previous = before_gis.get("previous") or {}
        row.geometry = previous.get("geometry")
        detection["location"] = previous.get("location")
        detection["location_class"] = previous.get("location_class")
        detection["affected_locations"] = previous.get("affected_locations") or []
    if apply:
        if was_applied:
            detection["affected_locations"] = (before_gis.get("previous") or {}).get("affected_locations") or []
        _apply_location(detection, row, next(m for m in models if m.applied), engine.network.version)
    _update_affected(detection, models, protected=protected or not apply)
    detection["gis"] = gis
    row.detection = detection
    row.version += 1
    row.updated_at = now
    summary = "; ".join(
        f"“{m.mention}”: {m.confidence}{' (ambiguous)' if m.ambiguous else ''}"
        + (f" {m.chosen.method} {m.chosen.matched_name}" if m.chosen else "")
        for m in models
    ) or "nothing to resolve"
    EventRepository(session).record_version(
        row,
        change_reason=(
            f"GIS resolution ({engine.network.version}): {summary}. "
            + ("Proposed as the event's location; awaiting review." if apply else f"Not applied: {reason}.")
        ),
        changed_by=ACTOR,
    )
    return {"event_id": row.event_id, "changed": True, "applied": apply, "results": models}


# --- the reviewer's decisions ----------------------------------------------------------------


def _event(session: Session, event_id: str) -> Event:
    row = EventRepository(session).get(event_id)
    if row is None:
        raise LookupError(event_id)
    return row


def _record(session: Session, row: Event, detection: dict, reason: str, reviewer: str) -> Event:
    row.detection = detection
    row.version += 1
    row.updated_at = utc_now()
    EventRepository(session).record_version(row, change_reason=reason, changed_by=reviewer)
    session.commit()
    return row


def approve(session: Session, event_id: str, *, reviewer: str, reason: str) -> Event:
    row = _event(session, event_id)
    detection = dict(row.detection or {})
    gis = dict(detection.get("gis") or {})
    if not gis.get("applied") or gis.get("review_status") != "PENDING":
        raise GisActionRefused("There is no GIS location awaiting review on this event.")
    gis |= {"review_status": "APPROVED", "reviewed_by": reviewer, "reviewed_at": utc_now().isoformat(), "review_reason": reason}
    detection["gis"] = gis
    return _record(session, row, detection, f"GIS location approved by a reviewer: {reason}", reviewer)


def reject(session: Session, event_id: str, *, reviewer: str, reason: str) -> Event:
    row = _event(session, event_id)
    detection = dict(row.detection or {})
    gis = dict(detection.get("gis") or {})
    if not gis.get("applied"):
        raise GisActionRefused("There is no GIS location on this event to reject.")
    previous = gis.get("previous") or {}
    row.geometry = previous.get("geometry")
    detection["location"] = previous.get("location")
    detection["location_class"] = previous.get("location_class")
    applied = next((r for r in gis.get("results") or [] if r.get("applied")), {})
    restored = [AffectedLocation.model_validate(loc) for loc in previous.get("affected_locations") or []]
    by_key = {name_key(loc.name): i for i, loc in enumerate(restored)}
    for result in gis.get("results") or []:
        i = by_key.get(name_key(result["mention"]))
        if i is not None:
            restored[i] = restored[i].model_copy(update={"gis": GisLocationResult.model_validate({**result, "applied": False})})
    detection["affected_locations"] = [loc.model_dump(mode="json") for loc in restored]
    gis |= {
        "applied": False, "review_status": "REJECTED", "reviewed_by": reviewer,
        "reviewed_at": utc_now().isoformat(), "review_reason": reason,
        "rejected_osm_ids": (applied.get("chosen") or {}).get("osm_ids"),
        "results": [{**r, "applied": False} for r in gis.get("results") or []],
    }  # fmt: skip
    detection["gis"] = gis
    return _record(session, row, detection, f"GIS location rejected by a reviewer; previous location restored: {reason}", reviewer)


def choose(
    session: Session, event_id: str, *, result_index: int, alternative_index: int | None, reviewer: str, reason: str
) -> Event:
    """A reviewer picks one candidate (e.g. of an ambiguous result) as the event's location."""
    row = _event(session, event_id)
    detection = dict(row.detection or {})
    gis = dict(detection.get("gis") or {})
    results = [GisLocationResult.model_validate(r) for r in gis.get("results") or []]
    if not 0 <= result_index < len(results):
        raise GisActionRefused("No such GIS result on this event.")
    current = _location_class(detection)
    if gis.get("applied"):
        current = (gis.get("previous") or {}).get("location_class") or "UNRESOLVED"
    if current in (LocationClass.SOURCE_PROVIDED.value,):
        raise GisActionRefused("The source provides this event's geometry; it is not replaced.")
    result = results[result_index]
    pool = [result.chosen] if alternative_index is None else result.alternatives
    index = 0 if alternative_index is None else alternative_index
    if not pool or not 0 <= index < len(pool) or pool[index] is None:
        raise GisActionRefused("No such candidate.")
    picked = result.model_copy(update={"chosen": pool[index], "ambiguous": False, "applied": True})
    if not gis.get("applied"):
        gis["previous"] = {
            "geometry": row.geometry, "location": detection.get("location"),
            "location_class": _location_class(detection), "affected_locations": detection.get("affected_locations") or [],
        }  # fmt: skip
    _apply_location(detection, row, picked, gis.get("network") or "OpenStreetMap", MatchMethod.REVIEWER_CONFIRMED.value)
    results = [r.model_copy(update={"applied": False}) for r in results]
    results[result_index] = picked
    gis |= {
        "applied": True, "results": [r.model_dump(mode="json") for r in results], "review_status": "APPROVED",
        "reviewed_by": reviewer, "reviewed_at": utc_now().isoformat(), "review_reason": reason,
        "not_applied_reason": None,
    }  # fmt: skip
    detection["gis"] = gis
    _update_affected(detection, [picked], protected=False)
    return _record(session, row, detection, f"A reviewer chose “{pool[index].matched_name}” as the location: {reason}", reviewer)


def supersede_on_correction(detection: dict) -> dict:
    """A reviewer placed the event themselves: a GIS proposal no longer applies."""
    gis = detection.get("gis")
    if gis and gis.get("applied"):
        detection["gis"] = {**gis, "applied": False, "review_status": "SUPERSEDED"}
    elif gis:
        detection["gis"] = {**gis, "review_status": "SUPERSEDED"}
    return detection


def cities_with_network() -> list[str]:
    return ["hyderabad"]


def get_network_city(row: Event) -> City | None:
    city = city_of(row)
    return city if city and city.id in cities_with_network() else None


__all__ = [
    "ACTOR", "GisActionRefused", "GisNotAvailable", "JunctionNotFound", "approve", "build_request",
    "choose", "decide_junction", "engine_for", "get_city", "junction_refs", "propose_junction",
    "reject", "resolve_event", "supersede_on_correction",
]  # fmt: skip
