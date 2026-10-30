import { useEffect, useRef, useState } from "react";
import { ALL, setFilterCount, UNCLASSIFIED, type EventFilters as Filters, type TypeChoice } from "../filters";
import {
  EVENT_SEVERITIES,
  EVENT_TYPES,
  LOCATION_STATUSES,
  type EventSeverity,
  type EventStatus,
  type LocationStatus,
} from "../model";
import { EVENT_TYPE_LABELS, getSeverityLabel, getStatusLabel, LOCATION_STATUS_LABELS } from "../presentation";

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

interface MultiSelectProps<T extends string> {
  /** "Type", "Location": the box's name. */
  label: string;
  /** What several chosen are called: "types", "locations". */
  plural: string;
  choices: readonly { value: T; label: string }[];
  value: readonly T[];
  onChange: (value: T[]) => void;
}

const TYPE_CHOICES: { value: TypeChoice; label: string }[] = [
  ...EVENT_TYPES.map((type) => ({ value: type, label: EVENT_TYPE_LABELS[type] })),
  { value: UNCLASSIFIED, label: "Unclassified (no type yet)" },
];
const LOCATION_CHOICES = LOCATION_STATUSES.map((status) => ({
  value: status,
  label: LOCATION_STATUS_LABELS[status].label,
}));

/** Choose one or several values; none chosen means every one. */
function MultiSelect<T extends string>({ label, plural, choices, value, onChange }: MultiSelectProps<T>) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const labelOf = (choice: T) => choices.find((c) => c.value === choice)?.label ?? choice;
  const isSet = value.length > 0;
  const summary =
    value.length === 0
      ? `${label}: All`
      : value.length === 1
        ? labelOf(value[0])
        : `${value.length} ${plural}`;

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

  const toggle = (choice: T) =>
    onChange(value.includes(choice) ? value.filter((c) => c !== choice) : [...value, choice]);

  return (
    <div ref={root} className="relative min-w-0">
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={label}
        title={isSet ? value.map(labelOf).join(", ") : `Choose one or more ${plural}`}
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
          aria-label={label}
          className="absolute left-0 z-30 mt-1 max-h-64 w-56 overflow-y-auto rounded-lg bg-white p-1.5 text-xs text-slate-800 shadow-lg ring-1 ring-slate-900/10"
        >
          <div className="flex items-center justify-between px-1.5 pb-1 text-[11px] text-slate-500">
            <span>{value.length === 0 ? `All ${plural} shown` : `${value.length} chosen`}</span>
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
  // The filter boxes fold behind a button so the console fits one screen;
  // the button says how many are set, so a set filter is never out of sight.
  const [open, setOpen] = useState(false);
  const setCount = setFilterCount(filters);
  return (
    <div className="space-y-2">
      <div className="flex gap-1.5">
        <label className="relative block min-w-0 flex-1">
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
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
          aria-controls="event-filter-boxes"
          className={`flex h-9 shrink-0 cursor-pointer items-center gap-1.5 rounded-lg px-3 text-xs font-semibold shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70 ${
            setCount > 0
              ? "bg-brand-50 text-brand-700 ring-2 ring-sky-300"
              : "bg-white/10 text-white ring-1 ring-inset ring-white/20 hover:bg-white/20"
          }`}
        >
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-3.5 w-3.5" aria-hidden="true">
            <path d="M2.5 4h11M4.5 8h7M6.5 12h3" strokeLinecap="round" />
          </svg>
          {setCount > 0 ? `Filters · ${setCount}` : "Filters"}
        </button>
      </div>
      {open && (
        <div id="event-filter-boxes" className="grid grid-cols-2 gap-1.5">
          <FilterSelect<string>
            label="Source"
            allLabel="All Sources"
            value={filters.sourceId}
            options={sourceOptions.map((source) => source.id)}
            getLabel={(id) => sourceOptions.find((source) => source.id === id)?.name ?? id}
            onChange={(sourceId) => onChange({ ...filters, sourceId })}
          />
          <MultiSelect<TypeChoice>
            label="Type"
            plural="types"
            choices={TYPE_CHOICES}
            value={filters.eventTypes}
            onChange={(eventTypes) => onChange({ ...filters, eventTypes })}
          />
          {/* The same choice as the map toolbar's location filter: one state for both. */}
          <MultiSelect<LocationStatus>
            label="Location"
            plural="locations"
            choices={LOCATION_CHOICES}
            value={filters.locations}
            onChange={(locations) => onChange({ ...filters, locations })}
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
      )}
    </div>
  );
}
