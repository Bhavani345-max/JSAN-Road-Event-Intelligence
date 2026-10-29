"use client";

import { useCallback, useEffect, useState } from "react";
import { isSessionEnded, isUnreachable, RECONNECT_MS } from "@/lib/apiClient";
import { apiEventRepository, LIST_STEP } from "../api/eventRepository";
import type { EventListView } from "../filters";
import type { RoadEvent } from "../model";

export type EventsState =
  | { status: "loading" }
  | {
      status: "ready";
      events: RoadEvent[];
      /** How many the list holds in all: more than `events` while not all are loaded. */
      total: number;
      /** How many were asked for. */
      limit: number;
      loadedAt: Date;
      queryKey?: string;
    }
  | { status: "error"; message: string };

interface UseEvents {
  state: EventsState;
  /** Load again, showing the loading state. */
  reload: () => void;
  /** Load again in the background, keeping the current events on screen. */
  refresh: () => void;
  /** Load the next LIST_STEP older events too, keeping these on screen meanwhile. */
  showMore: () => void;
  /** Whether more is being loaded after "Show more". */
  loadingMore: boolean;
}

/**
 * Loads the newest events of a list from the repository, LIST_STEP at first
 * and LIST_STEP more at each `showMore`. While `enabled` is false (the
 * overview of all cities is on screen) nothing is loaded.
 */
export function useEvents(view: EventListView, cityId: string | null, enabled = true): UseEvents {
  const [state, setState] = useState<EventsState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const queryKey = `${view}|${cityId ?? "all"}`;
  // Another view or place starts again from its newest events.
  const [limit, setLimit] = useState({ queryKey, count: LIST_STEP });
  const count = limit.queryKey === queryKey ? limit.count : LIST_STEP;

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    let retry: ReturnType<typeof setTimeout> | undefined;
    apiEventRepository
      .listEvents(view, cityId, count)
      .then(({ events, total }) => {
        if (!cancelled) setState({ status: "ready", events, total, limit: count, loadedAt: new Date(), queryKey });
      })
      .catch((error: unknown) => {
        // A session that ended is AuthGate's to handle: back to signing in, no error shown.
        if (cancelled || isSessionEnded(error)) return;
        console.error("Failed to load events", error);
        setState({
          status: "error",
          message: error instanceof Error ? error.message : "Unknown error",
        });
        // The API is down or restarting: try again until it answers.
        if (isUnreachable(error)) retry = setTimeout(() => setAttempt((n) => n + 1), RECONNECT_MS);
      });
    return () => {
      cancelled = true;
      if (retry) clearTimeout(retry);
    };
  }, [attempt, view, cityId, queryKey, enabled, count]);

  const refresh = useCallback(() => setAttempt((n) => n + 1), []);
  const reload = useCallback(() => {
    setState({ status: "loading" });
    refresh();
  }, [refresh]);
  const showMore = useCallback(
    () => setLimit({ queryKey, count: count + LIST_STEP }),
    [queryKey, count],
  );

  const visibleState =
    state.status === "ready" && state.queryKey !== queryKey ? { status: "loading" as const } : state;
  const loadingMore = visibleState.status === "ready" && visibleState.limit < count;
  return { state: visibleState, reload, refresh, showMore, loadingMore };
}
