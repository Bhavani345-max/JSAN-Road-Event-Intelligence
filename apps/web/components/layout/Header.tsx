import Image from "next/image";
import type { City } from "@/features/cities/cities";

interface HeaderProps {
  cities: City[];
  city: City;
  onCityChange: (cityId: string) => void;
}

export default function Header({ cities, city, onCityChange }: HeaderProps) {
  return (
    <header className="z-10 flex h-14 shrink-0 items-center justify-between gap-3 border-b border-slate-200 bg-white px-4">
      <div className="flex min-w-0 items-center gap-3">
        <Image
          src="/jsan-mark.png"
          alt="JSAN"
          width={36}
          height={36}
          priority
          className="h-9 w-9 shrink-0"
        />
        <div className="flex min-w-0 items-center gap-2.5">
          <h1 className="truncate text-[15px] font-semibold tracking-tight text-brand-800">
            JSAN Road Event Intelligence
          </h1>
          {cities.length > 1 ? (
            <label className="flex shrink-0 items-center gap-1.5">
              <span className="sr-only">City</span>
              <select
                value={city.id}
                onChange={(event) => onCityChange(event.target.value)}
                className="h-7 cursor-pointer rounded-full bg-brand-50 pl-2.5 pr-7 text-[11px] font-semibold text-brand-700 ring-1 ring-inset ring-brand-100 outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
              >
                {cities.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.id === "all" ? "All cities" : `${option.name} PoC`}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <span className="hidden shrink-0 rounded-full bg-brand-50 px-2 py-0.5 text-[11px] font-medium text-brand-700 ring-1 ring-inset ring-brand-100 sm:inline">
              {city.id === "all" ? "All cities" : `${city.name} PoC`}
            </span>
          )}
        </div>
      </div>
      <span
        className="flex shrink-0 items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-[11px] font-semibold tracking-wide text-amber-700 ring-1 ring-inset ring-amber-300"
        title="Events come from real sources and await human validation. None is a confirmed road event until a reviewer validates it, even when the source is official."
      >
        <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
        PoC
        <span className="hidden font-normal tracking-normal text-amber-700/80 md:inline">
          · real source events, pending validation
        </span>
      </span>
    </header>
  );
}
