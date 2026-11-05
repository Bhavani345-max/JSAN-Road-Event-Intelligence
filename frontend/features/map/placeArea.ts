/**
 * Which events are in a place found with "Find place" (decision 0056).
 *
 * A place counts as an area only when OpenStreetMap gives it one: a suburb's
 * box (Gachibowli: about 4.4 × 4.2 km). A postcode has no boundary in OSM (its
 * box is an estimate around a point: 10 × 10 km for PIN 500032), and a street
 * comes back as one short piece of it, so for those, and for every place in
 * REI's own place lists (points), "in the place" is a distance from its point,
 * which the user can change. Nothing is made up: the area or the distance is
 * drawn on the map and named in the summary.
 */

import { isLocated, type EventGeometry, type Position, type RoadEvent } from "@/features/events/model";
import type { BoundingBox } from "./geometry";
import type { FoundPlace } from "./placeSearch";

/** The place's own area (its OSM box), or a distance from its point in metres. */
export type PlaceRange = "area" | 500 | 1000 | 2000 | 5000;

export const PLACE_RADII = [500, 1000, 2000, 5000] as const satisfies readonly PlaceRange[];

/** An OSM box this long or longer is the place's area; a shorter one (a building, a street piece) is not. */
const MIN_AREA_SIDE_M = 500;

/** Kinds of place that cover a neighbourhood rather than a spot: a wider default distance. */
const WIDE_KINDS = new Set([
  "postcode", "area", "ward", "suburb", "neighbourhood", "quarter", "locality",
  "village", "town", "city", "city_district", "district", "borough", "municipality",
]);

const METRES_PER_DEGREE_LAT = 110_574;
const METRES_PER_DEGREE_LNG_AT_EQUATOR = 111_320;
const CIRCLE_STEPS = 64;

function metresPerDegreeLng(latitude: number): number {
  return METRES_PER_DEGREE_LNG_AT_EQUATOR * Math.cos((latitude * Math.PI) / 180);
}

/** Whether OpenStreetMap gives the place an area of its own (not a postcode's estimate). */
export function hasOwnArea(place: FoundPlace): boolean {
  if (!place.box || place.kind === "postcode") return false;
  const [west, south, east, north] = place.box;
  const width = (east - west) * metresPerDegreeLng((south + north) / 2);
  const height = (north - south) * METRES_PER_DEGREE_LAT;
  return Math.max(width, height) >= MIN_AREA_SIDE_M;
}

/** What a newly chosen place starts with: its own area if it has one, else a distance that suits its kind. */
export function defaultRange(place: FoundPlace): PlaceRange {
  if (hasOwnArea(place)) return "area";
  return WIDE_KINDS.has(place.kind.toLowerCase()) ? 2000 : 1000;
}

/** "500 m", "2 km". */
export function formatDistance(metres: number): string {
  return metres < 1000 ? `${metres} m` : `${metres / 1000} km`;
}

type Shape =
  | { kind: "box"; box: BoundingBox }
  | { kind: "circle"; center: Position; radius: number };

export interface PlaceArea {
  range: PlaceRange;
  center: Position;
  /** West, south, east, north: what the map frames. */
  bounds: BoundingBox;
  /** Drawn on the map: the box, or the circle of the chosen distance. */
  outline: { type: "Polygon"; coordinates: Position[][] };
  shape: Shape;
}

/** The area "in the place" covers for the chosen range. A place with no area of its own never gets "area". */
export function placeAreaOf(place: FoundPlace, range: PlaceRange): PlaceArea {
  const center: Position = [place.longitude, place.latitude];
  if (range === "area" && place.box && hasOwnArea(place)) {
    const [west, south, east, north] = place.box;
    return {
      range,
      center,
      bounds: [west, south, east, north],
      outline: {
        type: "Polygon",
        coordinates: [[[west, south], [east, south], [east, north], [west, north], [west, south]]],
      },
      shape: { kind: "box", box: [west, south, east, north] },
    };
  }
  const radius = range === "area" ? 1000 : range;
  const lngStep = radius / metresPerDegreeLng(place.latitude);
  const latStep = radius / METRES_PER_DEGREE_LAT;
  const ring: Position[] = [];
  for (let i = 0; i <= CIRCLE_STEPS; i++) {
    const angle = (2 * Math.PI * (i % CIRCLE_STEPS)) / CIRCLE_STEPS;
    ring.push([place.longitude + Math.cos(angle) * lngStep, place.latitude + Math.sin(angle) * latStep]);
  }
  return {
    range: radius as PlaceRange,
    center,
    bounds: [place.longitude - lngStep, place.latitude - latStep, place.longitude + lngStep, place.latitude + latStep],
    outline: { type: "Polygon", coordinates: [ring] },
    shape: { kind: "circle", center, radius },
  };
}

function pointHits(shape: Shape, [lng, lat]: Position): boolean {
  if (shape.kind === "box") {
    const [west, south, east, north] = shape.box;
    return lng >= west && lng <= east && lat >= south && lat <= north;
  }
  const [x, y] = toMetres(shape.center, [lng, lat]);
  return Math.hypot(x, y) <= shape.radius;
}

/** Position in metres east and north of `origin` (flat: accurate enough at city scale). */
function toMetres(origin: Position, [lng, lat]: Position): [number, number] {
  return [(lng - origin[0]) * metresPerDegreeLng(origin[1]), (lat - origin[1]) * METRES_PER_DEGREE_LAT];
}

/** Whether the segment from a to b passes through the shape (a road crossing it with no vertex inside counts). */
function segmentHits(shape: Shape, a: Position, b: Position): boolean {
  if (shape.kind === "circle") {
    const [ax, ay] = toMetres(shape.center, a);
    const [bx, by] = toMetres(shape.center, b);
    const dx = bx - ax;
    const dy = by - ay;
    const lengthSquared = dx * dx + dy * dy;
    const t = lengthSquared === 0 ? 0 : Math.max(0, Math.min(1, -(ax * dx + ay * dy) / lengthSquared));
    return Math.hypot(ax + t * dx, ay + t * dy) <= shape.radius;
  }
  // Liang–Barsky: clip the segment to the box; anything left means it crosses.
  const [west, south, east, north] = shape.box;
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const p = [-dx, dx, -dy, dy];
  const q = [a[0] - west, east - a[0], a[1] - south, north - a[1]];
  let enter = 0;
  let leave = 1;
  for (let i = 0; i < 4; i++) {
    if (p[i] === 0) {
      if (q[i] < 0) return false;
      continue;
    }
    const r = q[i] / p[i];
    if (p[i] < 0) {
      if (r > leave) return false;
      enter = Math.max(enter, r);
    } else {
      if (r < enter) return false;
      leave = Math.min(leave, r);
    }
  }
  return true;
}

function lineHits(shape: Shape, line: Position[]): boolean {
  if (line.length === 1) return pointHits(shape, line[0]);
  for (let i = 1; i < line.length; i++) {
    if (segmentHits(shape, line[i - 1], line[i])) return true;
  }
  return false;
}

/** Ray casting over every ring, so a hole leaves its inside out. */
function insidePolygon([lng, lat]: Position, rings: Position[][]): boolean {
  let inside = false;
  for (const ring of rings) {
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i];
      const [xj, yj] = ring[j];
      if (yi > lat !== yj > lat && lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
    }
  }
  return inside;
}

function shapeCentre(shape: Shape): Position {
  if (shape.kind === "circle") return shape.center;
  const [west, south, east, north] = shape.box;
  return [(west + east) / 2, (south + north) / 2];
}

/** A polygon is in the place where an edge crosses it, or where it covers the place entirely. */
function polygonHits(shape: Shape, rings: Position[][]): boolean {
  return rings.some((ring) => lineHits(shape, ring)) || insidePolygon(shapeCentre(shape), rings);
}

export function geometryInArea(geometry: EventGeometry, area: PlaceArea): boolean {
  const { shape } = area;
  switch (geometry.type) {
    case "Point":
      return pointHits(shape, geometry.coordinates);
    case "LineString":
      return lineHits(shape, geometry.coordinates);
    case "MultiLineString":
      return geometry.coordinates.some((line) => lineHits(shape, line));
    case "Polygon":
      return polygonHits(shape, geometry.coordinates);
    case "MultiPolygon":
      return geometry.coordinates.some((polygon) => polygonHits(shape, polygon));
  }
}

/** The located events whose road geometry or map marker lies in the area. Unlocated events are never counted. */
export function eventsInArea(events: RoadEvent[], area: PlaceArea): Set<string> {
  const ids = new Set<string>();
  for (const event of events) {
    if (!isLocated(event)) continue;
    if (pointHits(area.shape, [event.longitude, event.latitude]) || geometryInArea(event.geometry, area)) {
      ids.add(event.id);
    }
  }
  return ids;
}

/** "4 events inside the outlined area", "No events within 1 km". */
export function describeCount(count: number, range: PlaceRange): string {
  const events = count === 0 ? "No events" : count === 1 ? "1 event" : `${count} events`;
  return range === "area" ? `${events} inside the outlined area` : `${events} within ${formatDistance(range)}`;
}
