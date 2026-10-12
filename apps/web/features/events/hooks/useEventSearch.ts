"use client";

import { useEffect, useState } from "react";
import { searchEventIds } from "../api/eventRepository";

const DEBOUNCE_MS = 300;
const MIN_LENGTH = 2;

/**
 * Asks the API which events match the search text. The API also searches the
 * full text of the article behind each event, which the browser does not hold.
 *
 * Returns null until a result for exactly this search text has arrived, so
 * the caller can fall back to what it can match itself in the meantime.
 */
export function useEventSearch(search: string): ReadonlySet<string> | null {
  const query = search.trim();
  const [result, setResult] = useState<{ query: string; ids: Set<string> } | null>(null);

  useEffect(() => {
    if (query.length < MIN_LENGTH) return;
    let cancelled = false;
    const timer = setTimeout(() => {
      searchEventIds(query)
        .then((ids) => {
          if (!cancelled) setResult({ query, ids });
        })
        // The list still shows what could be matched in the browser.
        .catch((error: unknown) => console.error("Event search failed", error));
    }, DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query]);

  return query.length >= MIN_LENGTH && result?.query === query ? result.ids : null;
}
