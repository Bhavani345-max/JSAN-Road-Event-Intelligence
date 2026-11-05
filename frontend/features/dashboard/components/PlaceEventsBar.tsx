import { describeCount, formatDistance, PLACE_RADII, type PlaceRange } from "@/features/map/placeArea";
import { count as number } from "../sources";

interface PlaceEventsBarProps {
  /** The place found with "Find place". */
  name: string;
  range: PlaceRange;
  onRangeChange: (range: PlaceRange) => void;
  /** OpenStreetMap gives the place an area of its own: "Its area" can be chosen. */
  hasArea: boolean;
  /** Located events of the list in the place. */
  count: number;
  /** Of those, how many the map does not draw (ended, no stated start …). */
  offMap: number;
  listOnly: boolean;
  onListOnlyChange: (listOnly: boolean) => void;
  /** The list holds only the newest events: how many were checked. Null when it is whole. */
  checkedOfLoaded: number | null;
  /** All countries together: no events are loaded until a country is opened. */
  overview: boolean;
  /** The events are not loaded yet: nothing can be counted. */
  loading: boolean;
  onClear: () => void;
}

const PIN_ICON = (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-3.5 w-3.5 shrink-0" aria-hidden="true">
    <path d="M8 14.5s4.5-4.2 4.5-8a4.5 4.5 0 0 0-9 0c0 3.8 4.5 8 4.5 8Z" strokeLinejoin="round" />
    <circle cx="8" cy="6.5" r="1.6" />
  </svg>
);

const chipClass = (active: boolean) =>
  `h-7 cursor-pointer rounded-full px-2.5 text-[11px] font-semibold outline-none transition focus-visible:ring-2 focus-visible:ring-white/70 ${
    active ? "bg-white text-brand-700 shadow-sm" : "bg-white/10 text-white ring-1 ring-inset ring-white/25 hover:bg-white/20"
  }`;

/**
 * The events in a place found with "Find place" (decision 0056): how many,
 * what "in" covers (its own area, or a distance from its point), and whether
 * the list shows only them. The map rings them and draws the others faint.
 */
export default function PlaceEventsBar({
  name,
  range,
  onRangeChange,
  hasArea,
  count,
  offMap,
  listOnly,
  onListOnlyChange,
  checkedOfLoaded,
  overview,
  loading,
  onClear,
}: PlaceEventsBarProps) {
  const ranges: PlaceRange[] = hasArea ? ["area", ...PLACE_RADII] : [...PLACE_RADII];
  return (
    <section aria-label={`Events near ${name}`} className="mb-3 rounded-xl bg-white/10 p-3 text-white ring-1 ring-inset ring-white/20">
      <div className="flex items-center gap-2">
        {PIN_ICON}
        <h3 className="min-w-0 flex-1 truncate text-xs font-semibold" title={name}>
          Near {name}
        </h3>
        <button
          type="button"
          onClick={onClear}
          className="shrink-0 cursor-pointer rounded px-1.5 py-0.5 text-[11px] font-semibold text-white/90 underline decoration-white/50 underline-offset-2 outline-none transition hover:text-white focus-visible:ring-2 focus-visible:ring-white/70"
        >
          Clear place
        </button>
      </div>
      {overview ? (
        <p className="mt-1.5 text-[11px] leading-4 text-brand-100">
          Open a country to see its events near this place.
        </p>
      ) : (
        <>
          <p className="mt-1.5 text-[11px] leading-4 text-brand-100" role="status">
            {loading ? (
              "Loading the events…"
            ) : (
              <>
                <span className="font-semibold text-white">{describeCount(count, range)}</span>
                {offMap > 0 && ` · ${number(offMap)} of them not on the map`}
                {checkedOfLoaded !== null && ` · among the ${number(checkedOfLoaded)} events loaded`}
              </>
            )}
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5" role="group" aria-label="What counts as near">
            {ranges.map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={option === range}
                onClick={() => onRangeChange(option)}
                className={chipClass(option === range)}
                title={option === "area" ? "The area OpenStreetMap gives this place" : `Within ${formatDistance(option)} of the place`}
              >
                {option === "area" ? "Its area" : formatDistance(option)}
              </button>
            ))}
          </div>
          <button
            type="button"
            aria-pressed={listOnly && count > 0}
            disabled={loading || count === 0}
            onClick={() => onListOnlyChange(!listOnly)}
            className="mt-2 flex h-8 w-full cursor-pointer items-center justify-center rounded-lg bg-white/10 text-xs font-semibold text-white ring-1 ring-inset ring-white/20 outline-none transition hover:bg-white/20 focus-visible:ring-2 focus-visible:ring-white/70 disabled:cursor-not-allowed disabled:opacity-50 aria-pressed:bg-white aria-pressed:text-brand-700"
          >
            {listOnly && count > 0 ? "Show all events in the list" : "List only these events"}
          </button>
        </>
      )}
    </section>
  );
}
