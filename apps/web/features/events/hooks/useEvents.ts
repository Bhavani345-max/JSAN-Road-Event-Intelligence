"use client";

import { useCallback, useEffect, useState } from "react";
import { isUnreachable, RECONNECT_MS } from "@/lib/apiClient";
import { apiEventRepository } from "../api/eventRepository";
import type { EventListView } from "../filters";
import type { RoadEvent } from "../model";

export type EventsState =
  | { status: "loading" }
  | { status: "ready"; events: RoadEvent[]; loadedAt: Date; queryKey?: string }
  | { status: "error"; message: string };

interface UseEvents {
  state: EventsState;
  /** Load again, showing the loading state. */
  reload: () => void;
  /** Load again in the background, keeping the current events on screen. */
  refresh: () => void;
}

/** Loads events from the repository, whatever backs it. */
export function useEvents(view: EventListView, cityId: string | null): UseEvents {
  const [state, setState] = useState<EventsState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const queryKey = `${view}|${cityId ?? "all"}`;

  useEffect(() => {
    let cancelled = false;
    let retry: ReturnType<typeof setTimeout> | undefined;
    apiEventRepository
      .listEvents(view, cityId)
      .then((events) => {
        if (!cancelled) setState({ status: "ready", events, loadedAt: new Date(), queryKey });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
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
  }, [attempt, view, cityId, queryKey]);

  const refresh = useCallback(() => setAttempt((n) => n + 1), []);
  const reload = useCallback(() => {
    setState({ status: "loading" });
    refresh();
  }, [refresh]);

  const visibleState =
    state.status === "ready" && state.queryKey !== queryKey ? { status: "loading" as const } : state;
  return { state: visibleState, reload, refresh };
}
