import { describe, expect, it } from "vitest";
import type { ApiCity } from "@/types/api";
import { ALL_CITIES, areaIds, choiceLabel, countryName, groupByCountry, toCity } from "./cities";

function apiCity(id: string, name: string, country: string, extra: Partial<ApiCity> = {}): ApiCity {
  return {
    id,
    name,
    country,
    level: "city",
    parent_id: null,
    region: null,
    timezone: "UTC",
    language: "en",
    bbox: [-10, -10, 10, 10],
    map_center: [0, 0],
    map_zoom: 4,
    scope_terms: [name],
    official_sources: [],
    has_gazetteer: false,
    ...extra,
  };
}

// The configured entries as GET /api/cities lists them: the default city first.
const CITIES = [
  apiCity("hyderabad", "Hyderabad", "IN"),
  apiCity("canada", "Canada", "CA", { level: "country" }),
  apiCity("delhi", "Delhi", "IN"),
  apiCity("japan", "Japan", "JP", { level: "country" }),
  apiCity("new-york", "New York City", "US", { parent_id: "united-states" }),
  apiCity("toronto", "Toronto", "CA", { parent_id: "canada" }),
  apiCity("united-states", "United States", "US", { level: "country" }),
].map(toCity);
const byId = (id: string) => CITIES.find((city) => city.id === id)!;

describe("countries and the cities within them (decision 0035)", () => {
  it("reads each entry's level and the country it lies within", () => {
    expect([byId("toronto").level, byId("toronto").parentId]).toEqual(["city", "canada"]);
    expect([byId("canada").level, byId("canada").parentId]).toEqual(["country", null]);
  });

  it("covers a country's own events and its cities' when the country is chosen", () => {
    expect(areaIds(byId("canada"), CITIES)).toEqual(["canada", "toronto"]);
    expect(areaIds(byId("united-states"), CITIES)).toEqual(["united-states", "new-york"]);
  });

  it("covers only the city when a city is chosen", () => {
    expect(areaIds(byId("toronto"), CITIES)).toEqual(["toronto"]);
    expect(areaIds(byId("new-york"), CITIES)).toEqual(["new-york"]);
    expect(areaIds(byId("delhi"), CITIES)).toEqual(["delhi"]);
  });

  it("covers everything, filtered by nothing, for all cities", () => {
    expect(areaIds(ALL_CITIES, CITIES)).toBeNull();
  });

  it("groups the selector by country: the country first, its cities under it", () => {
    const groups = groupByCountry(CITIES);
    expect(groups.map((group) => [group.name, group.entry?.id ?? null, group.cities.map((city) => city.id)])).toEqual([
      ["Canada", "canada", ["toronto"]],
      ["India", null, ["hyderabad", "delhi"]],
      ["Japan", "japan", []],
      ["United States", "united-states", ["new-york"]],
    ]);
    // Toronto is never a country of its own, nor listed twice.
    expect(groups.flatMap((group) => [group.entry, ...group.cities]).filter(Boolean)).toHaveLength(CITIES.length);
  });

  it("says which cities a country's choice includes", () => {
    expect(choiceLabel(byId("canada"), CITIES)).toBe("Canada (incl. Toronto)");
    expect(choiceLabel(byId("united-states"), CITIES)).toBe("United States (incl. New York City)");
    expect(choiceLabel(byId("toronto"), CITIES)).toBe("Toronto");
    expect(choiceLabel(byId("japan"), CITIES)).toBe("Japan");
  });

  it("names countries in English", () => {
    expect(countryName("CA")).toBe("Canada");
    expect(countryName("US")).toBe("United States");
  });
});
