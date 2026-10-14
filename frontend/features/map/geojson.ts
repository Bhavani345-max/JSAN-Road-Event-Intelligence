import {
  isLocated,
  type EventGeometry,
  type PointGeometry,
  type RoadEvent,
} from "@/features/events/model";
import {
  formatEventPeriod,
  getEventTypeColor,
  getEventTypeLabel,
  getStatusMapStyle,
  isWholeDayPeriod,
  PLACE_ROLE_COLORS,
  PLACE_ROLE_LABELS,
  ROUTE_ROLES,
  timeZoneOf,
} from "@/features/events/presentation";

/** Properties the map layers style by. Kept flat for style expressions. */
export interface EventFeatureProperties {
  eventId: string;
  title: string;
  /**
   * What tells the event apart from others at its spot: its type, its stated
   * period and its source ("Planned road closure · 15 Sep 2026 → 15 Oct 2026 · …").
   */
  detail: string;
  color: string;
  dashed: boolean;
  opacity: number;
  selected: boolean;
  /** The marker is a named place's position, not the event's: drawn hollow. */
  approximate: boolean;
  /** How the location was obtained; styles the marker. */
  locationClass: string;
  /** A GIS candidate shown for review, not the event's location. */
  candidate: boolean;
  /**
   * Markers only: how many events have their marker at exactly this point
   * (1 when it is alone). Several reports naming the same place share its
   * position; none is moved, the marker says how many are there.
   */
  stackSize: number;
  /** Markers only: the one of a stack drawn on top and badged (the selected one, else the first). */
  stackTop: boolean;
}

export interface EventFeature<G extends EventGeometry = EventGeometry> {
  type: "Feature";
  geometry: G;
  properties: EventFeatureProperties;
}

export interface EventFeatureCollection<G extends EventGeometry = EventGeometry> {
  type: "FeatureCollection";
  features: EventFeature<G>[];
}

export interface EventMapData {
  /** Affected road geometry (Point / LineString / Polygon). */
  geometries: EventFeatureCollection;
  /** One marker point per event. */
  anchors: EventFeatureCollection<PointGeometry>;
  /** The selected event's named places, each by its role (closed, diversion route …). */
  places: PlaceFeatureCollection;
}

export interface PlaceFeatureProperties {
  eventId: string;
  title: string;
  name: string;
  role: string;
  /** "Necklace Road · closed or restricted" */
  label: string;
  color: string;
  /** Where traffic is sent, not where the event is. */
  route: boolean;
}

export interface PlaceFeatureCollection {
  type: "FeatureCollection";
  features: { type: "Feature"; geometry: PointGeometry; properties: PlaceFeatureProperties }[];
}

/**
 * The places an AI reading gave roles to, for the selected event: each at its
 * named place's position (OpenStreetMap), coloured by what it is to the event.
 * Places that could not be located are left out; nothing is made up.
 */
export function selectedEventPlaces(event: RoadEvent | undefined): PlaceFeatureCollection {
  const features: PlaceFeatureCollection["features"] = [];
  if (event) {
    const color = getEventTypeColor(event.eventType);
    for (const location of event.detection?.affectedLocations ?? []) {
      if (!location.role || location.geometry?.type !== "Point") continue;
      features.push({
        type: "Feature",
        geometry: location.geometry,
        properties: {
          eventId: event.id,
          title: event.title,
          name: location.name,
          role: location.role,
          label: `${location.name} · ${PLACE_ROLE_LABELS[location.role] ?? location.role}`,
          color: PLACE_ROLE_COLORS[location.role] ?? color,
          route: ROUTE_ROLES.includes(location.role),
        },
      });
    }
  }
  return { type: "FeatureCollection", features };
}

/**
 * Converts events into the GeoJSON the map renders. Events that have not
 * been located yet (GIS resolution pending) are left out: no geometry is
 * ever made up for them.
 */
export function toEventMapData(events: RoadEvent[], selectedEventId: string | null): EventMapData {
  const geometries: EventFeature[] = [];
  const anchors: EventFeature<PointGeometry>[] = [];

  for (const event of events) {
    if (!isLocated(event)) continue;
    const properties: EventFeatureProperties = {
      eventId: event.id,
      title: event.title,
      detail: describeForStack(event),
      color: getEventTypeColor(event.eventType),
      ...getStatusMapStyle(event.status),
      selected: event.id === selectedEventId,
      approximate: event.detection?.locationClass === "APPROXIMATE",
      locationClass: event.detection?.locationClass ?? "UNRESOLVED",
      candidate: false,
      stackSize: 1,
      stackTop: true,
    };
    geometries.push({ type: "Feature", geometry: event.geometry, properties });
    // The streets or segments an official source gives, drawn with the event.
    for (const location of event.detection?.affectedLocations ?? []) {
      if (
        location.geometry &&
        location.geometry.type !== "Point" &&
        location.resolution !== "APPROXIMATE" &&
        location.resolution !== "UNRESOLVED"
      ) {
        geometries.push({ type: "Feature", geometry: location.geometry, properties });
      }
      // A place resolved on the road network gets its own marker.
      if (location.geometry?.type === "Point" && location.resolution === "GIS_RESOLVED") {
        geometries.push({ type: "Feature", geometry: location.geometry, properties });
      }
    }
    // For the event under review, the GIS candidates not applied, drawn as candidates.
    if (event.id === selectedEventId && event.detection?.gis) {
      for (const result of event.detection.gis.results) {
        if (result.applied) continue;
        for (const candidate of [result.chosen, ...result.alternatives]) {
          if (candidate?.geometry) {
            geometries.push({
              type: "Feature",
              geometry: candidate.geometry,
              properties: { ...properties, color: "#64748b", dashed: true, candidate: true },
            });
          }
        }
      }
    }
    anchors.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: [event.longitude, event.latitude] },
      properties: { ...properties },
    });
  }

  return {
    geometries: { type: "FeatureCollection", features: geometries },
    anchors: { type: "FeatureCollection", features: stackAnchors(anchors) },
    places: selectedEventPlaces(events.find((event) => event.id === selectedEventId)),
  };
}

/** Type, stated period (in the event's city's zone) and source, joined for one line. */
export function describeForStack(event: RoadEvent): string {
  const parts = [getEventTypeLabel(event.eventType)];
  if (event.startTime || event.endTime) {
    const zone = timeZoneOf(event.city);
    const wholeDays = isWholeDayPeriod(event.startTime, event.endTime, zone);
    const { start, end } = formatEventPeriod(event.startTime, event.endTime, wholeDays, zone);
    parts.push(event.startTime ? `${start} → ${end}` : `until ${end}`);
  }
  parts.push(event.source.name);
  return parts.join(" · ");
}

/** Markers closer than this (about 10 cm) are at the same point. */
const SAME_POINT_DIGITS = 6;

function pointKey([lng, lat]: [number, number]): string {
  return `${lng.toFixed(SAME_POINT_DIGITS)},${lat.toFixed(SAME_POINT_DIGITS)}`;
}

/** Marks the markers that share a point: how many, and which is on top. */
export function stackAnchors(
  anchors: EventFeature<PointGeometry>[],
): EventFeature<PointGeometry>[] {
  const stacks = new Map<string, EventFeature<PointGeometry>[]>();
  for (const anchor of anchors) {
    const key = pointKey(anchor.geometry.coordinates as [number, number]);
    stacks.set(key, [...(stacks.get(key) ?? []), anchor]);
  }
  for (const stack of stacks.values()) {
    const top = stack.find((anchor) => anchor.properties.selected) ?? stack[0];
    for (const anchor of stack) {
      anchor.properties.stackSize = stack.length;
      anchor.properties.stackTop = anchor === top;
    }
  }
  return anchors;
}

/** An event under a click: enough to choose it from a list. */
export interface StackedEvent {
  id: string;
  title: string;
  detail: string;
}

/** One entry per event among features hit by a click, in the order given (top-most first). */
export function distinctEvents(
  features: { properties: Record<string, unknown> | null }[],
): StackedEvent[] {
  const seen = new Map<string, StackedEvent>();
  for (const feature of features) {
    const id = feature.properties?.eventId;
    if (id === undefined || id === null || seen.has(String(id))) continue;
    seen.set(String(id), {
      id: String(id),
      title: String(feature.properties?.title ?? ""),
      detail: String(feature.properties?.detail ?? ""),
    });
  }
  return [...seen.values()];
}
