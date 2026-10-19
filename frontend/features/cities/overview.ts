"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch, isUnreachable, RECONNECT_MS } from "@/lib/apiClient";
import type { EventListView } from "@/features/events/filters";
import { ROAD_CLOSURE_EVENT_TYPES } from "@/features/events/model";
import type { EventStats } from "@/features/events/stats";
import type { ApiCityEventCount, ApiEventSummary } from "@/types/api";
import { countryChoices, groupByCountry, type City } from "./cities";

/**
 * The overview of all countries: how many events each entry's view lists,
 * without loading them. The map shows one bubble per country instead of every
 * event. The same counts give each city's number once a country is chosen.
 */
export interface CityCount {
  cityId: string;
  cityName: string;
  stats: EventStats;
}

export function toCityCount(dto: ApiCityEventCount): CityCount {
  const status = (name: string) => dto.by_status[name] ?? 0;
  return {
    cityId: dto.city_id,
    cityName: dto.city_name,
    stats: {
      total: dto.total,
      active: status("ACTIVE"),
      scheduled: status("SCHEDULED"),
      roadClosures: ROAD_CLOSURE_EVENT_TYPES.reduce((sum, type) => sum + (dto.by_type[type] ?? 0), 0),
      needsReview: status("VALIDATION_REQUIRED"),
    },
  };
}

/** The tiles for all cities together. */
export function sumStats(counts: CityCount[]): EventStats {
  return counts.reduce<EventStats>(
    (sum, { stats }) => ({
      total: sum.total + stats.total,
      active: sum.active + stats.active,
      scheduled: sum.scheduled + stats.scheduled,
      roadClosures: sum.roadClosures + stats.roadClosures,
      needsReview: sum.needsReview + stats.needsReview,
    }),
    { total: 0, active: 0, scheduled: 0, roadClosures: 0, needsReview: 0 },
  );
}

export async function fetchCityCounts(view: EventListView): Promise<CityCount[]> {
  const summary = await apiFetch<ApiEventSummary>(`/events/summary?view=${encodeURIComponent(view)}`);
  return summary.cities.map(toCityCount);
}

export type CityCountsState =
  | { status: "loading" }
  | { status: "ready"; counts: CityCount[]; queryKey: string }
  | { status: "error"; message: string };

/** The per-city counts of a view, while `enabled` (the overview is on screen). */
export function useCityCounts(view: EventListView, enabled: boolean) {
  const [state, setState] = useState<CityCountsState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    let retry: ReturnType<typeof setTimeout> | undefined;
    fetchCityCounts(view)
      .then((counts) => {
        if (!cancelled) setState({ status: "ready", counts, queryKey: view });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        console.error("Failed to load the overview", error);
        setState({ status: "error", message: error instanceof Error ? error.message : "Unknown error" });
        if (isUnreachable(error)) retry = setTimeout(() => setAttempt((n) => n + 1), RECONNECT_MS);
      });
    return () => {
      cancelled = true;
      if (retry) clearTimeout(retry);
    };
  }, [view, enabled, attempt]);
  const refresh = useCallback(() => setAttempt((n) => n + 1), []);
  const visible: CityCountsState =
    state.status === "ready" && state.queryKey !== view ? { status: "loading" } : state;
  return { state: visible, refresh };
}

const NO_STATS: EventStats = { total: 0, active: 0, scheduled: 0, roadClosures: 0, needsReview: 0 };

/**
 * One country in the overview (decision 0035). Its entry, when configured
 * (Canada), carries what choosing it lists: its own events and those of the
 * cities within it (Toronto). Each city carries its own.
 */
export interface CountryCount {
  country: string;
  name: string;
  entry: CityCount | null;
  cities: CityCount[];
  /** Everything listed in the country: each event once. */
  stats: EventStats;
}

const byTotal = (a: CityCount, b: CityCount) => b.stats.total - a.stats.total || a.cityName.localeCompare(b.cityName);

/** The per-city counts grouped by country, the busiest country first. */
export function groupCityCounts(cities: City[], counts: CityCount[]): CountryCount[] {
  const byId = new Map(counts.map((count) => [count.cityId, count]));
  const countOf = (city: City): CityCount =>
    byId.get(city.id) ?? { cityId: city.id, cityName: city.name, stats: NO_STATS };
  const groups: CountryCount[] = groupByCountry(cities).map((group) => {
    const own = group.cities.map(countOf).sort(byTotal);
    const entry = group.entry ? countOf(group.entry) : null;
    const stats = sumStats(entry ? [entry, ...own] : own);
    return { country: group.country, name: group.name, entry: entry && { ...entry, stats }, cities: own, stats };
  });
  // A count for an entry the city list does not hold yet (still loading) is not left out.
  const listed = new Set(cities.map((city) => city.id));
  for (const count of counts) {
    if (!listed.has(count.cityId)) {
      groups.push({ country: count.cityId, name: count.cityName, entry: count, cities: [], stats: count.stats });
    }
  }
  return groups.sort((a, b) => b.stats.total - a.stats.total || a.name.localeCompare(b.name));
}

/**
 * What each choice within a country lists (decision 0036): the country its own
 * events and its cities' (India: every Indian city's), each city its own.
 */
export function cityChoiceCounts(country: City, cities: City[], counts: CityCount[]): Record<string, number> {
  const byId = new Map(counts.map((count) => [count.cityId, count.stats.total]));
  const own = (city: City) => byId.get(city.id) ?? 0;
  const result: Record<string, number> = {};
  for (const city of cities) result[city.id] = own(city);
  result[country.id] = own(country) + cities.reduce((sum, city) => sum + own(city), 0);
  return result;
}

/**
 * One bubble per country (decision 0036), at the place its map opens on, with
 * what choosing it lists: its own events and those of the cities within it.
 * Cities get no bubble of their own; choosing the country shows them.
 */
export interface CityBubbleFeature {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: { cityId: string; name: string; count: number; countLabel: string };
}

export interface CityBubbleCollection {
  type: "FeatureCollection";
  features: CityBubbleFeature[];
}

export function toCityBubbles(cities: City[], counts: CityCount[]): CityBubbleCollection {
  const byId = new Map(counts.map((count) => [count.cityId, count.stats.total]));
  const own = (city: City) => byId.get(city.id) ?? 0;
  return {
    type: "FeatureCollection",
    features: countryChoices(cities).map((city) => {
      const count =
        own(city) + cities.filter((other) => other.parentId === city.id).reduce((sum, other) => sum + own(other), 0);
      return {
        type: "Feature",
        geometry: { type: "Point", coordinates: city.view.center },
        properties: {
          cityId: city.id,
          name: city.name,
          count,
          countLabel: count.toLocaleString("en-GB"),
        },
      };
    }),
  };
}
