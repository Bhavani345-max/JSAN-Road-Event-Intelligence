import { useEffect, useRef, useState } from "react";
import type { TypeChoice } from "@/features/events/filters";
import type { LocationStatus } from "@/features/events/model";
import type { GisStatus } from "@/features/events/presentation";
import { BASEMAPS, type Basemap } from "@/lib/config";
import type { MapLayers } from "../layers";

/** One choice of a filter, with how many events it would show (given the other filters). */
export interface FacetOption<T extends string> {
  value: T;
  label: string;
  count: number;
  /** A category's map colour. */
  color?: string;
  /** A location status's tone. */
  tone?: GisStatus["tone"];
}

interface MapToolbarProps {
  basemap: Basemap;
  onBasemapChange: (basemap: Basemap) => void;
  layers: MapLayers;
  onLayersChange: (layers: MapLayers) => void;
  /** Categories of the loaded events (the backend's own), with counts. */
  typeOptions: FacetOption<TypeChoice>[];
  selectedTypes: readonly TypeChoice[];
  onTypesChange: (types: TypeChoice[]) => void;
  locationOptions: FacetOption<LocationStatus>[];
  selectedLocations: readonly LocationStatus[];
  onLocationsChange: (locations: LocationStatus[]) => void;
  /** Clears the categories and location statuses chosen (here or in the sidebar). */
  onClearAll: () => void;
  /** Events the filters leave, as the list shows them; and of those, the ones the map draws. */
  matchCount: number;
  onMapCount: number;
  /** Filters set only in the sidebar (search, source, status, severity, dates). */
  otherFilterCount: number;
  /** The overview of all countries: nothing to filter until a country is chosen. */
  filtersDisabled?: boolean;
}

const BASEMAP_LABELS: Record<Basemap, string> = { map: "Map", satellite: "Satellite" };

const TONE_DOT: Record<GisStatus["tone"], string> = {
  exact: "bg-emerald-500",
  approximate: "bg-white ring-2 ring-inset ring-amber-500",
  pending: "bg-sky-500",
  none: "bg-slate-300",
};

const PANEL_CLASS =
  // On a phone the map is 42dvh tall: the panel ends above its bottom controls.
  "rei-map-panel w-[min(20rem,calc(100vw-1.5rem))] overflow-y-auto overscroll-contain rounded-xl bg-white/97 p-3 text-xs text-slate-700 shadow-lg ring-1 ring-slate-900/10 backdrop-blur max-h-[calc(42dvh-6.5rem)] wide:max-h-[calc(100dvh-12rem)] sideways:max-h-[calc(100dvh-10rem)]";

function ToolbarButton({
  label,
  icon,
  open,
  badge,
  disabled,
  title,
  onClick,
}: {
  label: string;
  icon: React.ReactNode;
  open: boolean;
  badge?: number;
  disabled?: boolean;
  title?: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-expanded={open}
      title={title}
      className={`relative flex h-8 cursor-pointer items-center gap-1.5 rounded-lg px-2.5 text-xs font-semibold outline-none transition focus-visible:ring-2 focus-visible:ring-brand-400 disabled:cursor-not-allowed disabled:opacity-50 ${
        open ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
      }`}
    >
      {icon}
      <span className="max-sm:sr-only">{label}</span>
      {badge ? (
        <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-brand-600 px-1 text-[10px] font-bold text-white">
          {badge}
        </span>
      ) : null}
    </button>
  );
}

function Chip<T extends string>({
  option,
  selected,
  onToggle,
}: {
  option: FacetOption<T>;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onToggle}
      title={`${option.label}: ${option.count} event${option.count === 1 ? "" : "s"}`}
      className={`inline-flex max-w-full cursor-pointer items-center gap-1.5 rounded-full py-1 pl-2 pr-2.5 text-[11px] font-medium ring-1 ring-inset transition outline-none focus-visible:ring-2 focus-visible:ring-brand-400 ${
        selected
          ? "bg-brand-600 text-white ring-brand-600"
          : "bg-white text-slate-700 ring-slate-200 hover:bg-slate-50 hover:ring-slate-300"
      }`}
    >
      {option.color ? (
        <span className="h-2 w-2 shrink-0 rounded-full ring-1 ring-white/70" style={{ backgroundColor: option.color }} />
      ) : option.tone ? (
        <span className={`h-2 w-2 shrink-0 rounded-full ${TONE_DOT[option.tone]}`} />
      ) : null}
      <span className="truncate">{option.label}</span>
      <span className={`tabular-nums ${selected ? "text-white/80" : "text-slate-400"}`}>{option.count}</span>
    </button>
  );
}

function Switch({
  label,
  hint,
  checked,
  disabled,
  onChange,
}: {
  label: string;
  hint: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className={`flex items-start gap-3 rounded-lg px-1 py-1.5 ${disabled ? "opacity-50" : "cursor-pointer"}`}>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`relative mt-0.5 inline-flex h-4 w-7 shrink-0 cursor-pointer items-center rounded-full transition outline-none focus-visible:ring-2 focus-visible:ring-brand-400 disabled:cursor-not-allowed ${
          checked ? "bg-brand-600" : "bg-slate-300"
        }`}
      >
        <span
          className={`rei-switch-knob h-3 w-3 rounded-full bg-white shadow-sm transition-transform ${checked ? "translate-x-3.5" : "translate-x-0.5"}`}
        />
      </button>
      <span>
        <span className="block font-semibold text-slate-800">{label}</span>
        <span className="block text-[11px] leading-snug text-slate-500">{hint}</span>
      </span>
    </label>
  );
}

const FILTER_ICON = (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-3.5 w-3.5" aria-hidden="true">
    <path d="M2.5 3.5h11l-4.2 5v3.8l-2.6 1.2v-5l-4.2-5Z" strokeLinejoin="round" />
  </svg>
);
const LAYERS_ICON = (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-3.5 w-3.5" aria-hidden="true">
    <path d="m8 2 6 3-6 3-6-3 6-3Z" strokeLinejoin="round" />
    <path d="m2 8 6 3 6-3M2 11l6 3 6-3" strokeLinejoin="round" />
  </svg>
);

/**
 * The map's floating toolbar: basemap, filters and layers. Its filters are the
 * console's own (one state with the sidebar's Filters), so the list, the counts
 * and the map always show the same events. Its panels open below it, in the
 * map's top-left column, pushing the legend down instead of covering it.
 */
export default function MapToolbar(props: MapToolbarProps) {
  const {
    basemap, onBasemapChange, layers, onLayersChange,
    typeOptions, selectedTypes, onTypesChange,
    locationOptions, selectedLocations, onLocationsChange,
    onClearAll, matchCount, onMapCount, otherFilterCount, filtersDisabled = false,
  } = props;
  const [open, setOpen] = useState<"filters" | "layers" | null>(null);
  const root = useRef<HTMLDivElement>(null);
  const activeCount = selectedTypes.length + selectedLocations.length;

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => {
      if (root.current && !root.current.contains(event.target as Node)) setOpen(null);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(null);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);

  const toggle = <T extends string>(list: readonly T[], value: T): T[] =>
    list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
  // Chosen but no longer offered never happens (stale choices are dropped);
  // offered: what the loaded events hold.
  const shownTypes = typeOptions.filter((o) => o.count > 0 || selectedTypes.includes(o.value));
  const shownLocations = locationOptions.filter((o) => o.count > 0 || selectedLocations.includes(o.value));

  return (
    <div ref={root} className="pointer-events-auto flex flex-col items-start gap-2">
      <div
        role="toolbar"
        aria-label="Map tools"
        className="rei-map-toolbar flex items-center gap-1 rounded-xl bg-white/95 p-1 shadow-md ring-1 ring-slate-900/10 backdrop-blur"
      >
        <div role="group" aria-label="Basemap" className="flex rounded-lg bg-slate-100/80 p-0.5">
          {BASEMAPS.map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={option === basemap}
              onClick={() => onBasemapChange(option)}
              className={`cursor-pointer rounded-md px-2.5 py-1 text-xs font-semibold outline-none transition focus-visible:ring-2 focus-visible:ring-brand-400 ${
                option === basemap ? "bg-brand-600 text-white shadow-sm" : "text-slate-600 hover:text-brand-700"
              }`}
            >
              {BASEMAP_LABELS[option]}
            </button>
          ))}
        </div>
        <span className="mx-0.5 h-5 w-px bg-slate-200" aria-hidden="true" />
        <ToolbarButton
          label="Filters"
          icon={FILTER_ICON}
          open={open === "filters"}
          badge={activeCount}
          disabled={filtersDisabled}
          title={filtersDisabled ? "Choose a country to filter its events" : "Filter the events by category and location"}
          onClick={() => setOpen(open === "filters" ? null : "filters")}
        />
        <ToolbarButton
          label="Layers"
          icon={LAYERS_ICON}
          open={open === "layers"}
          title="Markers, clusters and heatmap"
          onClick={() => setOpen(open === "layers" ? null : "layers")}
        />
      </div>

      {open === "filters" && !filtersDisabled && (
        <div className={PANEL_CLASS} role="dialog" aria-label="Map filters">
          <div className="flex items-start justify-between gap-3">
            <p className="text-[11px] leading-snug text-slate-500">
              <span className="font-semibold text-slate-800 tabular-nums">{matchCount}</span>{" "}
              {matchCount === 1 ? "event matches" : "events match"} ·{" "}
              <span className="font-semibold text-slate-800 tabular-nums">{onMapCount}</span> on the map
            </p>
            {activeCount > 0 && (
              <button
                type="button"
                onClick={onClearAll}
                className="shrink-0 cursor-pointer text-[11px] font-semibold text-brand-700 hover:underline"
              >
                Clear all
              </button>
            )}
          </div>
          <p className="mt-3 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Category</p>
          {shownTypes.length > 0 ? (
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {shownTypes.map((option) => (
                <Chip
                  key={option.value}
                  option={option}
                  selected={selectedTypes.includes(option.value)}
                  onToggle={() => onTypesChange(toggle(selectedTypes, option.value))}
                />
              ))}
            </div>
          ) : (
            <p className="mt-1 text-[11px] text-slate-400">No events loaded here.</p>
          )}
          <p className="mt-3 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Location and GIS</p>
          {shownLocations.length > 0 ? (
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {shownLocations.map((option) => (
                <Chip
                  key={option.value}
                  option={option}
                  selected={selectedLocations.includes(option.value)}
                  onToggle={() => onLocationsChange(toggle(selectedLocations, option.value))}
                />
              ))}
            </div>
          ) : (
            <p className="mt-1 text-[11px] text-slate-400">No events loaded here.</p>
          )}
          <p className="mt-3 border-t border-slate-100 pt-2 text-[11px] leading-snug text-slate-400">
            The same filters as the sidebar&rsquo;s: the list and its counts follow.
            {otherFilterCount > 0 &&
              ` ${otherFilterCount} more filter${otherFilterCount === 1 ? " is" : "s are"} set in the sidebar.`}{" "}
            Counts are of loaded events; the map draws those with a location and a start.
          </p>
        </div>
      )}

      {open === "layers" && (
        <div className={PANEL_CLASS} role="dialog" aria-label="Map layers">
          <Switch
            label="Event markers"
            hint="Markers, lines and areas of the events."
            checked={layers.markers}
            onChange={(markers) => onLayersChange({ ...layers, markers })}
          />
          <Switch
            label="Clusters"
            hint="Group nearby markers into numbered circles while zoomed out. Never changes the events or counts."
            checked={layers.clusters}
            disabled={!layers.markers}
            onChange={(clusters) => onLayersChange({ ...layers, clusters })}
          />
          <Switch
            label="Heatmap"
            hint="Where events are dense, under the markers. Markers stay clickable."
            checked={layers.heatmap}
            onChange={(heatmap) => onLayersChange({ ...layers, heatmap })}
          />
        </div>
      )}
    </div>
  );
}
