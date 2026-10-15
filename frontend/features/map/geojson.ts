import {
  isLocated,
  type EventGeometry,
  type PointGeometry,
  type Position,
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
    const zone = timeZoneOf(event.city, event.source.id);
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

/** Ring radius, in screen pixels, of markers spread around the spot they share. */
const SPREAD_MIN_RADIUS_PX = 16;
const SPREAD_PX_PER_MARKER = 3.4;
const SPREAD_MAX_RADIUS_PX = 64;

/** Degrees of longitude one screen pixel covers at `zoom` (MapLibre's 512-pixel tiles). */
function degreesPerPixel(zoom: number): number {
  return 360 / (512 * 2 ** zoom);
}

export interface LeaderFeature {
  type: "Feature";
  geometry: { type: "LineString"; coordinates: Position[] };
  properties: { eventId: string; color: string; selected: boolean };
}

export interface SpreadMarkers {
  /** Every marker; those sharing a spot moved onto a ring around it, for display only. */
  anchors: EventFeatureCollection<PointGeometry>;
  /** A thin line from each moved marker back to the spot it shares. */
  leaders: { type: "FeatureCollection"; features: LeaderFeature[] };
}

/**
 * Gives each of several events at one spot its own marker: spread on a ring
 * around the spot, the same number of pixels across at every zoom, each with
 * a line pointing back to the spot. Only what is drawn moves; the events,
 * their geometry and the spot itself are unchanged, and a marker alone at
 * its spot stays exactly there.
 */
export function spreadStacks(
  anchors: EventFeatureCollection<PointGeometry>,
  zoom: number,
): SpreadMarkers {
  const stacks = new Map<string, EventFeature<PointGeometry>[]>();
  for (const anchor of anchors.features) {
    const key = pointKey(anchor.geometry.coordinates as [number, number]);
    stacks.set(key, [...(stacks.get(key) ?? []), anchor]);
  }
  const spread: EventFeature<PointGeometry>[] = [];
  const leaders: LeaderFeature[] = [];
  const step = degreesPerPixel(zoom);
  for (const stack of stacks.values()) {
    if (stack.length === 1) {
      spread.push(stack[0]);
      continue;
    }
    const [lng, lat] = stack[0].geometry.coordinates;
    const radius = Math.min(
      SPREAD_MAX_RADIUS_PX,
      Math.max(SPREAD_MIN_RADIUS_PX, stack.length * SPREAD_PX_PER_MARKER),
    );
    // On Web Mercator a degree of latitude is drawn longer by 1 / cos(latitude).
    const latStep = step * Math.cos((lat * Math.PI) / 180);
    stack.forEach((anchor, index) => {
      // Clockwise from the top, evenly spaced.
      const angle = (2 * Math.PI * index) / stack.length;
      const position: Position = [
        lng + radius * Math.sin(angle) * step,
        lat + radius * Math.cos(angle) * latStep,
      ];
      spread.push({ ...anchor, geometry: { type: "Point", coordinates: position } });
      leaders.push({
        type: "Feature",
        geometry: { type: "LineString", coordinates: [position, [lng, lat]] },
        properties: {
          eventId: anchor.properties.eventId,
          color: anchor.properties.color,
          selected: anchor.properties.selected,
        },
      });
    });
  }
  return {
    anchors: { type: "FeatureCollection", features: spread },
    leaders: { type: "FeatureCollection", features: leaders },
  };
}

/**
 * Up to this zoom, markers near each other are drawn as one numbered circle
 * (MapLibre clustering); zooming in splits it.
 */
export const CLUSTER_MAX_ZOOM = 13;
/** From this zoom, markers sharing an exact spot are spread around it. */
export const SPREAD_FROM_ZOOM = CLUSTER_MAX_ZOOM + 1;

/**
 * The markers to draw at `zoom`: as they are while clusters gather them, and
 * spread around a shared spot once zoomed in past clustering. Zoomed out, a
 * ring of lines would only clutter the map; there a numbered circle says how
 * many events are there.
 */
export function markersAtZoom(
  anchors: EventFeatureCollection<PointGeometry>,
  zoom: number,
): SpreadMarkers {
  if (zoom < SPREAD_FROM_ZOOM) {
    return { anchors, leaders: { type: "FeatureCollection", features: [] } };
  }
  return spreadStacks(anchors, zoom);
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
