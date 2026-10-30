"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/apiClient";
import type { ApiAnalytics } from "@/types/api";

interface Answer {
  /** The query last answered (or failed). */
  query: string;
  /** The last answer received: kept while a new query loads, so the page never flashes empty. */
  data: ApiAnalytics | null;
  error: string | null;
}

export interface AnalyticsState {
  data: ApiAnalytics | null;
  /** The current filters' answer has not arrived yet. */
  loading: boolean;
  error: string | null;
  retry: () => void;
}

/** The Analytics API's answer for a query (read only). */
export function useAnalytics(query: string): AnalyticsState {
  const [answer, setAnswer] = useState<Answer>({ query: "", data: null, error: null });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    apiFetch<ApiAnalytics>(`/events/analytics?${query}`)
      .then((data) => {
        if (!cancelled) setAnswer({ query, data, error: null });
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        const error = cause instanceof Error ? cause.message : "The analytics could not be loaded.";
        setAnswer((previous) => ({ ...previous, query, error }));
      });
    return () => {
      cancelled = true;
    };
  }, [query, attempt]);

  return {
    data: answer.data,
    loading: answer.query !== query,
    error: answer.query === query ? answer.error : null,
    retry: () => setAttempt((n) => n + 1),
  };
}
