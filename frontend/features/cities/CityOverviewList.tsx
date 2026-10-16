import type { EventListView } from "@/features/events/filters";
import type { City } from "./cities";
import { groupCityCounts, type CityCount, type CityCountsState } from "./overview";

interface CityOverviewListProps {
  state: CityCountsState;
  /** The configured countries and cities, for grouping cities under their country. */
  cities: City[];
  view: EventListView;
  onSelect: (cityId: string) => void;
  onRetry: () => void;
}

function CountButton({
  count,
  unit,
  label,
  nested = false,
  onSelect,
}: {
  count: CityCount;
  unit: string;
  label: string;
  nested?: boolean;
  onSelect: (cityId: string) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(count.cityId)}
      className={`flex w-full cursor-pointer items-center justify-between gap-3 rounded-xl bg-white text-left shadow-sm outline-none transition hover:shadow-md focus-visible:ring-2 focus-visible:ring-white ${
        nested ? "px-3 py-2" : "px-4 py-3"
      } ${count.stats.total === 0 ? "opacity-70" : ""}`}
    >
      <span className={`font-semibold text-slate-900 ${nested ? "text-xs" : "text-sm"}`}>{label}</span>
      <span className="text-right">
        <span
          className={`block font-semibold tabular-nums text-brand-700 ${nested ? "text-sm leading-4" : "text-base leading-5"}`}
        >
          {count.stats.total.toLocaleString("en-GB")}
        </span>
        <span className="block text-[11px] text-slate-500">{unit}</span>
      </span>
    </button>
  );
}

/**
 * All countries and cities at a glance, each city under its country
 * (decision 0035): a country's entry (Canada) counts what choosing it lists,
 * its own events and its cities' (Toronto); each city counts its own.
 * Choosing one opens it, with its events on the map.
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
        Choose a country or city to see its events on the map.
      </p>
      <ul className="space-y-2" aria-label="Countries and cities">
        {groups.map((group) => (
          <li key={group.country}>
            {group.entry ? (
              <CountButton count={group.entry} unit={unit} label={group.entry.cityName} onSelect={onSelect} />
            ) : (
              // A country with no entry of its own (India): a heading over its cities.
              <p className="flex items-baseline justify-between px-1 text-xs font-semibold text-white">
                <span>{group.name}</span>
                <span className="text-[11px] font-normal tabular-nums text-brand-100">
                  {group.stats.total.toLocaleString("en-GB")} {unit}
                </span>
              </p>
            )}
            {group.cities.length > 0 && (
              <ul
                className={`mt-1.5 space-y-1.5 ${group.entry ? "ml-4 border-l border-white/20 pl-2.5" : ""}`}
                aria-label={`Cities in ${group.name}`}
              >
                {group.cities.map((count) => (
                  <li key={count.cityId}>
                    <CountButton count={count} unit={unit} label={count.cityName} nested onSelect={onSelect} />
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
