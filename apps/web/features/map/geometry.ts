import type { EventGeometry, Position } from "@/features/events/model";

export type BoundingBox = [west: number, south: number, east: number, north: number];

function flattenPositions(geometry: EventGeometry): Position[] {
  switch (geometry.type) {
    case "Point":
      return [geometry.coordinates];
    case "LineString":
      return geometry.coordinates;
    case "Polygon":
    case "MultiLineString":
      return geometry.coordinates.flat();
    case "MultiPolygon":
      return geometry.coordinates.flat(2);
  }
}

export function getBoundingBox(geometry: EventGeometry): BoundingBox {
  const positions = flattenPositions(geometry);
  let west = Infinity;
  let south = Infinity;
  let east = -Infinity;
  let north = -Infinity;
  for (const [lng, lat] of positions) {
    west = Math.min(west, lng);
    south = Math.min(south, lat);
    east = Math.max(east, lng);
    north = Math.max(north, lat);
  }
  return [west, south, east, north];
}

/** Point half-way along a line, measured by length rather than vertex count. */
function lineMidpoint(line: Position[]): Position {
  const lengths: number[] = [];
  let total = 0;
  for (let i = 1; i < line.length; i++) {
    // Planar distance is accurate enough at city scale for picking a midpoint.
    const length = Math.hypot(line[i][0] - line[i - 1][0], line[i][1] - line[i - 1][1]);
    lengths.push(length);
    total += length;
  }
  let remaining = total / 2;
  for (let i = 0; i < lengths.length; i++) {
    if (remaining <= lengths[i] && lengths[i] > 0) {
      const t = remaining / lengths[i];
      return [
        line[i][0] + (line[i + 1][0] - line[i][0]) * t,
        line[i][1] + (line[i + 1][1] - line[i][1]) * t,
      ];
    }
    remaining -= lengths[i];
  }
  return line[0];
}

/** A single point that represents the geometry, used to anchor map markers. */
export function getRepresentativePoint(geometry: EventGeometry): Position {
  switch (geometry.type) {
    case "Point":
      return geometry.coordinates;
    case "LineString":
      return lineMidpoint(geometry.coordinates);
    case "Polygon":
      return ringCentre(geometry.coordinates[0]);
    case "MultiLineString":
      // The middle of the longest part, so the marker sits on the road.
      return lineMidpoint(longest(geometry.coordinates));
    case "MultiPolygon":
      return ringCentre(longest(geometry.coordinates.map((polygon) => polygon[0])));
  }
}

/** Mean of a ring's positions, skipping the closing vertex. */
function ringCentre(ring: Position[]): Position {
  const open = ring.slice(0, -1);
  const lng = open.reduce((sum, p) => sum + p[0], 0) / open.length;
  const lat = open.reduce((sum, p) => sum + p[1], 0) / open.length;
  return [lng, lat];
}

function longest(parts: Position[][]): Position[] {
  return parts.reduce((best, part) => (part.length > best.length ? part : best), parts[0]);
}
