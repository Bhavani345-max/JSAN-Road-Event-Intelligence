import type { EventListView } from "@/features/events/filters";
import type { City } from "./cities";
import { groupCityCounts, type CityCount, type CityCountsState } from "./overview";

interface CityOverviewListProps {
  state: CityCountsState;
  /** The configured countries and cities, for counting each country with its cities. */
  cities: City[];
  view: EventListView;
  onSelect: (cityId: string) => void;
  onRetry: () => void;
}

function citiesLabel(count: number): string | undefined {
  if (count === 0) return undefined;
  return count === 1 ? "1 city" : `${count} cities`;
}

function CountButton({
  count,
  unit,
  label,
  detail,
  onSelect,
}: {
  count: CityCount;
  unit: string;
  label: string;
  /** A second line under the label ("8 cities"). */
  detail?: string;
  onSelect: (cityId: string) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(count.cityId)}
      className={`flex w-full cursor-pointer items-center justify-between gap-3 rounded-xl bg-white px-4 py-3 text-left shadow-sm outline-none transition hover:shadow-md focus-visible:ring-2 focus-visible:ring-white ${
        count.stats.total === 0 ? "opacity-70" : ""
      }`}
    >
      <span>
        <span className="block text-sm font-semibold text-slate-900">{label}</span>
        {detail && <span className="block text-[11px] text-slate-500">{detail}</span>}
      </span>
      <span className="text-right">
        <span className="block text-base font-semibold leading-5 tabular-nums text-brand-700">
          {count.stats.total.toLocaleString("en-GB")}
        </span>
        <span className="block text-[11px] text-slate-500">{unit}</span>
      </span>
    </button>
  );
}

/**
 * All countries at a glance (decision 0036): each counts what choosing it
 * lists, its own events and its cities' (India: Hyderabad, Delhi, ...).
 * Choosing one opens it, with its events on the map and its cities to choose
 * from. A city is listed here only if its country has no entry.
 */
export default function CityOverviewList({ state, cities, view, onSelect, onRetry }: CityOverviewListProps) {
  if (state.status === "loading") {
    return (
      <ul className="space-y-2" aria-busy="true" aria-label="Loading cities">
        {[0, 1, 2, 3].map((i) => (
          <li key={i} className="h-14 animate-pulse rounded-xl bg-white/10" />
        ))}
      </ul>
    );
  }
  if (state.status === "error") {
    return (
      <div className="rounded-xl bg-white/10 p-4 text-sm text-white ring-1 ring-inset ring-white/15">
        <p className="font-semibold">The overview could not be loaded</p>
        <p className="mt-1 text-xs text-brand-100">{state.message}</p>
        <button type="button" onClick={onRetry} className="mt-2 text-xs font-semibold underline">
          Try again
        </button>
      </div>
    );
  }
  const unit = view === "validation" ? "to review" : "in effect or upcoming";
  const groups = groupCityCounts(cities, state.counts);
  return (
    <div>
      <p className="mb-2 text-xs text-brand-100">
        Choose a country to see its events on the map and its cities.
      </p>
      <ul className="space-y-2" aria-label="Countries">
        {groups.flatMap((group) =>
          group.entry
            ? [
                <li key={group.country}>
                  <CountButton
                    count={group.entry}
                    unit={unit}
                    label={group.entry.cityName}
                    detail={citiesLabel(group.cities.length)}
                    onSelect={onSelect}
                  />
                </li>,
              ]
            : // Cities of a country with no entry (none is configured so) stay reachable.
              group.cities.map((count) => (
                <li key={count.cityId}>
                  <CountButton count={count} unit={unit} label={count.cityName} onSelect={onSelect} />
                </li>
              )),
        )}
      </ul>
    </div>
  );
}
