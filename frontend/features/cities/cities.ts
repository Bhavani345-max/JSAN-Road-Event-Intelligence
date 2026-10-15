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
  timeZone: "Asia/Kolkata",
  view: { center: [30, 30], zoom: 1.6 },
  hasGazetteer: false,
  sourceTimeZones: {},
};

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
