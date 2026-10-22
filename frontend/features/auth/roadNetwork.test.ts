import { describe, expect, it } from "vitest";
import { loginEventColors } from "./loginTheme";
import { createRng, deckHeightAt, distanceToSegments, generateRoadNetwork, pointAlong, polylineLength } from "./roadNetwork";

describe("createRng", () => {
  it("is deterministic for a seed and stays within [0, 1)", () => {
    const first = createRng(42);
    const second = createRng(42);
    for (let index = 0; index < 50; index += 1) {
      const value = first();
      expect(value).toBe(second());
      expect(value).toBeGreaterThanOrEqual(0);
      expect(value).toBeLessThan(1);
    }
  });
});

describe("generateRoadNetwork", () => {
  const network = generateRoadNetwork(7, 160);

  it("produces the same network for the same seed", () => {
    expect(generateRoadNetwork(7, 160)).toEqual(network);
  });

  it("keeps every element inside the ground square", () => {
    const half = network.size / 2 + 0.01;
    const inside = (point: { x: number; z: number }) => Math.abs(point.x) <= half && Math.abs(point.z) <= half;
    expect(network.arterials.flat().every(inside)).toBe(true);
    expect(network.streets.flat().every(inside)).toBe(true);
    expect(network.closures.every(inside)).toBe(true);
    expect(network.markers.every(inside)).toBe(true);
    expect(network.detour.every(inside)).toBe(true);
    expect(network.elevated.flatMap((road) => road.line).every(inside)).toBe(true);
    expect(network.river.every(inside)).toBe(true);
    expect(network.trees.every(inside)).toBe(true);
    expect(network.works.every(inside)).toBe(true);
  });

  it("clears blocks along the canal and keeps parks and towers out of the built blocks", () => {
    const nearRiver = (block: { x: number; z: number; w: number; d: number }) =>
      network.river.some((point) => Math.hypot(point.x - (block.x + block.w / 2), point.z - (block.z + block.d / 2)) <= 5.2);
    expect(network.blocks.some(nearRiver)).toBe(false);
    expect(network.parks.length).toBeGreaterThan(3);
    expect(network.towers.length).toBeGreaterThan(3);
    for (const special of [...network.parks, ...network.towers]) {
      expect(network.blocks.includes(special)).toBe(false);
    }
    expect(network.works.length).toBeGreaterThanOrEqual(2);
    expect(network.crossings.length).toBe(3);
    expect(network.trees.length).toBeGreaterThan(40);
  });

  it("gives every elevated road one height per point, ramping from and to grade", () => {
    expect(network.elevated.map((road) => road.name)).toEqual(["flyover", "viaduct", "ramp"]);
    for (const road of network.elevated) {
      expect(road.heights.length).toBe(road.line.length);
      expect(Math.max(...road.heights)).toBeGreaterThan(3);
      expect(Math.min(...road.heights)).toBeLessThan(0.1);
    }
    const [flyover, viaduct] = network.elevated;
    expect(Math.max(...viaduct.heights)).toBeGreaterThan(Math.max(...flyover.heights) + 3);
  });

  it("places closures on arterials and routes the detour around the first one", () => {
    for (const closure of network.closures) {
      const onArterial = network.arterials.some((line) => line.some((point) => point.x === closure.x && point.z === closure.z));
      expect(onArterial).toBe(true);
    }
    const [closure] = network.closures;
    expect(network.detour[0].x).toBeLessThan(closure.x);
    expect(network.detour[network.detour.length - 1].x).toBeGreaterThan(closure.x);
    expect(network.detour.every((point) => point.z <= closure.z)).toBe(true);
  });

  it("keeps the road works out from under the elevated roads, so its pin stays visible", () => {
    const distanceToSegment = (point: { x: number; z: number }, from: { x: number; z: number }, to: { x: number; z: number }) => {
      const dx = to.x - from.x;
      const dz = to.z - from.z;
      const t = Math.max(0, Math.min(1, ((point.x - from.x) * dx + (point.z - from.z) * dz) / (dx * dx + dz * dz || 1)));
      return Math.hypot(point.x - (from.x + dx * t), point.z - (from.z + dz * t));
    };
    for (const road of network.elevated) {
      for (let index = 1; index < road.line.length; index += 1) {
        if (Math.min(road.heights[index - 1], road.heights[index]) < 0.5) continue;
        for (const point of network.works) {
          expect(distanceToSegment(point, road.line[index - 1], road.line[index])).toBeGreaterThan(road.width / 2 + 1.5);
        }
      }
    }
  });

  it("keeps every building off the avenues and from under the elevated decks", () => {
    expect(network.buildings.length).toBeGreaterThan(600);
    expect(network.arterialHalfWidths).toHaveLength(network.arterials.length);
    for (const building of network.buildings) {
      expect(building.h).toBeGreaterThan(0.5);
      expect(building.h).toBeLessThanOrEqual(7.5);
      const probes = [
        { x: building.x + building.w / 2, z: building.z + building.d / 2 },
        { x: building.x, z: building.z },
        { x: building.x + building.w, z: building.z + building.d },
      ];
      for (const probe of probes) {
        network.arterials.forEach((line, index) => {
          expect(distanceToSegments(line, probe)).toBeGreaterThan(network.arterialHalfWidths[index] + 1.3);
        });
        for (const road of network.elevated) {
          expect(distanceToSegments(road.line, probe)).toBeGreaterThan(road.width / 2 + 0.8);
        }
      }
    }
  });

  it("places one pin per event type, inside the city, on the ground or on a deck", () => {
    const half = network.size / 2;
    expect(network.events.map((event) => event.type).sort()).toEqual(Object.keys(loginEventColors).sort());
    for (const event of network.events) {
      expect(Math.abs(event.point.x)).toBeLessThan(half);
      expect(Math.abs(event.point.z)).toBeLessThan(half);
      if (event.lift > 0) {
        expect(network.elevated.some((road) => Math.abs(deckHeightAt(road, event.point) - event.lift) < 1e-9 && distanceToSegments(road.line, event.point) < 1e-6)).toBe(true);
      }
    }
  });

  it("stays light enough for a weak GPU", () => {
    expect(network.streets.length).toBeLessThan(4000);
    expect(network.arterials.flat().length).toBeLessThan(900);
  });
});

describe("pointAlong", () => {
  const line = [{ x: 0, z: 0 }, { x: 10, z: 0 }, { x: 10, z: 10 }];

  it("walks the polyline by distance and clamps at both ends", () => {
    expect(polylineLength(line)).toBe(20);
    expect(pointAlong(line, -5)).toEqual({ x: 0, z: 0 });
    expect(pointAlong(line, 5)).toEqual({ x: 5, z: 0 });
    expect(pointAlong(line, 15)).toEqual({ x: 10, z: 5 });
    expect(pointAlong(line, 99)).toEqual({ x: 10, z: 10 });
  });
});
