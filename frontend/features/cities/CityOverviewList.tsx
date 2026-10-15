import type { EventListView } from "@/features/events/filters";
import type { CityCountsState } from "./overview";

interface CityOverviewListProps {
  state: CityCountsState;
  view: EventListView;
  onSelect: (cityId: string) => void;
  onRetry: () => void;
}

/**
 * All cities at a glance: each with how many events its view lists. Choosing
 * one opens it, with its own events on the map.
 */
export default function CityOverviewList({ state, view, onSelect, onRetry }: CityOverviewListProps) {
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
  const counts = [...state.counts].sort(
    (a, b) => b.stats.total - a.stats.total || a.cityName.localeCompare(b.cityName),
  );
  return (
    <div>
      <p className="mb-2 text-xs text-brand-100">
        Choose a country or city to see its events on the map.
      </p>
      <ul className="space-y-2">
        {counts.map(({ cityId, cityName, stats }) => (
          <li key={cityId}>
            <button
              type="button"
              onClick={() => onSelect(cityId)}
              className={`flex w-full cursor-pointer items-center justify-between gap-3 rounded-xl bg-white px-4 py-3 text-left shadow-sm outline-none transition hover:shadow-md focus-visible:ring-2 focus-visible:ring-white ${
                stats.total === 0 ? "opacity-70" : ""
              }`}
            >
              <span className="text-sm font-semibold text-slate-900">{cityName}</span>
              <span className="text-right">
                <span className="block text-base font-semibold tabular-nums leading-5 text-brand-700">
                  {stats.total.toLocaleString("en-GB")}
                </span>
                <span className="block text-[11px] text-slate-500">{unit}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
