"use client";

import { useEffect, useState } from "react";
import { isSessionEnded } from "@/lib/apiClient";
import { searchEvents, type EventPage } from "../api/eventRepository";
import type { EventListView } from "../filters";

const DEBOUNCE_MS = 300;
const MIN_LENGTH = 2;

/**
 * Asks the API which events match the search text: the newest LIST_STEP of
 * them, loaded or not. The API also searches the full text of the article
 * behind each event, which the browser does not hold.
 *
 * Returns null until a result for exactly this search text has arrived, so
 * the caller can fall back to what it can match itself in the meantime.
 */
export function useEventSearch(
  search: string,
  view: EventListView,
  cityId: string | null,
): EventPage | null {
  const query = search.trim();
  const [result, setResult] = useState<{ query: string; key: string; page: EventPage } | null>(null);
  const key = `${view}|${cityId ?? "all"}`;

  useEffect(() => {
    if (query.length < MIN_LENGTH) return;
    let cancelled = false;
    const timer = setTimeout(() => {
      searchEvents(query, view, cityId)
        .then((page) => {
          if (!cancelled) setResult({ query, key, page });
        })
        // The list still shows what could be matched in the browser.
        .catch((error: unknown) => {
          if (!isSessionEnded(error)) console.error("Event search failed", error);
        });
    }, DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query, view, cityId, key]);

  return query.length >= MIN_LENGTH && result?.query === query && result.key === key ? result.page : null;
}
