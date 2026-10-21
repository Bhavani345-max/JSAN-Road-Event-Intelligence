import { describe, expect, it } from "vitest";
import { createRng, generateRoadNetwork, pointAlong, polylineLength } from "./roadNetwork";

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
