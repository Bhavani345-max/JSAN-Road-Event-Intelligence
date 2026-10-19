import type { City } from "./cities";
import { cityChoiceCounts, type CityCountsState } from "./overview";

interface CountryCitiesProps {
  /** The chosen country (India). */
  country: City;
  /** The cities within it, in the configured order. */
  cities: City[];
  /** The entry on screen: the country itself or one of its cities. */
  selectedId: string;
  /** The view's counts per entry (GET /api/events/summary); numbers are left out until they load. */
  counts: CityCountsState;
  onSelect: (cityId: string) => void;
}

/**
 * The cities of the chosen country (decision 0036): the whole country first,
 * then each city, with what choosing it lists in the view on screen.
 */
export default function CountryCities({ country, cities, selectedId, counts, onSelect }: CountryCitiesProps) {
  const numbers = counts.status === "ready" ? cityChoiceCounts(country, cities, counts.counts) : null;
  const choices = [
    { id: country.id, label: `All of ${country.name}` },
    ...cities.map((city) => ({ id: city.id, label: city.name })),
  ];
  return (
    <nav aria-label={`Cities in ${country.name}`}>
      <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-brand-100">
        Cities in {country.name}
      </p>
      <ul className="flex flex-wrap gap-1.5">
        {choices.map((choice) => {
          const selected = choice.id === selectedId;
          const count = numbers?.[choice.id];
          return (
            <li key={choice.id}>
              <button
                type="button"
                aria-pressed={selected}
                onClick={() => onSelect(choice.id)}
                className={`flex h-7 cursor-pointer items-center gap-1.5 rounded-full px-2.5 text-[11px] font-semibold ring-1 ring-inset transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70 ${
                  selected
                    ? "bg-white text-brand-700 ring-white"
                    : "bg-white/10 text-white ring-white/20 hover:bg-white/20"
                }`}
              >
                {choice.label}
                {count !== undefined && (
                  <span className={`tabular-nums ${selected ? "text-brand-500" : "text-brand-100"}`}>
                    {count.toLocaleString("en-GB")}
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
