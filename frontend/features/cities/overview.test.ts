import { describe, expect, it } from "vitest";
import type { City } from "./cities";
import { groupCityCounts, sumStats, toCityBubbles, toCityCount } from "./overview";

const CANADA = {
  city_id: "canada",
  city_name: "Canada",
  total: 5,
  by_status: { VALIDATION_REQUIRED: 3, QC_PENDING: 1, ACTIVE: 1 },
  by_type: { PLANNED_ROAD_CLOSURE: 2, EMERGENCY_ROAD_CLOSURE: 1, ROAD_WORKS: 2 },
};
const SOUTH_AFRICA = { city_id: "south-africa", city_name: "South Africa", total: 0, by_status: {}, by_type: {} };

function city(
  id: string,
  name: string,
  center: [number, number],
  place: Partial<Pick<City, "country" | "level" | "parentId">> = {},
): City {
  return {
    id, name, country: "", level: "city", parentId: null, timeZone: "UTC", view: { center, zoom: 4 },
    hasGazetteer: false, sourceTimeZones: {}, ...place,
  };
}

function counted(cityId: string, total: number) {
  return toCityCount({ city_id: cityId, city_name: cityId, total, by_status: { VALIDATION_REQUIRED: total }, by_type: {} });
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

describe("countries and the cities within them (decision 0035)", () => {
  const cities = [
    city("hyderabad", "Hyderabad", [78.47, 17.4], { country: "IN" }),
    city("canada", "Canada", [-96.8, 54], { country: "CA", level: "country" }),
    city("delhi", "Delhi", [77.2, 28.6], { country: "IN" }),
    city("toronto", "Toronto", [-79.38, 43.65], { country: "CA", parentId: "canada" }),
    city("united-states", "United States", [-98, 39], { country: "US", level: "country" }),
    city("new-york", "New York City", [-74, 40.7], { country: "US", parentId: "united-states" }),
  ];
  const counts = [
    counted("hyderabad", 12), counted("canada", 1162), counted("delhi", 0), counted("toronto", 109),
    counted("united-states", 3979), counted("new-york", 2082),
  ];

  it("groups each city under its country, the country's own entry counting its cities too", () => {
    const groups = groupCityCounts(cities, counts);
    expect(groups.map((group) => [group.name, group.entry?.cityId ?? null, group.stats.total])).toEqual([
      ["United States", "united-states", 6061],
      ["Canada", "canada", 1271],
      ["India", null, 12],
    ]);
    const canada = groups[1];
    // Choosing Canada lists Canada's and Toronto's events; Toronto its own.
    expect(canada.entry?.stats.total).toBe(1271);
    expect(canada.cities.map((count) => [count.cityId, count.stats.total])).toEqual([["toronto", 109]]);
    // A country without an entry of its own is a heading over its cities.
    expect(groups[2].cities.map((count) => count.cityId)).toEqual(["hyderabad", "delhi"]);
  });

  it("keeps the tiles of all cities to each event once", () => {
    expect(sumStats(counts).total).toBe(12 + 1162 + 109 + 3979 + 2082);
  });

  it("gives a country's bubble what choosing it lists, and a city's bubble its own", () => {
    const bubbles = Object.fromEntries(
      toCityBubbles(cities, counts).features.map((f) => [f.properties.cityId, f.properties.count]),
    );
    expect(bubbles).toMatchObject({ canada: 1271, toronto: 109, "united-states": 6061, "new-york": 2082 });
  });

  it("does not leave out a count whose city is not listed yet", () => {
    const groups = groupCityCounts([cities[0]], [counted("hyderabad", 12), counted("canada", 5)]);
    expect(groups.map((group) => group.stats.total)).toEqual([12, 5]);
  });
});
