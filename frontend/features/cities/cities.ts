"use client";

import { useEffect, useState } from "react";
import { apiFetch, isUnreachable, RECONNECT_MS } from "@/lib/apiClient";
import { HYDERABAD_VIEW } from "@/lib/config";
import type { ApiCity } from "@/types/api";

/** A configured city, as the console uses it. */
export interface City {
  id: string;
  name: string;
  country: string;
  /** "country": a whole country's entry (Canada), which covers the cities within it; "city": one city. */
  level: "country" | "city";
  /** The country entry the city lies within (Toronto: "canada"); null for a country or a city with none. */
  parentId: string | null;
  timeZone: string;
  view: { center: [number, number]; zoom: number };
  /** Whether a place list exists, so events can be located by the places they name. */
  hasGazetteer: boolean;
  /** For a country spanning several zones: each regional source's zone. */
  sourceTimeZones: Record<string, string>;
}

export const DEFAULT_CITY_ID = "hyderabad";

/** The first city, used until the API answers and if it never does. */
export const DEFAULT_CITY: City = {
  id: DEFAULT_CITY_ID,
  name: "Hyderabad",
  country: "IN",
  level: "city",
  parentId: null,
  timeZone: "Asia/Kolkata",
  view: HYDERABAD_VIEW,
  hasGazetteer: true,
  sourceTimeZones: {},
};

export function toCity(dto: ApiCity): City {
  return {
    id: dto.id,
    name: dto.name,
    country: dto.country,
    level: dto.level,
    parentId: dto.parent_id,
    timeZone: dto.timezone,
    // Hyderabad keeps the view the console has always opened on.
    view:
      dto.id === DEFAULT_CITY_ID ? HYDERABAD_VIEW : { center: dto.map_center, zoom: dto.map_zoom },
    hasGazetteer: dto.has_gazetteer,
    sourceTimeZones: dto.source_time_zones ?? {},
  };
}

/**
 * Every city at once: one map with all their events and sources. Not a
 * configured city; each event keeps its own city and time zone.
 */
export const ALL_CITIES_ID = "all";
export const ALL_CITIES: City = {
  id: ALL_CITIES_ID,
  name: "All cities",
  country: "",
  level: "city",
  parentId: null,
  timeZone: "Asia/Kolkata",
  view: { center: [30, 30], zoom: 1.6 },
  hasGazetteer: false,
  sourceTimeZones: {},
};

/**
 * The configured ids a choice covers (decision 0035): a city alone, or a
 * country entry and the cities within it (Canada: Canada and Toronto). Null
 * for all cities together.
 */
export function areaIds(city: City, cities: City[]): string[] | null {
  if (city.id === ALL_CITIES_ID) return null;
  return [city.id, ...cities.filter((other) => other.parentId === city.id).map((other) => other.id)];
}

/** A country's name in English ("CA" -> "Canada"); the code itself if unknown. */
export function countryName(code: string): string {
  try {
    return new Intl.DisplayNames(["en"], { type: "region" }).of(code) ?? code;
  } catch {
    return code;
  }
}

/** One country in the console's lists: its entry, if configured, and its cities. */
export interface CountryGroup {
  country: string;
  name: string;
  /** The country's own entry (Canada); null when only cities of it are configured (India). */
  entry: City | null;
  /** Its cities, in the configured order (the default city first). */
  cities: City[];
}

/** The configured cities grouped by country, countries by name. */
export function groupByCountry(cities: City[]): CountryGroup[] {
  const groups = new Map<string, CountryGroup>();
  for (const city of cities) {
    if (city.id === ALL_CITIES_ID) continue;
    const group = groups.get(city.country) ?? {
      country: city.country,
      name: countryName(city.country),
      entry: null,
      cities: [],
    };
    if (city.level === "country") group.entry = city;
    else group.cities.push(city);
    groups.set(city.country, group);
  }
  return [...groups.values()].sort((a, b) => a.name.localeCompare(b.name));
}

/**
 * The name a choice is offered under: a country entry with cities within it
 * says which ("Canada (incl. Toronto)"), so it is clear that it covers them.
 */
export function choiceLabel(city: City, cities: City[]): string {
  if (city.id === ALL_CITIES_ID) return city.name;
  const within = cities.filter((other) => other.parentId === city.id);
  if (within.length === 0) return city.name;
  const names = within.length <= 2 ? within.map((other) => other.name).join(", ") : `${within.length} cities`;
  return `${city.name} (incl. ${names})`;
}

/** The configured cities, the default first. */
export function useCities(): City[] {
  const [cities, setCities] = useState<City[]>([DEFAULT_CITY]);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let cancelled = false;
    let retry: ReturnType<typeof setTimeout> | undefined;
    apiFetch<ApiCity[]>("/cities")
      .then((loaded) => {
        if (!cancelled && loaded.length > 0) setCities(loaded.map(toCity));
      })
      // Without the API there is only the default city; the event list reports
      // the error. Try again until the API answers.
      .catch((error: unknown) => {
        console.error("Failed to load cities", error);
        if (!cancelled && isUnreachable(error)) {
          retry = setTimeout(() => setAttempt((n) => n + 1), RECONNECT_MS);
        }
      });
    return () => {
      cancelled = true;
      if (retry) clearTimeout(retry);
    };
  }, [attempt]);
  return cities;
}
