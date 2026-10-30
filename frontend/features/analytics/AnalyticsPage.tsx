"use client";

import Image from "next/image";
import Link from "next/link";
import { useMemo, useState, type CSSProperties } from "react";
import { useAuth } from "@/features/auth/AuthGate";
import { canManageAccounts } from "@/features/auth/permissions";
import { groupByCountry, useCities } from "@/features/cities/cities";
import { useSources } from "@/features/dashboard/sources";
import { EVENT_TYPES, type EventStatus, type EventType, type LocationStatus } from "@/features/events/model";
import {
  EVENT_TYPE_LABELS,
  getEventTypeColor,
  getStatusLabel,
  LOCATION_STATUS_LABELS,
} from "@/features/events/presentation";
import { themeStyle, useTheme } from "@/features/theme/themes";
import AppearanceToggle from "@/features/theme/AppearanceToggle";
import {
  analyticsQuery,
  DEFAULT_ANALYTICS_FILTERS,
  formatCount,
  formatShare,
  kpis,
  lastDays,
  STATUS_GROUP_LABELS,
  STATUS_GROUPS,
  topWithOther,
  type AnalyticsFilters,
  type Kpi,
  type StatusGroup,
} from "./analytics";
import { BarList, DataTable, DayChart, StackedBars, StatusLegend, type BarRow } from "./charts";
import { useAnalytics } from "./useAnalytics";

const CONTROL =
  "h-9 min-w-0 rounded-lg bg-white px-2.5 text-xs text-slate-700 shadow-sm ring-1 ring-inset ring-slate-200 outline-none transition hover:ring-slate-300 focus-visible:ring-2 focus-visible:ring-brand-500";
const SET_CONTROL = "font-semibold text-brand-700 ring-2 ring-brand-300";

function ChartCard({
  title,
  description,
  children,
  wide = false,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  wide?: boolean;
}) {
  return (
    <section
      className={`rei-viz-card rounded-xl bg-white p-4 shadow-[0_1px_2px_rgb(15_23_42/0.06)] ring-1 ring-slate-900/5 ${wide ? "lg:col-span-2" : ""}`}
    >
      <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
      <p className="mt-0.5 text-[11px] leading-snug text-slate-500">{description}</p>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function KpiTile({ kpi, tone }: { kpi: Kpi; tone: "total" | "group" | "subset" }) {
  return (
    <div
      data-kpi={kpi.key}
      className={`rounded-xl p-3.5 ring-1 ring-inset ${
        tone === "total" ? "bg-brand-600 text-white ring-brand-700" : "bg-white ring-slate-200"
      }`}
    >
      <p className={`flex items-center gap-1 text-[11px] font-semibold ${tone === "total" ? "text-white/85" : "text-slate-500"}`}>
        {kpi.label}
        <span
          className={`flex h-3.5 w-3.5 cursor-help items-center justify-center rounded-full text-[9px] font-bold ring-1 ring-inset ${
            tone === "total" ? "ring-white/50" : "ring-slate-300 text-slate-400"
          }`}
          title={kpi.definition}
          aria-label={`How it is counted: ${kpi.definition}`}
          role="img"
        >
          i
        </span>
      </p>
      <p data-kpi-value className={`mt-1 text-2xl font-semibold tracking-tight ${tone === "total" ? "text-white" : "text-slate-900"}`}>
        {formatCount(kpi.value)}
      </p>
      <p className={`mt-0.5 text-[11px] ${tone === "total" ? "text-white/75" : "text-slate-500"}`}>
        {kpi.shareOf ? `${formatShare(kpi.share)} ${kpi.shareOf}` : "= the four groups below added up"}
      </p>
    </div>
  );
}

/** The console's Analytics: counts of the stored events, from the API, with their definitions. */
export default function AnalyticsPage() {
  const { user } = useAuth();
  const theme = useTheme();
  const cities = useCities();
  const { sources } = useSources();
  const [filters, setFilters] = useState<AnalyticsFilters>(DEFAULT_ANALYTICS_FILTERS);
  const groups = useMemo(() => groupByCountry(cities), [cities]);
  const place = cities.find((city) => city.id === filters.cityId) ?? null;
  // Days, and the date range, in the chosen place's zone; UTC for all countries.
  const timeZone = place?.timeZone ?? "UTC";
  const query = analyticsQuery(filters, timeZone);
  const { data, loading, error, retry } = useAnalytics(query);
  const sourceOptions = useMemo(
    () => sources.filter((source) => source.candidateCount > 0).sort((a, b) => a.name.localeCompare(b.name)),
    [sources],
  );
  const set = (change: Partial<AnalyticsFilters>) => setFilters((current) => ({ ...current, ...change }));
  const filtered = JSON.stringify(filters) !== JSON.stringify(DEFAULT_ANALYTICS_FILTERS);
  const preset = (days: number) => set(lastDays(days, new Date(), timeZone));
  const presetActive = (days: number) => {
    const range = lastDays(days, new Date(), timeZone);
    return filters.start === range.start && filters.end === range.end;
  };

  const total = data?.totals.total ?? 0;
  const tiles = data ? kpis(data) : null;
  const cityRows = data
    ? topWithOther<BarRow>(
        data.by_city.map((row) => ({ key: row.key, label: row.key, count: row.count })),
        12,
        (count, rest) => ({ key: "__other", label: `Other (${rest} places)`, count }),
      )
    : [];
  const categoryRows: BarRow[] = data
    ? data.by_category.map((row) => ({
        key: row.key,
        label: row.key === "UNCLASSIFIED" ? "Unclassified" : (EVENT_TYPE_LABELS[row.key as EventType] ?? row.key),
        count: row.count,
        marker: (
          <span
            className="h-2 w-2 shrink-0 rounded-full"
            style={{ backgroundColor: getEventTypeColor(row.key === "UNCLASSIFIED" ? null : (row.key as EventType)) }}
            aria-hidden="true"
          />
        ),
      }))
    : [];
  const locationRows: BarRow[] = data
    ? data.by_location.map((row) => ({
        key: row.key,
        label: LOCATION_STATUS_LABELS[row.key as LocationStatus]?.label ?? "Located, no class recorded",
        count: row.count,
      }))
    : [];
  const statusRows: BarRow[] = data
    ? data.by_status.map((row) => ({ key: row.key, label: getStatusLabel(row.key as EventStatus), count: row.count }))
    : [];
  const cityStacks = data ? data.validation_by_city.slice(0, 12).map((row) => ({ key: row.key, label: row.key, groups: row })) : [];
  const sourceStacks = data
    ? data.by_source.slice(0, 12).map((row) => ({ key: row.source_id, label: row.source_name, groups: row }))
    : [];
  const days = data?.by_day ?? [];

  return (
    <div className="rei-app min-h-dvh bg-slate-50 text-slate-900" style={themeStyle(theme) as CSSProperties}>
      <header className="sticky top-0 z-20 flex h-14 items-center justify-between gap-3 border-b border-slate-200 bg-white px-4">
        <div className="flex min-w-0 items-center gap-3">
          <Image src="/jsan-mark.png" alt="JSAN" width={36} height={36} className="h-9 w-9 shrink-0" />
          <h1 className="truncate text-[15px] font-semibold tracking-tight text-brand-800">
            <span className="max-sm:sr-only">JSAN Road Event Intelligence · </span>Analytics
          </h1>
        </div>
        <nav className="flex shrink-0 items-center gap-2" aria-label="Pages">
          <Link
            href="/"
            className="flex h-8 items-center rounded-lg px-2.5 text-[11px] font-semibold text-slate-600 ring-1 ring-inset ring-slate-200 transition hover:bg-slate-50 hover:text-slate-900"
          >
            Console
          </Link>
          {canManageAccounts(user) && (
            <Link
              href="/users"
              className="hidden h-8 items-center rounded-lg px-2.5 text-[11px] font-semibold text-slate-600 ring-1 ring-inset ring-slate-200 transition hover:bg-slate-50 hover:text-slate-900 sm:flex"
            >
              Users
            </Link>
          )}
          <AppearanceToggle />
        </nav>
      </header>

      <main className="mx-auto max-w-7xl space-y-4 px-4 py-4">
        {/* Filters: one row above everything they change. */}
        <section aria-label="Filters" className="rei-viz-card rounded-xl bg-white p-3 ring-1 ring-slate-900/5">
          <div className="flex flex-wrap items-center gap-2">
            <label className="min-w-0">
              <span className="sr-only">Country or city</span>
              <select
                value={filters.cityId ?? ""}
                onChange={(event) => set({ cityId: event.target.value || null })}
                className={`${CONTROL} ${filters.cityId ? SET_CONTROL : ""} max-w-56`}
              >
                <option value="">All countries</option>
                {groups.map((group) => (
                  <optgroup key={group.country} label={group.name}>
                    {group.entry && <option value={group.entry.id}>All of {group.entry.name}</option>}
                    {group.cities.map((city) => (
                      <option key={city.id} value={city.id}>
                        {city.name}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </label>
            <div role="group" aria-label="Detected" className="flex items-center gap-1 rounded-lg bg-slate-100 p-0.5">
              {[7, 30, 90].map((days) => (
                <button
                  key={days}
                  type="button"
                  aria-pressed={presetActive(days)}
                  onClick={() => preset(days)}
                  className={`h-8 cursor-pointer rounded-md px-2.5 text-[11px] font-semibold transition ${
                    presetActive(days) ? "bg-white text-brand-700 shadow-sm" : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  {days} days
                </button>
              ))}
              <button
                type="button"
                aria-pressed={!filters.start && !filters.end}
                onClick={() => set({ start: "", end: "" })}
                className={`h-8 cursor-pointer rounded-md px-2.5 text-[11px] font-semibold transition ${
                  !filters.start && !filters.end ? "bg-white text-brand-700 shadow-sm" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                All time
              </button>
            </div>
            <label className="flex items-center gap-1 text-[11px] text-slate-500">
              From
              <input
                type="date"
                value={filters.start}
                max={filters.end || undefined}
                onChange={(event) => set({ start: event.target.value })}
                className={`${CONTROL} ${filters.start ? SET_CONTROL : ""}`}
              />
            </label>
            <label className="flex items-center gap-1 text-[11px] text-slate-500">
              To
              <input
                type="date"
                value={filters.end}
                min={filters.start || undefined}
                onChange={(event) => set({ end: event.target.value })}
                className={`${CONTROL} ${filters.end ? SET_CONTROL : ""}`}
              />
            </label>
            <label className="min-w-0">
              <span className="sr-only">Category</span>
              <select
                value={filters.eventType}
                onChange={(event) => set({ eventType: event.target.value })}
                className={`${CONTROL} ${filters.eventType ? SET_CONTROL : ""} max-w-48`}
              >
                <option value="">All categories</option>
                {EVENT_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {EVENT_TYPE_LABELS[type]}
                  </option>
                ))}
                <option value="UNCLASSIFIED">Unclassified</option>
              </select>
            </label>
            <label className="min-w-0">
              <span className="sr-only">Validation status</span>
              <select
                value={filters.statusGroup}
                onChange={(event) => set({ statusGroup: event.target.value as StatusGroup | "" })}
                className={`${CONTROL} ${filters.statusGroup ? SET_CONTROL : ""}`}
              >
                <option value="">All statuses</option>
                {STATUS_GROUPS.map((group) => (
                  <option key={group} value={group}>
                    {STATUS_GROUP_LABELS[group]}
                  </option>
                ))}
              </select>
            </label>
            <label className="min-w-0">
              <span className="sr-only">Source</span>
              <select
                value={filters.sourceId}
                onChange={(event) => set({ sourceId: event.target.value })}
                className={`${CONTROL} ${filters.sourceId ? SET_CONTROL : ""} max-w-56`}
              >
                <option value="">All sources</option>
                {sourceOptions.map((source) => (
                  <option key={source.id} value={source.id}>
                    {source.name}
                  </option>
                ))}
              </select>
            </label>
            {filtered && (
              <button
                type="button"
                onClick={() => setFilters(DEFAULT_ANALYTICS_FILTERS)}
                className="h-9 cursor-pointer rounded-lg px-2.5 text-[11px] font-semibold text-brand-700 hover:underline"
              >
                Reset
              </button>
            )}
            <p className="ml-auto text-[11px] text-slate-500" aria-live="polite">
              {loading && data ? "Updating…" : `Days in ${timeZone === "UTC" ? "UTC" : timeZone}`}
            </p>
          </div>
        </section>

        {error && (
          <div role="alert" className="flex items-center justify-between gap-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800 ring-1 ring-inset ring-red-200">
            <span>The analytics could not be loaded: {error}</span>
            <button type="button" onClick={retry} className="cursor-pointer text-xs font-semibold underline">
              Try again
            </button>
          </div>
        )}

        {!data && !error && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5" aria-busy="true" aria-label="Loading">
            {Array.from({ length: 10 }, (_, i) => (
              <div key={i} className="h-24 animate-pulse rounded-xl bg-slate-200/70" />
            ))}
          </div>
        )}

        {data && tiles && (
          <div className={`space-y-4 transition-opacity ${loading ? "opacity-70" : ""}`}>
            <section aria-label="Events by status group">
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                By status: each event in exactly one group; the groups add up to the total
              </p>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
                {tiles.exclusive.map((kpi) => (
                  <KpiTile key={kpi.key} kpi={kpi} tone={kpi.key === "total" ? "total" : "group"} />
                ))}
              </div>
            </section>
            <section aria-label="Subsets">
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Subsets: these overlap the groups above and are not added to them
              </p>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {tiles.subsets.map((kpi) => (
                  <KpiTile key={kpi.key} kpi={kpi} tone="subset" />
                ))}
              </div>
            </section>

            {total === 0 ? (
              <div className="rounded-xl bg-white px-6 py-12 text-center ring-1 ring-slate-900/5">
                <p className="text-sm font-semibold text-slate-800">No events match these filters</p>
                <p className="mt-1 text-xs text-slate-500">Widen the date range or clear a filter.</p>
              </div>
            ) : (
              <div className="grid gap-4 lg:grid-cols-2">
                <ChartCard
                  wide
                  title="Events detected over time"
                  description={`Events by the day REI stored them, in ${data.time_zone}. ${formatCount(total)} events in all.`}
                >
                  {days.length > 0 && <DayChart days={days} />}
                  <DataTable head={["Day", "Events"]} rows={days.map((d) => [d.date, d.count])} />
                </ChartCard>
                <ChartCard title="Events by city" description="Where the events are, by the city each records. The largest 11, the rest as Other.">
                  <BarList rows={cityRows} total={total} />
                  <DataTable head={["City", "Events"]} rows={data.by_city.map((r) => [r.key, r.count])} />
                </ChartCard>
                <ChartCard title="Events by category" description="The event type each was classified as; Unclassified when its source did not make the kind clear.">
                  <BarList rows={categoryRows} total={total} />
                  <DataTable head={["Category", "Events"]} rows={categoryRows.map((r) => [r.label, r.count])} />
                </ChartCard>
                <ChartCard title="Validation progress" description="Share of each city's events in each status group (largest 12 cities). The number is the city's total.">
                  <StatusLegend />
                  <div className="mt-3">
                    <StackedBars rows={cityStacks} />
                  </div>
                  <DataTable
                    head={["City", ...STATUS_GROUPS.map((g) => STATUS_GROUP_LABELS[g])]}
                    rows={data.validation_by_city.map((r) => [r.key, ...STATUS_GROUPS.map((g) => r[g])])}
                  />
                </ChartCard>
                <ChartCard title="Source performance" description="Each source's events and how reviewers decided them (largest 12 sources). The number is the source's total.">
                  <StatusLegend />
                  <div className="mt-3">
                    <StackedBars rows={sourceStacks} />
                  </div>
                  <DataTable
                    head={["Source", "Events", ...STATUS_GROUPS.map((g) => STATUS_GROUP_LABELS[g])]}
                    rows={data.by_source.map((r) => [r.source_name, r.total, ...STATUS_GROUPS.map((g) => r[g])])}
                  />
                </ChartCard>
                <ChartCard title="GIS resolution" description="How each event was located: by its source, matched to the road network, corrected by a reviewer, only approximately, or not at all.">
                  <BarList rows={locationRows} total={total} />
                  <DataTable head={["Location", "Events"]} rows={locationRows.map((r) => [r.label, r.count])} />
                </ChartCard>
                <ChartCard title="Event status" description="Every lifecycle status the events hold now.">
                  <BarList rows={statusRows} total={total} />
                  <DataTable head={["Status", "Events"]} rows={statusRows.map((r) => [r.label, r.count])} />
                </ChartCard>
              </div>
            )}

            <details className="rei-viz-card rounded-xl bg-white p-4 text-xs ring-1 ring-slate-900/5">
              <summary className="cursor-pointer select-none text-sm font-semibold text-slate-900">
                How these numbers are counted
              </summary>
              <dl className="mt-3 grid gap-x-6 gap-y-2 sm:grid-cols-2">
                {Object.entries(data.definitions).map(([key, text]) => (
                  <div key={key}>
                    <dt className="font-semibold text-slate-700">
                      {{ total: "Total events", awaiting_review: "Awaiting validation", validated: "Validated", closed: "Closed", rejected: "Rejected", published: "Published", in_review_queue: "In the review queue", gis_pending: "GIS pending", detected_over_time: "Detected over time" }[key] ?? key}
                    </dt>
                    <dd className="text-slate-500">{text}</dd>
                  </div>
                ))}
                <div>
                  <dt className="font-semibold text-slate-700">Merged reports</dt>
                  <dd className="text-slate-500">
                    {formatCount(data.totals.merged)} reports merged into another event are part of that event and not counted again.
                  </dd>
                </div>
              </dl>
              <p className="mt-3 text-[11px] text-slate-400">
                Counted by the REI API from the stored events at {new Date(data.generated_at).toLocaleString("en-GB")} (read only).
              </p>
            </details>
          </div>
        )}
      </main>
    </div>
  );
}
