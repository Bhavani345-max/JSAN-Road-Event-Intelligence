"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch, isUnreachable, RECONNECT_MS } from "@/lib/apiClient";
import type { EventListView } from "@/features/events/filters";
import { ROAD_CLOSURE_EVENT_TYPES } from "@/features/events/model";
import type { EventStats } from "@/features/events/stats";
import type { ApiCityEventCount, ApiEventSummary } from "@/types/api";
import type { City } from "./cities";

/**
 * The overview of all cities: how many events each city's view lists, without
 * loading them. The map shows one bubble per city instead of every event.
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

/** One bubble per configured city, at the place its map opens on, with its count. */
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
  return {
    type: "FeatureCollection",
    features: cities.map((city) => {
      const count = byId.get(city.id) ?? 0;
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
