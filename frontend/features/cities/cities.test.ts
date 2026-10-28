import { describe, expect, it } from "vitest";
import type { ApiCity } from "@/types/api";
import {
  ALL_CITIES,
  areaIds,
  citiesIn,
  countryChoices,
  countryName,
  countryOf,
  groupByCountry,
  searchCountries,
  toCity,
} from "./cities";

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
  apiCity("hyderabad", "Hyderabad", "IN", { parent_id: "india" }),
  apiCity("canada", "Canada", "CA", { level: "country" }),
  apiCity("delhi", "Delhi", "IN", { parent_id: "india" }),
  apiCity("india", "India", "IN", { level: "country" }),
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
    expect(areaIds(byId("india"), CITIES)).toEqual(["india", "hyderabad", "delhi"]);
  });

  it("covers only the city when a city is chosen", () => {
    expect(areaIds(byId("toronto"), CITIES)).toEqual(["toronto"]);
    expect(areaIds(byId("new-york"), CITIES)).toEqual(["new-york"]);
    expect(areaIds(byId("delhi"), CITIES)).toEqual(["delhi"]);
  });

  it("covers everything, filtered by nothing, for all cities", () => {
    expect(areaIds(ALL_CITIES, CITIES)).toBeNull();
  });

  it("groups the entries by country: the country, its cities under it", () => {
    const groups = groupByCountry(CITIES);
    expect(groups.map((group) => [group.name, group.entry?.id ?? null, group.cities.map((city) => city.id)])).toEqual([
      ["Canada", "canada", ["toronto"]],
      ["India", "india", ["hyderabad", "delhi"]],
      ["Japan", "japan", []],
      ["United States", "united-states", ["new-york"]],
    ]);
    // Toronto is never a country of its own, nor listed twice.
    expect(groups.flatMap((group) => [group.entry, ...group.cities]).filter(Boolean)).toHaveLength(CITIES.length);
  });
});

describe("countries first, then their cities (decision 0036)", () => {
  it("offers only the countries, by name", () => {
    expect(countryChoices(CITIES).map((city) => city.id)).toEqual(["canada", "india", "japan", "united-states"]);
  });

  it("keeps a city reachable if its country has no entry", () => {
    const lone = toCity(apiCity("london", "London", "GB"));
    expect(countryChoices([...CITIES, lone]).map((city) => city.id)).toContain("london");
    expect(countryOf(lone, CITIES)).toBe(lone);
    expect(citiesIn(countryOf(lone, CITIES), CITIES)).toEqual([]);
  });

  it("finds the country of a choice: the country itself, or a city's country", () => {
    expect(countryOf(byId("india"), CITIES)?.id).toBe("india");
    expect(countryOf(byId("delhi"), CITIES)?.id).toBe("india");
    expect(countryOf(byId("toronto"), CITIES)?.id).toBe("canada");
    expect(countryOf(ALL_CITIES, CITIES)).toBeNull();
  });

  it("lists a country's cities in the configured order, the default city first", () => {
    expect(citiesIn(byId("india"), CITIES).map((city) => city.id)).toEqual(["hyderabad", "delhi"]);
    expect(citiesIn(byId("japan"), CITIES)).toEqual([]);
    expect(citiesIn(byId("delhi"), CITIES)).toEqual([]);
    expect(citiesIn(null, CITIES)).toEqual([]);
  });

  it("calls the whole set All countries", () => {
    expect(ALL_CITIES.name).toBe("All countries");
  });

  it("names countries in English", () => {
    expect(countryName("CA")).toBe("Canada");
    expect(countryName("US")).toBe("United States");
  });
});

describe("searching the country list (decision 0043)", () => {
  const choices = countryChoices(CITIES);
  const found = (query: string) =>
    searchCountries(choices, CITIES, query).map(({ choice, city }) => (city ? `${choice.name} (${city})` : choice.name));

  it("lists every country while nothing is typed", () => {
    expect(found("")).toEqual(["Canada", "India", "Japan", "United States"]);
    expect(found("   ")).toEqual(["Canada", "India", "Japan", "United States"]);
  });

  it("finds a country by the start of its name, in any case", () => {
    expect(found("in")).toEqual(["India"]);
    expect(found("JAP")).toEqual(["Japan"]);
    expect(found("united")).toEqual(["United States"]);
  });

  it("puts names starting with the text before names containing it", () => {
    expect(found("ja")).toEqual(["Japan"]);
    expect(found("an")).toEqual(["Canada", "Japan"]); // both contain "an"; no name starts with it
    // One letter: names only, not other names (America).
    expect(found("a")).toEqual(["Canada", "India", "Japan", "United States"]);
    expect(found("states")).toEqual(["United States"]);
  });

  it("finds a country by its code or a common other name", () => {
    expect(found("ca")).toEqual(["Canada"]);
    expect(found("us")).toEqual(["United States"]);
    expect(found("usa")).toEqual(["United States"]);
    expect(found("america")).toEqual(["United States"]);
  });

  it("finds a country by one of its cities, naming the city", () => {
    expect(found("toron")).toEqual(["Canada (Toronto)"]);
    expect(found("hyd")).toEqual(["India (Hyderabad)"]);
    expect(found("new york")).toEqual(["United States (New York City)"]);
  });

  it("ignores accents and finds nothing for an unknown name", () => {
    expect(found("Jápan")).toEqual(["Japan"]);
    expect(found("atlantis")).toEqual([]);
  });
});
