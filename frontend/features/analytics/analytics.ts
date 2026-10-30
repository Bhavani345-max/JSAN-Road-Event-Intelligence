import type { ApiAnalytics, ApiStatusGroups } from "@/types/api";

/**
 * The Analytics page's model (decision 0051). Every number comes from the API
 * (GET /api/events/analytics), which counts the stored events with the same
 * rules as the console's own counts; nothing here computes or invents one.
 */

export const STATUS_GROUPS = ["awaiting_review", "validated", "closed", "rejected"] as const;
export type StatusGroup = (typeof STATUS_GROUPS)[number];

export const STATUS_GROUP_LABELS: Record<StatusGroup, string> = {
  awaiting_review: "Awaiting validation",
  validated: "Validated",
  closed: "Closed",
  rejected: "Rejected",
};

export interface AnalyticsFilters {
  /** A city's or a country's id; null for all. */
  cityId: string | null;
  /** YYYY-MM-DD, the first and last day detected (inclusive), in `timeZone`; "" for open. */
  start: string;
  end: string;
  /** One event type, UNCLASSIFIED, or "" for all. */
  eventType: string;
  statusGroup: StatusGroup | "";
  sourceId: string;
}

export const DEFAULT_ANALYTICS_FILTERS: AnalyticsFilters = {
  cityId: null,
  start: "",
  end: "",
  eventType: "",
  statusGroup: "",
  sourceId: "",
};

/** The API query for the filters; days are read in `timeZone`. */
export function analyticsQuery(filters: AnalyticsFilters, timeZone: string): string {
  const params = new URLSearchParams({ tz: timeZone });
  if (filters.cityId) params.set("city", filters.cityId);
  if (filters.start) params.set("start", filters.start);
  if (filters.end) params.set("end", filters.end);
  if (filters.eventType) params.append("event_type", filters.eventType);
  if (filters.statusGroup) params.append("status_group", filters.statusGroup);
  if (filters.sourceId) params.append("source_id", filters.sourceId);
  return params.toString();
}

/** The date `days - 1` days before `today` and `today` itself (a range of `days` days), as YYYY-MM-DD in `timeZone`. */
export function lastDays(days: number, now: Date, timeZone: string): { start: string; end: string } {
  const day = (date: Date) =>
    new Intl.DateTimeFormat("en-CA", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" }).format(date);
  const end = day(now);
  // Calendar arithmetic on the date itself, so a time-zone shift never moves it.
  const [y, m, d] = end.split("-").map(Number);
  const start = new Date(Date.UTC(y, m - 1, d - (days - 1))).toISOString().slice(0, 10);
  return { start, end };
}

export interface Kpi {
  key: keyof ApiAnalytics["totals"];
  label: string;
  value: number;
  /** "of Total", "of Validated": what the share is taken of; null for the total itself. */
  shareOf: string | null;
  share: number | null;
  definition: string;
}

function share(part: number, whole: number): number | null {
  return whole > 0 ? part / whole : null;
}

/**
 * The KPI tiles in two rows: the status groups, mutually exclusive and adding
 * up to the total; then the subsets, which overlap them.
 */
export function kpis(data: ApiAnalytics): { exclusive: Kpi[]; subsets: Kpi[] } {
  const t = data.totals;
  const d = data.definitions;
  const group = (key: StatusGroup): Kpi => ({
    key,
    label: STATUS_GROUP_LABELS[key],
    value: t[key],
    shareOf: "of total",
    share: share(t[key], t.total),
    definition: d[key] ?? "",
  });
  return {
    exclusive: [
      { key: "total", label: "Total events", value: t.total, shareOf: null, share: null, definition: d.total ?? "" },
      ...STATUS_GROUPS.map(group),
    ],
    subsets: [
      {
        key: "published",
        label: "Published",
        value: t.published,
        shareOf: "of validated",
        share: share(t.published, t.validated),
        definition: d.published ?? "",
      },
      {
        key: "in_review_queue",
        label: "In the review queue",
        value: t.in_review_queue,
        shareOf: "of awaiting validation",
        share: share(t.in_review_queue, t.awaiting_review),
        definition: d.in_review_queue ?? "",
      },
      {
        key: "gis_pending",
        label: "GIS pending",
        value: t.gis_pending,
        shareOf: "of total",
        share: share(t.gis_pending, t.total),
        definition: d.gis_pending ?? "",
      },
    ],
  };
}

/** The `limit` largest rows, the rest summed as one "Other" row (never a dropped count). */
export function topWithOther<T extends { label: string; count: number }>(
  rows: readonly T[],
  limit: number,
  other: (count: number, rest: number) => T,
): T[] {
  if (rows.length <= limit) return [...rows];
  const rest = rows.slice(limit - 1);
  return [...rows.slice(0, limit - 1), other(rest.reduce((sum, row) => sum + row.count, 0), rest.length)];
}

export function groupTotal(groups: ApiStatusGroups): number {
  return STATUS_GROUPS.reduce((sum, group) => sum + groups[group], 0);
}

/** "43,432", as the console writes counts everywhere. */
export function formatCount(value: number): string {
  return value.toLocaleString("en-GB");
}

/** A share as a percentage that never rounds to "none" or "all" when it is neither. */
export function formatShare(value: number | null): string {
  if (value === null) return "–";
  const percent = value * 100;
  if (percent > 0 && percent < 0.1) return "<0.1%";
  if (percent > 99.9 && percent < 100) return ">99.9%";
  const digits = percent < 10 || percent >= 99.5 ? 1 : 0;
  return `${Number(percent.toFixed(digits))}%`;
}
