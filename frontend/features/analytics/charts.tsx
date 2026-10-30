"use client";

import { useEffect, useRef, useState } from "react";
import type { ApiStatusGroups } from "@/types/api";
import { formatCount, formatShare, groupTotal, STATUS_GROUP_LABELS, STATUS_GROUPS, type StatusGroup } from "./analytics";

/**
 * The Analytics page's charts: plain SVG and HTML, no chart library. Colours
 * are roles (--viz-*, app/globals.css) with their own light and dark values.
 * Every chart labels its values or offers them in a table, so a tooltip is
 * never the only way to read a number.
 */

export interface BarRow {
  key: string;
  label: string;
  count: number;
  /** A small identity mark before the label (an event type's map colour). */
  marker?: React.ReactNode;
}

/** Hover help for one mark: follows the pointer within its chart. */
function Tooltip({ x, y, children }: { x: number; y: number; children: React.ReactNode }) {
  return (
    <div
      role="tooltip"
      className="rei-viz-tooltip pointer-events-none absolute z-10 w-max max-w-56 -translate-x-1/2 -translate-y-full rounded-lg bg-slate-900 px-2.5 py-1.5 text-[11px] leading-snug text-white shadow-lg"
      style={{ left: x, top: y - 8 }}
    >
      {children}
    </div>
  );
}

/** Horizontal bars of one measure, longest first, each with its value at its end. */
export function BarList({ rows, total, unit = "events" }: { rows: BarRow[]; total: number; unit?: string }) {
  const max = Math.max(1, ...rows.map((row) => row.count));
  const [hover, setHover] = useState<{ row: BarRow; x: number; y: number } | null>(null);
  const root = useRef<HTMLUListElement>(null);
  return (
    <ul ref={root} className="relative space-y-1.5" onMouseLeave={() => setHover(null)}>
      {rows.map((row) => (
        <li
          key={row.key}
          className="grid grid-cols-[minmax(0,11rem)_1fr_auto] items-center gap-3 rounded-md px-1 py-0.5 text-xs hover:bg-slate-50"
          aria-label={`${row.label}: ${formatCount(row.count)} ${unit} (${formatShare(row.count / Math.max(1, total))})`}
          onMouseMove={(event) => {
            const box = root.current?.getBoundingClientRect();
            if (box) setHover({ row, x: event.clientX - box.left, y: event.clientY - box.top });
          }}
        >
          <span className="flex min-w-0 items-center gap-1.5 text-slate-700" title={row.label}>
            {row.marker}
            <span className="truncate">{row.label}</span>
          </span>
          <span className="h-2.5 overflow-hidden" aria-hidden="true">
            <span
              className="block h-full rounded-r-[4px] bg-[var(--viz-series)]"
              style={{ width: `${Math.max(row.count > 0 ? 0.6 : 0, (row.count / max) * 100)}%` }}
            />
          </span>
          <span className="min-w-[3.5rem] text-right text-[11px] font-medium text-slate-600 tabular-nums">
            {formatCount(row.count)}
          </span>
        </li>
      ))}
      {hover && (
        <Tooltip x={hover.x} y={hover.y}>
          <span className="font-semibold">{hover.row.label}</span>
          <br />
          {formatCount(hover.row.count)} {unit} · {formatShare(hover.row.count / Math.max(1, total))} of {formatCount(total)}
        </Tooltip>
      )}
    </ul>
  );
}

const GROUP_ORDER: StatusGroup[] = ["validated", "awaiting_review", "rejected", "closed"];
const GROUP_VAR: Record<StatusGroup, string> = {
  validated: "var(--viz-validated)",
  awaiting_review: "var(--viz-awaiting)",
  rejected: "var(--viz-rejected)",
  closed: "var(--viz-closed)",
};
/** Status is never colour alone: each group also has its shape in the legend. */
const GROUP_ICON: Record<StatusGroup, string> = {
  validated: "✓",
  awaiting_review: "…",
  rejected: "✕",
  closed: "■",
};

export function StatusLegend() {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-600" aria-label="Legend">
      {GROUP_ORDER.map((group) => (
        <li key={group} className="flex items-center gap-1.5">
          <span
            className="flex h-3.5 w-3.5 items-center justify-center rounded-[4px] text-[9px] font-bold leading-none text-white"
            style={{ backgroundColor: GROUP_VAR[group] }}
            aria-hidden="true"
          >
            {GROUP_ICON[group]}
          </span>
          {STATUS_GROUP_LABELS[group]}
        </li>
      ))}
    </ul>
  );
}

export interface StackRow {
  key: string;
  label: string;
  groups: ApiStatusGroups;
}

/**
 * One 100% bar per row: the share of its events in each status group, with a
 * 2px gap between parts, and the row's total at its end. Proportions, so a
 * city with ten events reads as clearly as one with ten thousand.
 */
export function StackedBars({ rows }: { rows: StackRow[] }) {
  const [hover, setHover] = useState<{ row: StackRow; x: number; y: number } | null>(null);
  const root = useRef<HTMLUListElement>(null);
  return (
    <ul ref={root} className="relative space-y-2" onMouseLeave={() => setHover(null)}>
      {rows.map((row) => {
        const total = groupTotal(row.groups);
        return (
          <li
            key={row.key}
            className="grid grid-cols-[minmax(0,11rem)_1fr_auto] items-center gap-3 rounded-md px-1 py-0.5 text-xs hover:bg-slate-50"
            aria-label={`${row.label}: ${GROUP_ORDER.map((g) => `${STATUS_GROUP_LABELS[g]} ${formatCount(row.groups[g])}`).join(", ")}`}
            onMouseMove={(event) => {
              const box = root.current?.getBoundingClientRect();
              if (box) setHover({ row, x: event.clientX - box.left, y: event.clientY - box.top });
            }}
          >
            <span className="truncate text-slate-700" title={row.label}>
              {row.label}
            </span>
            <span className="flex h-2.5 gap-[2px]" aria-hidden="true">
              {GROUP_ORDER.filter((g) => row.groups[g] > 0).map((g, index, shown) => (
                <span
                  key={g}
                  className={`h-full ${index === shown.length - 1 ? "rounded-r-[4px]" : ""}`}
                  style={{ flexGrow: row.groups[g], flexBasis: 0, minWidth: 2, backgroundColor: GROUP_VAR[g] }}
                />
              ))}
            </span>
            <span className="min-w-[3.5rem] text-right text-[11px] font-medium text-slate-600 tabular-nums">
              {formatCount(total)}
            </span>
          </li>
        );
      })}
      {hover && (
        <Tooltip x={hover.x} y={hover.y}>
          <span className="font-semibold">{hover.row.label}</span>
          {GROUP_ORDER.map((g) => (
            <span key={g} className="block">
              {STATUS_GROUP_LABELS[g]}: {formatCount(hover.row.groups[g])} (
              {formatShare(hover.row.groups[g] / Math.max(1, groupTotal(hover.row.groups)))})
            </span>
          ))}
        </Tooltip>
      )}
    </ul>
  );
}

/** The element's width, followed as it resizes (charts draw in real pixels). */
function useWidth<T extends HTMLElement>(): [React.RefObject<T | null>, number] {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  return [ref, width];
}

/** 0, and up to four round steps to just above `max`. */
function niceTicks(max: number): number[] {
  if (max <= 0) return [0];
  const rough = max / 4;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => s >= rough) ?? rough;
  const ticks = [];
  for (let value = 0; value <= max + step * 0.001; value += step) ticks.push(Math.round(value));
  if (ticks[ticks.length - 1] < max) ticks.push(Math.round(ticks[ticks.length - 1] + step));
  return ticks;
}

function dayLabel(date: string, withYear = false): string {
  const [y, m, d] = date.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-GB", {
    timeZone: "UTC",
    day: "numeric",
    month: "short",
    ...(withYear ? { year: "numeric" } : {}),
    ...(withYear ? { weekday: "short" } : {}),
  });
}

/** Events detected per day: one line on a zero baseline, with a crosshair and the day's count on hover. */
export function DayChart({ days }: { days: { date: string; count: number }[] }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);
  const height = 200;
  const pad = { top: 12, right: 12, bottom: 24, left: 44 };
  const ticks = niceTicks(Math.max(0, ...days.map((d) => d.count)));
  const top = ticks[ticks.length - 1] || 1;
  const plotW = Math.max(1, width - pad.left - pad.right);
  const plotH = height - pad.top - pad.bottom;
  const x = (index: number) => pad.left + (days.length === 1 ? plotW / 2 : (index / (days.length - 1)) * plotW);
  const y = (value: number) => pad.top + plotH - (value / top) * plotH;
  const line = days.map((d, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(d.count).toFixed(1)}`).join("");
  const area = days.length > 1 ? `${line}L${x(days.length - 1)},${y(0)}L${x(0)},${y(0)}Z` : "";
  const labelIndexes = days.length <= 1 ? [0] : [0, Math.floor((days.length - 1) / 2), days.length - 1];
  const hovered = hover !== null ? days[hover] : null;

  return (
    <div ref={ref} className="relative w-full" style={{ height }}>
      {width > 0 && (
        <svg
          width={width}
          height={height}
          role="img"
          aria-label={`Events detected per day, ${dayLabel(days[0].date, true)} to ${dayLabel(days[days.length - 1].date, true)}`}
          onMouseMove={(event) => {
            const box = event.currentTarget.getBoundingClientRect();
            const relative = (event.clientX - box.left - pad.left) / plotW;
            setHover(Math.min(days.length - 1, Math.max(0, Math.round(relative * (days.length - 1)))));
          }}
          onMouseLeave={() => setHover(null)}
        >
          {ticks.map((tick) => (
            <g key={tick}>
              <line x1={pad.left} x2={width - pad.right} y1={y(tick)} y2={y(tick)} stroke="var(--viz-grid)" strokeWidth={1} />
              <text x={pad.left - 8} y={y(tick)} dy="0.32em" textAnchor="end" fontSize={10} fill="var(--viz-muted)">
                {formatCount(tick)}
              </text>
            </g>
          ))}
          <line x1={pad.left} x2={width - pad.right} y1={y(0)} y2={y(0)} stroke="var(--viz-axis)" strokeWidth={1} />
          {area && <path d={area} fill="var(--viz-series)" opacity={0.12} />}
          {days.length > 1 ? (
            <path d={line} fill="none" stroke="var(--viz-series)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
          ) : (
            <circle cx={x(0)} cy={y(days[0].count)} r={4} fill="var(--viz-series)" />
          )}
          {labelIndexes.map((index) => (
            <text
              key={index}
              x={x(index)}
              y={height - 6}
              fontSize={10}
              fill="var(--viz-muted)"
              textAnchor={index === 0 ? "start" : index === days.length - 1 ? "end" : "middle"}
            >
              {dayLabel(days[index].date)}
            </text>
          ))}
          {hovered && hover !== null && (
            <g>
              <line x1={x(hover)} x2={x(hover)} y1={pad.top} y2={y(0)} stroke="var(--viz-axis)" strokeWidth={1} />
              <circle cx={x(hover)} cy={y(hovered.count)} r={4} fill="var(--viz-series)" stroke="var(--viz-surface)" strokeWidth={2} />
            </g>
          )}
        </svg>
      )}
      {hovered && hover !== null && (
        <Tooltip x={Math.min(Math.max(x(hover), 70), width - 70)} y={y(hovered.count)}>
          <span className="font-semibold">{dayLabel(hovered.date, true)}</span>
          <br />
          {formatCount(hovered.count)} events detected
        </Tooltip>
      )}
    </div>
  );
}

/** The chart's numbers as a table: every value readable without the chart or a pointer. */
export function DataTable({ head, rows }: { head: string[]; rows: (string | number)[][] }) {
  return (
    <details className="mt-3 text-xs">
      <summary className="cursor-pointer select-none text-[11px] font-semibold text-brand-700 hover:underline">
        Show as a table
      </summary>
      <div className="mt-2 max-h-64 overflow-auto rounded-lg ring-1 ring-inset ring-slate-200">
        <table className="w-full border-collapse text-left">
          <thead className="sticky top-0 bg-slate-50 text-[11px] text-slate-500">
            <tr>
              {head.map((cell, index) => (
                <th key={cell} className={`px-2.5 py-1.5 font-semibold ${index > 0 ? "text-right" : ""}`}>
                  {cell}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={String(row[0])} className="border-t border-slate-100">
                {row.map((cell, index) => (
                  <td key={index} className={`px-2.5 py-1 ${index > 0 ? "text-right tabular-nums" : "text-slate-700"}`}>
                    {typeof cell === "number" ? formatCount(cell) : cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

export { GROUP_ORDER, STATUS_GROUPS };
