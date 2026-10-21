/**
 * Procedural, deterministic road network used by the sign-in scene.
 *
 * Everything here is pure geometry in world units (x to the right, z towards
 * the viewer, y up). The scene is purely decorative: it is NOT a map of any
 * real place and carries no data from the product.
 */

export type Point = { x: number; z: number };
export type Polyline = Point[];
export type Segment = [Point, Point];
export type Block = { x: number; z: number; w: number; d: number; density: number };
/** An elevated carriageway: a polyline with a deck height per point (0 = at grade). */
export type ElevatedRoad = { name: string; line: Polyline; heights: number[]; width: number };

export type RoadNetwork = {
  /** Side length of the square the network covers, centred on the origin. */
  size: number;
  /** Long glowing routes (ring road, avenues, one diagonal). */
  arterials: Polyline[];
  /** Short straight minor-street segments on a jittered grid. */
  streets: Segment[];
  /** Faint block footprints between streets. */
  blocks: Block[];
  /** Road-event beacons (closures) placed on arterials. */
  closures: Point[];
  /** Highlighted detour route around the first closure, following the grid. */
  detour: Polyline;
  /** Smaller event markers placed on arterials. */
  markers: Point[];
  /** Elevated roads: a flyover, a higher viaduct crossing it, and a branch ramp. */
  elevated: ElevatedRoad[];
};

/** mulberry32: tiny seeded PRNG returning floats in [0, 1). */
export function createRng(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function polylineLength(line: Polyline): number {
  let total = 0;
  for (let index = 1; index < line.length; index += 1) {
    total += Math.hypot(line[index].x - line[index - 1].x, line[index].z - line[index - 1].z);
  }
  return total;
}

/** Point at `distance` along the polyline (clamped to its ends). */
export function pointAlong(line: Polyline, distance: number): Point {
  if (distance <= 0) return line[0];
  let travelled = 0;
  for (let index = 1; index < line.length; index += 1) {
    const from = line[index - 1];
    const to = line[index];
    const length = Math.hypot(to.x - from.x, to.z - from.z);
    if (travelled + length >= distance) {
      const t = length === 0 ? 0 : (distance - travelled) / length;
      return { x: from.x + (to.x - from.x) * t, z: from.z + (to.z - from.z) * t };
    }
    travelled += length;
  }
  return line[line.length - 1];
}

function nearestPointOnPolyline(line: Polyline, target: Point): Point {
  let best = line[0];
  let bestDistance = Number.POSITIVE_INFINITY;
  for (const point of line) {
    const distance = Math.hypot(point.x - target.x, point.z - target.z);
    if (distance < bestDistance) {
      bestDistance = distance;
      best = point;
    }
  }
  return best;
}

function smoothstep(edge0: number, edge1: number, value: number): number {
  const t = Math.min(1, Math.max(0, (value - edge0) / (edge1 - edge0)));
  return t * t * (3 - 2 * t);
}

/** Deck heights that ramp up over the first `rise` and down over the last `fall` fraction. */
function elevationProfile(count: number, top: number, rise: number, fall: number): number[] {
  const heights: number[] = [];
  for (let index = 0; index < count; index += 1) {
    const t = index / (count - 1);
    heights.push(top * smoothstep(0, rise, t) * smoothstep(1, 1 - fall, t));
  }
  return heights;
}

function wavyAvenue(
  axis: "x" | "z",
  offset: number,
  half: number,
  amplitude: number,
  frequency: number,
  phase: number,
): Polyline {
  const points: Polyline = [];
  for (let along = -half; along <= half; along += 2.5) {
    const wobble = Math.sin(along * frequency + phase) * amplitude;
    points.push(axis === "x" ? { x: along, z: offset + wobble } : { x: offset + wobble, z: along });
  }
  return points;
}

export function generateRoadNetwork(seed = 7, size = 160): RoadNetwork {
  const random = createRng(seed);
  const half = size / 2;

  // Arterials: three east-west avenues, four north-south avenues, a ring road
  // and one long diagonal. Offsets are chosen so the interesting part sits in
  // front of the camera (z between about +8 and -70).
  const arterials: Polyline[] = [
    wavyAvenue("x", -8, half, 1.6, 0.045, 0.6),
    wavyAvenue("x", -22, half, 2.2, 0.035, 2.1),
    wavyAvenue("x", -44, half, 1.4, 0.05, 4.0),
    wavyAvenue("z", -16, half, 1.8, 0.04, 1.2),
    wavyAvenue("z", 6, half, 1.2, 0.05, 3.3),
    wavyAvenue("z", 28, half, 2.0, 0.038, 0.2),
    wavyAvenue("z", -42, half, 1.5, 0.042, 2.6),
  ];

  const ring: Polyline = [];
  for (let step = 0; step <= 110; step += 1) {
    const angle = (step / 110) * Math.PI * 2;
    ring.push({ x: Math.cos(angle) * 34 + 2, z: Math.sin(angle) * 24 - 24 });
  }
  arterials.push(ring);

  const diagonal: Polyline = [];
  for (let t = 0; t <= 1; t += 1 / 48) {
    diagonal.push({ x: -78 + 150 * t, z: 36 - 112 * t + Math.sin(t * 9) * 1.5 });
  }
  arterials.push(diagonal);

  // Minor streets: a regular grid with organic drop-outs. Streets near the
  // city centre (around the ring road) are denser than at the edges.
  const spacing = 4;
  const streets: Segment[] = [];
  const blocks: Block[] = [];
  const centre = { x: 2, z: -24 };
  const keepProbability = (x: number, z: number) => {
    const distance = Math.hypot((x - centre.x) / 1.15, z - centre.z);
    return 0.95 - Math.min(0.55, distance / 110);
  };

  for (let x = -half; x <= half; x += spacing) {
    for (let z = -half; z < half; z += spacing) {
      if (random() < keepProbability(x, z)) streets.push([{ x, z }, { x, z: z + spacing }]);
    }
  }
  for (let z = -half; z <= half; z += spacing) {
    for (let x = -half; x < half; x += spacing) {
      if (random() < keepProbability(x, z)) streets.push([{ x, z }, { x: x + spacing, z }]);
    }
  }
  for (let x = -half; x < half; x += spacing) {
    for (let z = -half; z < half; z += spacing) {
      const roll = random();
      if (roll > 0.62) continue;
      const density = Math.max(0, keepProbability(x, z) - 0.4) * (0.4 + random() * 0.6);
      blocks.push({ x: x + 0.45, z: z + 0.45, w: spacing - 0.9, d: spacing - 0.9, density });
    }
  }

  // Events. The main closure sits on the first avenue, slightly right of the
  // camera axis, where the hero composition has room for it.
  const closureA = nearestPointOnPolyline(arterials[0], { x: 1, z: -8 });
  const closureB = nearestPointOnPolyline(diagonal, { x: 14, z: -33 });
  const closures = [closureA, closureB];

  // Detour: leave the avenue two blocks before the closure, go one block
  // north, pass the closure and come back. Snapped to the minor grid.
  const snap = (value: number) => Math.round(value / spacing) * spacing;
  const detourZ = snap(closureA.z) - spacing * 2;
  const detour: Polyline = [
    { x: snap(closureA.x) - spacing * 2, z: closureA.z },
    { x: snap(closureA.x) - spacing * 2, z: detourZ },
    { x: snap(closureA.x) + spacing * 2, z: detourZ },
    { x: snap(closureA.x) + spacing * 2, z: closureA.z },
  ];

  const markers: Point[] = [
    pointAlong(ring, polylineLength(ring) * 0.18),
    pointAlong(ring, polylineLength(ring) * 0.71),
    pointAlong(arterials[1], polylineLength(arterials[1]) * 0.62),
    pointAlong(arterials[3], polylineLength(arterials[3]) * 0.36),
    pointAlong(arterials[5], polylineLength(arterials[5]) * 0.3),
    pointAlong(arterials[2], polylineLength(arterials[2]) * 0.48),
  ];

  // Elevated structures. The flyover sweeps diagonally across the view, the
  // viaduct crosses above it on the right, and a branch ramp leaves the
  // flyover and descends to the first avenue.
  const flyoverLine: Polyline = [];
  for (let x = -80; x <= 80; x += 4) {
    flyoverLine.push({ x, z: -20 - x * 0.36 + Math.sin(x * 0.035 + 0.8) * 5 });
  }
  const viaductLine: Polyline = [];
  for (let z = -80; z <= 12; z += 4) {
    viaductLine.push({ x: 12 + Math.sin(z * 0.04) * 3, z });
  }
  // The ramp leaves the flyover near the centre and descends away from the
  // viewer to join the second avenue.
  const rampStart = nearestPointOnPolyline(flyoverLine, { x: -4, z: -18 });
  const rampLine: Polyline = [
    rampStart,
    { x: rampStart.x + 3, z: rampStart.z - 8 },
    { x: rampStart.x + 5, z: rampStart.z - 16 },
    { x: rampStart.x + 6, z: rampStart.z - 24 },
    { x: rampStart.x + 6, z: rampStart.z - 31 },
  ];
  const elevated: ElevatedRoad[] = [
    { name: "flyover", line: flyoverLine, heights: elevationProfile(flyoverLine.length, 4.6, 0.22, 0.22), width: 5.2 },
    { name: "viaduct", line: viaductLine, heights: elevationProfile(viaductLine.length, 8.2, 0.26, 0.3), width: 4.2 },
    { name: "ramp", line: rampLine, heights: [4.6, 4.3, 3.1, 1.4, 0.05], width: 3.4 },
  ];

  return { size, arterials, streets, blocks, closures, detour, markers, elevated };
}
