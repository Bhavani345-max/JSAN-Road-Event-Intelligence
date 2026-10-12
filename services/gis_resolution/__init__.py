"""The GIS Resolution Engine: interface only (6 October 2026).

The engine will take the places an event names (junctions, roads) and find
them in a road network: the candidate road segments, the affected geometry,
and the direction where the evidence supports one. It is not built in this
phase. What is here is the contract it will meet, so that the event model,
the API and the console are ready for it:

    event + its affected locations
        -> engine.resolve(...)
        -> one ResolvedLocation per affected location
           (GIS_RESOLVED with a geometry and the segments used, or UNRESOLVED)
        -> human QC
        -> map

Rules the engine must keep, enforced by `apply_resolution`:

- Geometry a source provides (SOURCE_PROVIDED) is never replaced.
- A reviewer's correction (HUMAN_CORRECTED) and a QC-approved location are
  never replaced.
- A location the engine cannot resolve stays UNRESOLVED; nothing is guessed.
- Every result carries its evidence (segment ids, network version) and a
  confidence only if the engine actually computes one.

`NullGisEngine` is the stand-in until then: it resolves nothing.
"""

from dataclasses import dataclass, field
from typing import Protocol

from packages.event_schema import AffectedLocation, LocationClass, ReiEvent
from packages.geo_models import Geometry

# Locations the engine must leave as they are.
PROTECTED = {
    LocationClass.SOURCE_PROVIDED,
    LocationClass.HUMAN_CORRECTED,
    LocationClass.QC_APPROVED,
}


@dataclass(frozen=True)
class ResolvedLocation:
    """The engine's answer for one affected location."""

    name: str
    resolution: LocationClass  # GIS_RESOLVED or UNRESOLVED
    geometry: Geometry | None = None
    # The road-network segments the geometry was built from.
    segment_ids: tuple[str, ...] = ()
    # As the network or the source supports it; None when it does not.
    direction: str | None = None
    # Only when the engine computes one; never a default.
    confidence: float | None = None
    # The road network and its version, e.g. "OpenStreetMap 2026-10-06".
    network: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)


class GisResolutionEngine(Protocol):
    def resolve(self, event: ReiEvent, city_id: str) -> list[ResolvedLocation]:
        """One result per affected location of `event`, in the same order."""
        ...


class NullGisEngine:
    """The stand-in until a road-network engine exists: it resolves nothing."""

    def resolve(self, event: ReiEvent, city_id: str) -> list[ResolvedLocation]:
        locations = event.detection.affected_locations if event.detection else []
        return [
            ResolvedLocation(name=location.name, resolution=LocationClass.UNRESOLVED)
            for location in locations
        ]


def apply_resolution(
    locations: list[AffectedLocation], results: list[ResolvedLocation]
) -> list[AffectedLocation]:
    """The affected locations with the engine's results applied, under the rules above."""
    if len(locations) != len(results):
        raise ValueError("The engine must answer once for every affected location")
    applied: list[AffectedLocation] = []
    for location, result in zip(locations, results, strict=True):
        if location.resolution in PROTECTED or result.resolution is not LocationClass.GIS_RESOLVED:
            applied.append(location)
            continue
        if result.geometry is None:
            raise ValueError(f"{result.name}: GIS_RESOLVED needs a geometry")
        applied.append(
            location.model_copy(
                update={
                    "resolution": LocationClass.GIS_RESOLVED,
                    "geometry": result.geometry,
                    "direction": result.direction or location.direction,
                    "reference": result.network,
                }
            )
        )
    return applied


__all__ = [
    "GisResolutionEngine",
    "NullGisEngine",
    "PROTECTED",
    "ResolvedLocation",
    "apply_resolution",
]
