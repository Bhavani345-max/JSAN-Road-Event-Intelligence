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
/** One building: footprint corner (x, z), size (w, d) and height. */
export type Building = { x: number; z: number; w: number; d: number; h: number };
/** Event types drawn as map pins; the names match the console's event types. */
export type SceneEventType = "EMERGENCY_ROAD_CLOSURE" | "ROAD_CONSTRUCTION" | "TRAFFIC_DIVERSION" | "MARATHON";
/** A map pin: where it stands and the deck height under it (0 = at grade). */
export type SceneEvent = { type: SceneEventType; point: Point; lift: number };

export type RoadNetwork = {
  /** Side length of the square the network covers, centred on the origin. */
  size: number;
  /** Long glowing routes (ring road, avenues, one diagonal). */
  arterials: Polyline[];
  /** Carriageway half width of each arterial: main avenues are wider than secondary ones. */
  arterialHalfWidths: number[];
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
  /** A calm canal crossing the city; blocks are cleared along it. */
  river: Polyline;
  /** Green park blocks (removed from `blocks`). */
  parks: Block[];
  /** Taller glass towers (removed from `blocks`). */
  towers: Block[];
  /** Street trees along the avenues and in parks. */
  trees: Point[];
  /** Zebra crossings: position plus the avenue heading in radians. */
  crossings: { point: Point; angle: number }[];
  /** Road-works stretch on the first avenue (a short sub-polyline). */
  works: Polyline;
  /** Lane-restriction spot on the ring road, with the road heading. */
  laneRestriction: { point: Point; angle: number };
  /** Buildings on the remaining blocks: one to four per block, clear of roads and decks. */
  buildings: Building[];
  /** Map pins, one per event type. */
  events: SceneEvent[];
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

function nearestIndexOnPolyline(line: Polyline, target: Point): number {
  let best = 0;
  let bestDistance = Number.POSITIVE_INFINITY;
  line.forEach((point, index) => {
    const distance = Math.hypot(point.x - target.x, point.z - target.z);
    if (distance < bestDistance) {
      bestDistance = distance;
      best = index;
    }
  });
  return best;
}

/** Heading (radians, about +y) of the polyline at `index`, from its neighbours. */
export function headingAt(line: Polyline, index: number): number {
  const previous = line[Math.max(0, index - 1)];
  const next = line[Math.min(line.length - 1, index + 1)];
  return Math.atan2(-(next.z - previous.z), next.x - previous.x);
}

/** Distance from a point to the nearest vertex of a polyline. */
export function distanceToPolyline(line: Polyline, target: Point): number {
  let best = Number.POSITIVE_INFINITY;
  for (const point of line) best = Math.min(best, Math.hypot(point.x - target.x, point.z - target.z));
  return best;
}

/** Exact distance from a point to a polyline (to its segments, not only its vertices). */
export function distanceToSegments(line: Polyline, target: Point): number {
  let best = Number.POSITIVE_INFINITY;
  for (let index = 1; index < line.length; index += 1) {
    const from = line[index - 1];
    const dx = line[index].x - from.x;
    const dz = line[index].z - from.z;
    const t = Math.max(0, Math.min(1, ((target.x - from.x) * dx + (target.z - from.z) * dz) / (dx * dx + dz * dz || 1)));
    best = Math.min(best, Math.hypot(target.x - (from.x + dx * t), target.z - (from.z + dz * t)));
  }
  return best;
}

/** Deck height of an elevated road at the vertex nearest to `target`. */
export function deckHeightAt(road: ElevatedRoad, target: Point): number {
  return road.heights[nearestIndexOnPolyline(road.line, target)];
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

  // A canal runs diagonally from the far left to the near right, under the
  // flyover and the viaduct. Blocks along it are cleared.
  const river: Polyline = [];
  for (let t = 0; t <= 1; t += 1 / 40) {
    river.push({ x: -60 + 120 * t + Math.sin(t * 7) * 2.5, z: -70 + 80 * t + Math.cos(t * 5) * 2 });
  }
  const builtBlocks = blocks.filter((block) => distanceToPolyline(river, { x: block.x + block.w / 2, z: block.z + block.d / 2 }) > 5.2);

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

  // The first two east-west avenues, the central north-south avenue and the
  // ring road are main roads; the others are narrower secondary avenues.
  const arterialHalfWidths = arterials.map((_, index) => ([0, 1, 4, 7].includes(index) ? 1.3 : 0.85));

  // A footprint is clear when its centre and corners keep off the avenues
  // (carriageway, kerb and a verge for street trees) and off the decks.
  const isClear = (x: number, z: number, w: number, d: number) => {
    const probes = [
      { x: x + w / 2, z: z + d / 2 },
      { x, z },
      { x: x + w, z },
      { x, z: z + d },
      { x: x + w, z: z + d },
    ];
    return probes.every(
      (probe) =>
        arterials.every((line, index) => distanceToSegments(line, probe) > arterialHalfWidths[index] + 1.3) &&
        elevated.every((road) => distanceToSegments(road.line, probe) > road.width / 2 + 0.8),
    );
  };

  // Parks and glass towers are picked from the built blocks deterministically.
  // Towers stand behind the centre so they read as a skyline.
  const parks: Block[] = [];
  const towers: Block[] = [];
  const remaining: Block[] = [];
  let towerCandidates = 0;
  builtBlocks.forEach((block, index) => {
    const cx = block.x + block.w / 2;
    const cz = block.z + block.d / 2;
    const nearFocus = Math.abs(cx - 2) < 14 && cz > -20 && cz < 0;
    const towerSite = !nearFocus && cz < -30 && Math.abs(cx) < 60 && isClear(block.x, block.z, block.w, block.d);
    if (!nearFocus && parks.length < 12 && index % 37 === 0 && block.density > 0.08) parks.push(block);
    else if (towerSite && towers.length < 22 && towerCandidates++ % 5 === 2) towers.push(block);
    else remaining.push(block);
  });
  blocks.length = 0;
  blocks.push(...remaining);

  // Buildings: every free plot of the grid (not only the blocks above) holds
  // one, two or four buildings of varied height, taller towards the centre and
  // sparser at the edges. A separate generator keeps the street grid above
  // unchanged by this step.
  const lots = createRng(seed + 101);
  const buildings: Building[] = [];
  const gap = 0.2;
  const taken = new Set([...parks, ...towers].map((block) => `${block.x},${block.z}`));
  const plots: Block[] = [];
  for (let x = -half; x < half; x += spacing) {
    for (let z = -half; z < half; z += spacing) {
      const block = { x: x + 0.45, z: z + 0.45, w: spacing - 0.9, d: spacing - 0.9, density: 0 };
      if (taken.has(`${block.x},${block.z}`)) continue;
      if (distanceToPolyline(river, { x: x + spacing / 2, z: z + spacing / 2 }) <= 5.2) continue;
      if (lots() > keepProbability(x, z) + 0.12) continue;
      plots.push(block);
    }
  }
  for (const block of plots) {
    const pattern = lots();
    const parts: [number, number, number, number][] =
      pattern < 0.34
        ? [[block.x + 0.1, block.z + 0.1, block.w - 0.2, block.d - 0.2]]
        : pattern < 0.67
          ? lots() < 0.5
            ? [
                [block.x, block.z, block.w / 2 - gap / 2, block.d],
                [block.x + block.w / 2 + gap / 2, block.z, block.w / 2 - gap / 2, block.d],
              ]
            : [
                [block.x, block.z, block.w, block.d / 2 - gap / 2],
                [block.x, block.z + block.d / 2 + gap / 2, block.w, block.d / 2 - gap / 2],
              ]
          : [
              [block.x, block.z, block.w / 2 - gap / 2, block.d / 2 - gap / 2],
              [block.x + block.w / 2 + gap / 2, block.z, block.w / 2 - gap / 2, block.d / 2 - gap / 2],
              [block.x, block.z + block.d / 2 + gap / 2, block.w / 2 - gap / 2, block.d / 2 - gap / 2],
              [block.x + block.w / 2 + gap / 2, block.z + block.d / 2 + gap / 2, block.w / 2 - gap / 2, block.d / 2 - gap / 2],
            ];
    const distance = Math.hypot(block.x + block.w / 2 - centre.x, block.z + block.d / 2 - centre.z);
    const base = 1.1 + 2.8 * Math.exp(-distance / 40);
    for (const [x, z, w, d] of parts) {
      const roll = lots();
      const tall = lots() < 0.06 ? 2.1 : 1;
      if (roll < 0.05) continue;
      const h = Math.min(7.5, base * (0.5 + roll) * tall);
      if (isClear(x, z, w, d)) {
        buildings.push({ x, z, w, d, h });
        continue;
      }
      // Too close to a road as a whole: keep the quarters that fit, lower.
      const qw = w / 2 - gap / 2;
      const qd = d / 2 - gap / 2;
      if (qw < 0.6 || qd < 0.6) continue;
      for (const [qx, qz] of [[x, z], [x + qw + gap, z], [x, z + qd + gap], [x + qw + gap, z + qd + gap]]) {
        if (isClear(qx, qz, qw, qd)) buildings.push({ x: qx, z: qz, w: qw, d: qd, h: Math.max(0.9, h * 0.7) });
      }
    }
  }

  // Street trees on both verges of the avenues and the ring road, plus a few
  // in each park. Trees never stand inside a building or the canal.
  const insideBuilding = (point: Point) =>
    buildings.some((b) => point.x > b.x - 0.3 && point.x < b.x + b.w + 0.3 && point.z > b.z - 0.3 && point.z < b.z + b.d + 0.3);
  const trees: Point[] = [];
  for (const lineIndex of [0, 1, 2, 3, 4, 7]) {
    const line = arterials[lineIndex];
    const verge = arterialHalfWidths[lineIndex] + 0.9;
    const length = polylineLength(line);
    for (let distance = 2; distance < length; distance += 4.2) {
      const point = pointAlong(line, distance);
      const index = nearestIndexOnPolyline(line, point);
      const heading = headingAt(line, index);
      const nx = Math.sin(heading);
      const nz = Math.cos(heading);
      for (const side of [verge, -verge]) {
        const tree = { x: point.x + nx * side, z: point.z + nz * side };
        const onRoad = arterials.some((other, index) => distanceToSegments(other, tree) < arterialHalfWidths[index] + 0.8);
        const underDeck = elevated.some((road) => distanceToSegments(road.line, tree) < road.width / 2 + 0.5);
        if (distanceToPolyline(river, tree) > 4 && !onRoad && !underDeck && !insideBuilding(tree)) trees.push(tree);
      }
    }
  }
  // A promenade of trees along both banks of the canal.
  const riverLength = polylineLength(river);
  for (let distance = 1.5; distance < riverLength; distance += 3.4) {
    const point = pointAlong(river, distance);
    const heading = headingAt(river, nearestIndexOnPolyline(river, point));
    for (const side of [5, -5]) {
      const tree = { x: point.x + Math.sin(heading) * side, z: point.z + Math.cos(heading) * side };
      const onRoad = arterials.some((other, index) => distanceToSegments(other, tree) < arterialHalfWidths[index] + 0.8);
      const underDeck = elevated.some((road) => distanceToSegments(road.line, tree) < road.width / 2 + 0.5);
      if (!onRoad && !underDeck && !insideBuilding(tree)) trees.push(tree);
    }
  }
  for (const park of parks) {
    trees.push({ x: park.x + park.w * 0.3, z: park.z + park.d * 0.3 });
    trees.push({ x: park.x + park.w * 0.7, z: park.z + park.d * 0.4 });
    trees.push({ x: park.x + park.w * 0.5, z: park.z + park.d * 0.75 });
  }

  // Events. The closure sits on the first avenue, slightly right of the
  // camera axis, where the hero composition has room for it.
  const closureA = nearestPointOnPolyline(arterials[0], { x: 1, z: -8 });
  const closures = [closureA];

  // Road works: a short stretch on the near side of the ring road, in front of
  // the closure. It stays in the open, away from the viaduct (whose deck would
  // hide its pin) and away from the sign-in card on the right.
  const worksStart = nearestIndexOnPolyline(ring, { x: 5.5, z: 0 });
  const worksEnd = nearestIndexOnPolyline(ring, { x: 0.5, z: 0 });
  const works = ring.slice(Math.min(worksStart, worksEnd), Math.max(worksStart, worksEnd) + 1);

  // Lane restriction on the ring road, in the far mid-band.
  const laneIndex = nearestIndexOnPolyline(ring, { x: 8, z: -48 });
  const laneRestriction = { point: ring[laneIndex], angle: headingAt(ring, laneIndex) };

  // Zebra crossings where minor streets meet the first two avenues.
  const crossings = [
    { x: -24, z: -8 },
    { x: 20, z: -8 },
    { x: -4, z: -22 },
  ].map((target) => {
    const lineIndex = target.z === -8 ? 0 : 1;
    const index = nearestIndexOnPolyline(arterials[lineIndex], target);
    return { point: arterials[lineIndex][index], angle: headingAt(arterials[lineIndex], index) };
  });

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

  // Secondary markers are no longer drawn; the field is kept for the scene API.
  const markers: Point[] = [];

  // Map pins: closure, works, diversion and a marathon on the flyover, all in
  // the open band between the hero copy and the sign-in card.
  const worksMid = works[Math.floor(works.length / 2)];
  const marathonSpot = nearestPointOnPolyline(flyoverLine, { x: 5, z: -18 });
  const events: SceneEvent[] = [
    { type: "EMERGENCY_ROAD_CLOSURE", point: closureA, lift: 0 },
    { type: "ROAD_CONSTRUCTION", point: worksMid, lift: 0 },
    { type: "TRAFFIC_DIVERSION", point: { x: (detour[1].x + detour[2].x) / 2, z: detour[1].z }, lift: 0 },
    { type: "MARATHON", point: marathonSpot, lift: deckHeightAt(elevated[0], marathonSpot) },
  ];

  return { size, arterials, arterialHalfWidths, streets, blocks, closures, detour, markers, elevated, river, parks, towers, trees, crossings, works, laneRestriction, buildings, events };
}
