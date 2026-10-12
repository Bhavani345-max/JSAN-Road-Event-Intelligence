import { useEffect, useRef, useState } from "react";
import { ALL, UNCLASSIFIED, type EventFilters as Filters, type TypeChoice } from "../filters";
import {
  EVENT_SEVERITIES,
  EVENT_TYPES,
  type EventSeverity,
  type EventStatus,
} from "../model";
import { EVENT_TYPE_LABELS, getSeverityLabel, getStatusLabel } from "../presentation";

interface EventFiltersProps {
  filters: Filters;
  /** Statuses to offer — only those present in the loaded events. */
  statusOptions: EventStatus[];
  /** Connected sources. A newly connected source appears here automatically. */
  sourceOptions: { id: string; name: string }[];
  onChange: (filters: Filters) => void;
}

interface FilterSelectProps<T extends string> {
  label: string;
  /** Wording of the "everything" choice. */
  allLabel?: string;
  value: T | typeof ALL;
  options: readonly T[];
  getLabel: (option: T) => string;
  onChange: (value: T | typeof ALL) => void;
}

function FilterSelect<T extends string>({
  label,
  allLabel,
  value,
  options,
  getLabel,
  onChange,
}: FilterSelectProps<T>) {
  const isSet = value !== ALL;
  return (
    <label className="min-w-0">
      <span className="sr-only">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as T | typeof ALL)}
        className={`h-9 w-full cursor-pointer truncate rounded-lg px-2 text-xs shadow-sm outline-none transition focus-visible:ring-2 focus-visible:ring-white/70 ${
          isSet
            ? "bg-brand-50 font-semibold text-brand-700 ring-2 ring-sky-300"
            : "bg-white text-slate-700 hover:bg-brand-50"
        }`}
      >
        <option value={ALL}>{allLabel ?? `${label}: All`}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {getLabel(option)}
          </option>
        ))}
      </select>
    </label>
  );
}

interface TypeMultiSelectProps {
  value: readonly TypeChoice[];
  onChange: (value: TypeChoice[]) => void;
}

/** Choose one or several event types; none chosen means every type. */
function TypeMultiSelect({ value, onChange }: TypeMultiSelectProps) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const choices: { value: TypeChoice; label: string }[] = [
    ...EVENT_TYPES.map((type) => ({ value: type, label: EVENT_TYPE_LABELS[type] })),
    { value: UNCLASSIFIED, label: "Unclassified (no type yet)" },
  ];
  const labelOf = (choice: TypeChoice) => choices.find((c) => c.value === choice)?.label ?? choice;
  const isSet = value.length > 0;
  const summary =
    value.length === 0
      ? "Type: All"
      : value.length === 1
        ? labelOf(value[0])
        : `${value.length} types`;

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (root.current && !root.current.contains(e.target as Node)) setOpen(false);
    };
    const escape = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);

  const toggle = (choice: TypeChoice) =>
    onChange(value.includes(choice) ? value.filter((c) => c !== choice) : [...value, choice]);

  return (
    <div ref={root} className="relative min-w-0">
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="Type"
        title={isSet ? value.map(labelOf).join(", ") : "Choose one or more event types"}
        onClick={() => setOpen((o) => !o)}
        className={`flex h-9 w-full cursor-pointer items-center justify-between gap-1 rounded-lg px-2 text-left text-xs shadow-sm outline-none transition focus-visible:ring-2 focus-visible:ring-white/70 ${
          isSet
            ? "bg-brand-50 font-semibold text-brand-700 ring-2 ring-sky-300"
            : "bg-white text-slate-700 hover:bg-brand-50"
        }`}
      >
        <span className="truncate">{summary}</span>
        <span aria-hidden="true" className="shrink-0 text-[10px]">
          {open ? "▲" : "▼"}
        </span>
      </button>
      {open && (
        <div
          role="listbox"
          aria-multiselectable="true"
          aria-label="Event types"
          className="absolute left-0 z-30 mt-1 max-h-64 w-56 overflow-y-auto rounded-lg bg-white p-1.5 text-xs text-slate-800 shadow-lg ring-1 ring-slate-900/10"
        >
          <div className="flex items-center justify-between px-1.5 pb-1 text-[11px] text-slate-500">
            <span>{value.length === 0 ? "All types shown" : `${value.length} chosen`}</span>
            {isSet && (
              <button
                type="button"
                onClick={() => onChange([])}
                className="cursor-pointer font-semibold text-brand-700 hover:underline"
              >
                Clear
              </button>
            )}
          </div>
          {choices.map((choice) => (
            <label
              key={choice.value}
              role="option"
              aria-selected={value.includes(choice.value)}
              className="flex cursor-pointer items-center gap-2 rounded px-1.5 py-1 hover:bg-brand-50"
            >
              <input
                type="checkbox"
                checked={value.includes(choice.value)}
                onChange={() => toggle(choice.value)}
                className="h-3.5 w-3.5 accent-brand-600"
              />
              <span className="truncate">{choice.label}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

interface DateTimeFilterProps {
  label: string;
  value: string;
  min?: string;
  max?: string;
  onChange: (value: string) => void;
}

function DateTimeFilter({ label, value, min, max, onChange }: DateTimeFilterProps) {
  const isSet = value !== "";
  return (
    <label
      className={`flex h-9 min-w-0 items-center gap-1.5 rounded-lg px-2 text-xs shadow-sm transition focus-within:ring-2 focus-within:ring-white/70 ${
        isSet
          ? "bg-brand-50 font-semibold text-brand-700 ring-2 ring-sky-300"
          : "bg-white text-slate-700 hover:bg-brand-50"
      }`}
    >
      <span className={isSet ? "" : "text-slate-500"}>{label}</span>
      <input
        type="datetime-local"
        value={value}
        min={min}
        max={max}
        onChange={(e) => onChange(e.target.value)}
        className="min-w-0 flex-1 cursor-pointer bg-transparent outline-none"
      />
    </label>
  );
}

export default function EventFilters({
  filters,
  statusOptions,
  sourceOptions,
  onChange,
}: EventFiltersProps) {
  return (
    <div className="space-y-2">
      <label className="relative block">
        <span className="sr-only">Search events, roads, places, sources and article text</span>
        <svg
          viewBox="0 0 20 20"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
          aria-hidden="true"
        >
          <circle cx="9" cy="9" r="5.5" />
          <path d="m13.5 13.5 3.5 3.5" strokeLinecap="round" />
        </svg>
        <input
          type="search"
          value={filters.search}
          onChange={(e) => onChange({ ...filters, search: e.target.value })}
          placeholder="Search events, roads, places, article text"
          className="h-9 w-full rounded-lg bg-white pl-9 pr-3 text-sm text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus-visible:ring-2 focus-visible:ring-white/70"
        />
      </label>
      <div className="grid grid-cols-2 gap-1.5">
        <FilterSelect<string>
          label="Source"
          allLabel="All Sources"
          value={filters.sourceId}
          options={sourceOptions.map((source) => source.id)}
          getLabel={(id) => sourceOptions.find((source) => source.id === id)?.name ?? id}
          onChange={(sourceId) => onChange({ ...filters, sourceId })}
        />
        <TypeMultiSelect
          value={filters.eventTypes}
          onChange={(eventTypes) => onChange({ ...filters, eventTypes })}
        />
        <FilterSelect<EventStatus>
          label="Status"
          value={filters.status}
          options={statusOptions}
          getLabel={getStatusLabel}
          onChange={(status) => onChange({ ...filters, status })}
        />
        <FilterSelect<EventSeverity>
          label="Severity"
          value={filters.severity}
          options={EVENT_SEVERITIES}
          getLabel={getSeverityLabel}
          onChange={(severity) => onChange({ ...filters, severity })}
        />
        <DateTimeFilter
          label="From"
          value={filters.from}
          max={filters.to || undefined}
          onChange={(from) => onChange({ ...filters, from })}
        />
        <DateTimeFilter
          label="To"
          value={filters.to}
          min={filters.from || undefined}
          onChange={(to) => onChange({ ...filters, to })}
        />
      </div>
      <label className="flex cursor-pointer items-center gap-2 text-xs text-white/80">
        <input
          type="checkbox"
          checked={filters.showHistory}
          onChange={(e) => onChange({ ...filters, showHistory: e.target.checked })}
          className="h-3.5 w-3.5 rounded border-white/40 bg-white/10 accent-white"
        />
        Show history (ended, rejected and old events)
      </label>
    </div>
  );
}
