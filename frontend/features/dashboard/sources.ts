"use client";

import { useCallback, useEffect, useState } from "react";
import type { EventListView } from "@/features/events/filters";
import { apiFetch, apiPost, isUnreachable, RECONNECT_MS } from "@/lib/apiClient";
import type { ApiCityCoverage, ApiEventCoverage, ApiIngestionResult, ApiIngestionRun, ApiSource } from "@/types/api";

/**
 * A source's state, as the API derives it from the registry, its polling and
 * its events (decision 0034). The console never works one out on its own.
 */
export type SourceStatus =
  | "COLLECTING"
  | "NO_RECENT_EVENTS"
  | "FAILING"
  | "NOT_POLLED_YET"
  | "NOT_SCHEDULED"
  | "DISABLED"
  | "AWAITING_PERMISSION"
  | "BLOCKED_BY_TERMS"
  | "BLOCKED"
  | "REMOVED"
  | "NEEDS_CREDENTIALS"
  | "RESEARCHED"
  | "MANUAL_ONLY";

/** A source in REI's registry, connected or not, with its state. */
export interface RegistrySource {
  id: string;
  name: string;
  type: string;
  status: SourceStatus;
  statusLabel: string;
  /** Why it stands there: the last error, the terms, the switch that turns it off… */
  statusReason: string | null;
  /** Whether REI polls it on its own schedule. */
  polled: boolean;
  /** Whether it can be run now ("Check"): connected, even if not scheduled here. */
  checkable: boolean;
  lastPollAt: string | null;
  lastSuccessAt: string | null;
  lastFailureAt: string | null;
  /** Articles or records retrieved and stored as evidence. */
  articleCount: number;
  /** Events detected from them, ever. */
  candidateCount: number;
  recentEventCount: number;
  pendingReviewCount: number;
  validatedCount: number;
  /** Its events awaiting review that the review queue's map shows. */
  onMapReviewCount: number;
  /** Its validated events that the operations map shows. Never added to the review count. */
  onMapOperationsCount: number;
  /** The city the source is about; null when it is about none in particular. */
  city: string | null;
  /** Its country (ISO 3166-1 alpha-2); null when it covers none in particular. */
  country: string | null;
  /** AUTHORITATIVE_OFFICIAL, PUBLISHER, DISCOVERY, … */
  sourceClass: string | null;
  tier: number | null;
}

/** How the console groups sources, in this order. */
export const SOURCE_GROUPS: { key: string; label: string; statuses: SourceStatus[] }[] = [
  {
    key: "polled",
    label: "Polled by REI",
    statuses: ["FAILING", "COLLECTING", "NO_RECENT_EVENTS", "NOT_POLLED_YET"],
  },
  { key: "off", label: "Connected, off here", statuses: ["NOT_SCHEDULED", "DISABLED"] },
  {
    key: "unavailable",
    label: "Not connected",
    statuses: [
      "AWAITING_PERMISSION",
      "NEEDS_CREDENTIALS",
      "BLOCKED_BY_TERMS",
      "BLOCKED",
      "REMOVED",
      "RESEARCHED",
      "MANUAL_ONLY",
    ],
  },
];

/** Outcome of asking sources for new items right now. */
export interface IngestionOutcome {
  /** Sources that could not be reached, with the reason. */
  failures: { sourceId: string; error: string }[];
  newArticles: number;
  newEvents: number;
  /** Held records the source has revised since. */
  revised: number;
}

export function toRegistrySource(source: ApiSource): RegistrySource {
  return {
    id: source.source_id,
    name: source.source_name,
    type: source.source_type,
    status: source.status as SourceStatus,
    statusLabel: source.status_label,
    statusReason: source.status_reason,
    polled: source.polled,
    // Only a connected source has a connector; a disabled one is never run.
    checkable: source.integration_status === "CONNECTED",
    lastPollAt: source.last_poll_at,
    lastSuccessAt: source.last_success_at,
    lastFailureAt: source.last_failure_at,
    articleCount: source.artifact_count,
    candidateCount: source.event_count,
    recentEventCount: source.recent_event_count,
    pendingReviewCount: source.pending_review_count,
    validatedCount: source.validated_count,
    onMapReviewCount: source.on_map_review_count,
    onMapOperationsCount: source.on_map_operations_count,
    city: source.city ?? null,
    country: source.country ?? null,
    sourceClass: source.source_class ?? null,
    tier: source.source_tier ?? null,
  };
}

/** The sources of each group, in the group's order of states, then by name. */
export function groupSources(sources: RegistrySource[]) {
  return SOURCE_GROUPS.map((group) => ({
    ...group,
    sources: sources
      .filter((source) => group.statuses.includes(source.status))
      .sort(
        (a, b) =>
          group.statuses.indexOf(a.status) - group.statuses.indexOf(b.status) ||
          a.name.localeCompare(b.name),
      ),
  })).filter((group) => group.sources.length > 0);
}

/** Every source in the registry, with its state: nothing is left out. */
async function fetchSources(): Promise<RegistrySource[]> {
  const sources = await apiFetch<ApiSource[]>("/sources");
  return sources.map(toRegistrySource);
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

/** Loads `load()` and keeps retrying while the API is unreachable. */
function useLoaded<T>(load: () => Promise<T>, empty: T, what: string): { value: T; refresh: () => void } {
  const [value, setValue] = useState<T>(empty);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let retry: ReturnType<typeof setTimeout> | undefined;
    load()
      .then((loaded) => {
        if (!cancelled) setValue(loaded);
      })
      // The event list already reports an unreachable API; stay quiet here
      // and try again until it answers.
      .catch((error: unknown) => {
        console.error(`Failed to load ${what}`, error);
        if (!cancelled && isUnreachable(error)) {
          retry = setTimeout(() => setAttempt((n) => n + 1), RECONNECT_MS);
        }
      });
    return () => {
      cancelled = true;
      if (retry) clearTimeout(retry);
    };
  }, [attempt, load, what]);

  const refresh = useCallback(() => setAttempt((n) => n + 1), []);
  return { value, refresh };
}

const NO_SOURCES: RegistrySource[] = [];
const NO_COVERAGE: ApiCityCoverage[] = [];
const fetchCoverage = async () => (await apiFetch<ApiEventCoverage>("/events/coverage")).cities;

export function useSources(): { sources: RegistrySource[]; refresh: () => void } {
  const { value, refresh } = useLoaded(fetchSources, NO_SOURCES, "sources");
  return { sources: value, refresh };
}

/** Per city: events detected, awaiting review, validated, on each map, and hidden from it by why. */
export function useCoverage(): { coverage: ApiCityCoverage[]; refresh: () => void } {
  const { value, refresh } = useLoaded(fetchCoverage, NO_COVERAGE, "event coverage");
  return { coverage: value, refresh };
}

export interface CoverageTotals {
  detected: number;
  pendingReview: number;
  validated: number;
  /** Events awaiting review that the review queue's map shows. */
  onMapReview: number;
  /** Validated events that the operations map shows. */
  onMapOperations: number;
  merged: number;
  rejected: number;
  closed: number;
  /** Awaiting review, not on the review queue's map, by the rule hiding them. */
  hiddenReview: Record<string, number>;
  /** Validated, not on the operations map, by the rule hiding them. */
  hiddenOperations: Record<string, number>;
}

function addUp(target: Record<string, number>, counts: Record<string, number>) {
  for (const [reason, count] of Object.entries(counts)) target[reason] = (target[reason] ?? 0) + count;
}

/**
 * The coverage of what a choice covers (`areaIds`: one city, or a country
 * entry and its cities, decision 0035), or of every city together (null).
 * Each row is one entry's own events, so nothing is counted twice.
 */
export function coverageTotals(coverage: ApiCityCoverage[], areaIds: string[] | null): CoverageTotals {
  const rows = areaIds === null ? coverage : coverage.filter((row) => areaIds.includes(row.city_id));
  const hiddenReview: Record<string, number> = {};
  const hiddenOperations: Record<string, number> = {};
  for (const row of rows) {
    addUp(hiddenReview, row.hidden_review);
    addUp(hiddenOperations, row.hidden_operations);
  }
  const sum = (pick: (row: ApiCityCoverage) => number) => rows.reduce((total, row) => total + pick(row), 0);
  return {
    detected: sum((row) => row.detected),
    pendingReview: sum((row) => row.pending_review),
    validated: sum((row) => row.validated),
    onMapReview: sum((row) => row.on_map_review),
    onMapOperations: sum((row) => row.on_map_operations),
    merged: sum((row) => row.merged),
    rejected: sum((row) => row.rejected),
    closed: sum((row) => row.closed),
    hiddenReview,
    hiddenOperations,
  };
}

/**
 * What the map of a view shows (decision 0035): the review queue's map,
 * events awaiting review; the operations map, validated events only. An
 * event awaiting review is never counted as one on the operations map.
 */
export function shownOnMap(view: EventListView, counts: { review: number; operations: number }): number {
  return view === "validation" ? counts.review : counts.operations;
}

/** Plain words for why events are hidden from the map. */
export const HIDDEN_REASONS: Record<string, string> = {
  no_location: "no location",
  no_start: "no stated start",
  ended: "ended",
  source_ended: "reported over by the source",
  open_end_lapsed: "open-ended article over 30 days old",
};

/** A count as the console writes it: "3,979". */
export const count = (value: number) => value.toLocaleString("en-GB");
const number = count;

/** "(40 ended, 20 no location)", most first; nothing when no rule is counted. */
function reasons(hidden: Record<string, number>): string {
  const words = Object.entries(hidden)
    .filter(([, count]) => count > 0)
    .sort(([, a], [, b]) => b - a)
    .map(([reason, count]) => `${number(count)} ${HIDDEN_REASONS[reason] ?? reason}`);
  return words.length > 0 ? ` (${words.join(", ")})` : "";
}

/**
 * Why the events of a choice are not on this view's map (decision 0035): in
 * the operations view, every event awaiting review (it is not confirmed) and
 * the validated ones hidden by a rule; in the review queue, the events
 * awaiting review hidden by a rule and the validated ones (on the other map).
 */
export function notOnThisMap(totals: CoverageTotals, view: EventListView): string[] {
  const parts: string[] = [];
  if (view === "validation") {
    const hidden = totals.pendingReview - totals.onMapReview;
    if (hidden > 0) parts.push(`${number(hidden)} awaiting review${reasons(totals.hiddenReview)}`);
    if (totals.validated > 0) {
      parts.push(`${number(totals.validated)} validated (the operations map shows ${number(totals.onMapOperations)})`);
    }
  } else {
    if (totals.pendingReview > 0) {
      parts.push(
        `${number(totals.pendingReview)} awaiting review, not confirmed (the review queue's map shows ${number(totals.onMapReview)})`,
      );
    }
    const hidden = totals.validated - totals.onMapOperations;
    if (hidden > 0) parts.push(`${number(hidden)} validated${reasons(totals.hiddenOperations)}`);
  }
  return parts;
}

/**
 * A source's event counts in words: awaiting review, validated, and how many
 * this view's map shows (events awaiting review on the review queue's map,
 * validated ones on the operations map; decision 0035).
 */
export function sourceCounts(source: RegistrySource, view: EventListView): string[] {
  const parts: string[] = [];
  if (source.pendingReviewCount) parts.push(`${count(source.pendingReviewCount)} awaiting review`);
  if (source.validatedCount) parts.push(`${count(source.validatedCount)} validated`);
  const shown = shownOnMap(view, { review: source.onMapReviewCount, operations: source.onMapOperationsCount });
  if (source.checkable || shown) parts.push(`${count(shown)} on this map`);
  return parts;
}

/**
 * The sources shown for a choice (decision 0035): those of the city, or of a
 * country entry and the cities within it (Canada: Canada's and Toronto's),
 * and those of no city in particular that are about its country or about no
 * country. A city never lists its country entry's sources (Toronto does not
 * list DriveBC), and a catalogue entry for another country is not listed.
 */
export function sourcesForCity(
  sources: RegistrySource[],
  area: { ids: string[]; country: string } | null,
): RegistrySource[] {
  if (area === null) return sources;
  return sources.filter(
    (source) =>
      (source.city !== null && area.ids.includes(source.city)) ||
      (source.city === null && (source.country === null || source.country === area.country)),
  );
}
