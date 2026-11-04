import { describe, expect, it } from "vitest";
import { boxAreaKm2, describeIncident, liveBbox, MAX_LIVE_AREA_KM2 } from "./liveIncidents";

describe("TomTom live incidents", () => {
  it("asks only for areas TomTom answers for (up to 10,000 km²)", () => {
    const centralWarsaw: [number, number, number, number] = [20.95, 52.18, 21.1, 52.27];
    expect(boxAreaKm2(centralWarsaw)).toBeGreaterThan(90);
    expect(boxAreaKm2(centralWarsaw)).toBeLessThan(120);
    expect(liveBbox(centralWarsaw)).toBe("20.95000,52.18000,21.10000,52.27000");
    // All of Poland: zoom in first.
    expect(liveBbox([14.1, 49.0, 24.2, 54.9])).toBeNull();
    expect(boxAreaKm2([14.1, 49.0, 24.2, 54.9])).toBeGreaterThan(MAX_LIVE_AREA_KM2);
  });

  it("keeps the box within the world and refuses an empty one", () => {
    expect(liveBbox([-200, 10, -179.9, 10.1])).not.toBeNull();
    expect(liveBbox([10, 10, 10, 10.1])).toBeNull();
  });

  it("describes an incident in one line", () => {
    const line = describeIncident({
      id: "a2",
      category: "ROAD_WORKS",
      label: "Road works",
      description: "Roadworks",
      from: "Marszałkowska",
      to: "Świętokrzyska",
      roads: ["7"],
      start: null,
      end: null,
      delay: "minor",
    });
    expect(line).toBe("Road works · Marszałkowska → Świętokrzyska · 7");
  });
});
