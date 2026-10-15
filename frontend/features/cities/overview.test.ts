import { describe, expect, it } from "vitest";
import type { City } from "./cities";
import { sumStats, toCityBubbles, toCityCount } from "./overview";

const CANADA = {
  city_id: "canada",
  city_name: "Canada",
  total: 5,
  by_status: { VALIDATION_REQUIRED: 3, QC_PENDING: 1, ACTIVE: 1 },
  by_type: { PLANNED_ROAD_CLOSURE: 2, EMERGENCY_ROAD_CLOSURE: 1, ROAD_WORKS: 2 },
};
const SOUTH_AFRICA = { city_id: "south-africa", city_name: "South Africa", total: 0, by_status: {}, by_type: {} };

function city(id: string, name: string, center: [number, number]): City {
  return { id, name, country: "", timeZone: "UTC", view: { center, zoom: 4 }, hasGazetteer: false, sourceTimeZones: {} };
}

describe("the overview of all cities", () => {
  it("reads a city's tiles from its counts", () => {
    expect(toCityCount(CANADA).stats).toEqual({
      total: 5, active: 1, scheduled: 0, roadClosures: 3, needsReview: 3,
    });
  });

  it("adds the cities up for the tiles of all cities", () => {
    const all = sumStats([toCityCount(CANADA), toCityCount(SOUTH_AFRICA), toCityCount(CANADA)]);
    expect(all).toEqual({ total: 10, active: 2, scheduled: 0, roadClosures: 6, needsReview: 6 });
  });

  it("draws one bubble per city at its map centre, with its count, even when it is 0", () => {
    const cities = [city("canada", "Canada", [-96.8, 54]), city("south-africa", "South Africa", [24.7, -29])];
    const { features } = toCityBubbles(cities, [toCityCount(CANADA)]);
    expect(features.map((f) => [f.properties.cityId, f.properties.count, f.geometry.coordinates])).toEqual([
      ["canada", 5, [-96.8, 54]],
      ["south-africa", 0, [24.7, -29]],
    ]);
    expect(toCityBubbles(cities, [{ ...toCityCount(CANADA), stats: { ...toCityCount(CANADA).stats, total: 1256 } }])
      .features[0].properties.countLabel).toBe("1,256");
  });
});
