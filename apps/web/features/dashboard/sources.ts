"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch, apiPost, isUnreachable, RECONNECT_MS } from "@/lib/apiClient";
import type { ApiIngestionResult, ApiIngestionRun, ApiSource } from "@/types/api";

export type SourceHealth = "healthy" | "failing" | "not-checked" | "inactive";

/** A connected source REI ingests from, with the state of polling it. */
export interface ConnectedSource {
  id: string;
  name: string;
  type: string;
  health: SourceHealth;
  lastSuccessAt: string | null;
  lastFailureAt: string | null;
  /** Error from the latest poll; null if it succeeded or has not run. */
  lastError: string | null;
  /** Articles retrieved and stored as evidence. */
  articleCount: number;
  /** Candidate events created from those articles. */
  candidateCount: number;
  /** The city the source is about; null when it is about none in particular. */
  city: string | null;
  /** AUTHORITATIVE_OFFICIAL, PUBLISHER, DISCOVERY, … */
  sourceClass: string | null;
  tier: number | null;
}

/** Outcome of asking sources for new items right now. */
export interface IngestionOutcome {
  /** Sources that could not be reached, with the reason. */
  failures: { sourceId: string; error: string }[];
  newArticles: number;
  newEvents: number;
  /** Held records the source has revised since. */
  revised: number;
}

function toConnectedSource(source: ApiSource): ConnectedSource {
  const failedLast =
    source.last_failure_at !== null &&
    (source.last_success_at === null || source.last_failure_at > source.last_success_at);
  const health: SourceHealth = !source.active
    ? "inactive"
    : failedLast
      ? "failing"
      : source.last_success_at
        ? "healthy"
        : "not-checked";
  return {
    id: source.source_id,
    name: source.source_name,
    type: source.source_type,
    health,
    lastSuccessAt: source.last_success_at,
    lastFailureAt: source.last_failure_at,
    lastError: failedLast ? (source.last_error ?? "The last check failed.") : null,
    articleCount: source.artifact_count,
    candidateCount: source.event_count,
    city: source.city ?? null,
    sourceClass: source.source_class ?? null,
    tier: source.source_tier ?? null,
  };
}

/**
 * Only sources that are actually connected. Sources that were merely
 * researched are in the registry too, but are never presented as live.
 */
async function fetchConnectedSources(): Promise<ConnectedSource[]> {
  const sources = await apiFetch<ApiSource[]>("/sources?integration_status=CONNECTED");
  return sources.map(toConnectedSource);
}

function toOutcome(results: ApiIngestionResult[]): IngestionOutcome {
  return {
    failures: results
      .filter((result) => result.status !== "ok")
      .map((result) => ({
        sourceId: result.source_id,
        error: result.error ?? "The source could not be checked.",
      })),
    newArticles: results.reduce((sum, result) => sum + result.new_artifacts, 0),
    newEvents: results.reduce((sum, result) => sum + result.events_created, 0),
    revised: results.reduce((sum, result) => sum + (result.revised ?? 0), 0),
  };
}

/** Fetch one source now, or every connected source when no id is given. */
export async function checkSourcesNow(sourceId?: string): Promise<IngestionOutcome> {
  const query = sourceId ? `?source_id=${encodeURIComponent(sourceId)}` : "";
  const run = await apiPost<ApiIngestionRun>(`/ingestion/run${query}`);
  return toOutcome(run.results);
}

export function useConnectedSources(): { sources: ConnectedSource[]; refresh: () => void } {
  const [sources, setSources] = useState<ConnectedSource[]>([]);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let retry: ReturnType<typeof setTimeout> | undefined;
    fetchConnectedSources()
      .then((loaded) => {
        if (!cancelled) setSources(loaded);
      })
      // The event list already reports an unreachable API; stay quiet here
      // and try again until it answers.
      .catch((error: unknown) => {
        console.error("Failed to load sources", error);
        if (!cancelled && isUnreachable(error)) {
          retry = setTimeout(() => setAttempt((n) => n + 1), RECONNECT_MS);
        }
      });
    return () => {
      cancelled = true;
      if (retry) clearTimeout(retry);
    };
  }, [attempt]);

  const refresh = useCallback(() => setAttempt((n) => n + 1), []);
  return { sources, refresh };
}
