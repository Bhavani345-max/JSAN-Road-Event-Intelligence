import Image from "next/image";
import { ALL_CITIES, choiceLabel, groupByCountry, type City } from "@/features/cities/cities";
import type { AuthUser } from "@/features/auth/types";

interface HeaderProps {
  /** The configured countries and cities (not "All cities"). */
  cities: City[];
  /** The one chosen, or All cities. */
  city: City;
  onCityChange: (cityId: string) => void;
  user: AuthUser;
  onSignOut: () => Promise<void>;
}

export default function Header({ cities, city, onCityChange, user, onSignOut }: HeaderProps) {
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
          {cities.length > 0 ? (
            <label className="flex shrink-0 items-center gap-1.5">
              <span className="sr-only">Country or city</span>
              <select
                value={city.id}
                onChange={(event) => onCityChange(event.target.value)}
                className="h-7 cursor-pointer rounded-full bg-brand-50 pl-2.5 pr-7 text-[11px] font-semibold text-brand-700 ring-1 ring-inset ring-brand-100 outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
              >
                <option value={ALL_CITIES.id}>{ALL_CITIES.name}</option>
                {/* Each country, its own entry first (Canada, which covers its
                    cities), then its cities (Toronto). */}
                {groupByCountry(cities).map((group) => (
                  <optgroup key={group.country} label={group.name}>
                    {[...(group.entry ? [group.entry] : []), ...group.cities].map((option) => (
                      <option key={option.id} value={option.id}>
                        {`${choiceLabel(option, cities)} PoC`}
                      </option>
                    ))}
                  </optgroup>
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
      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        <span
          className="hidden items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-[11px] font-semibold tracking-wide text-amber-700 ring-1 ring-inset ring-amber-300 sm:flex"
          title="Events come from real sources and await human validation. None is a confirmed road event until a reviewer validates it, even when the source is official."
        >
          <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
          PoC
          <span className="hidden font-normal tracking-normal text-amber-700/80 md:inline">
            · real source events, pending validation
          </span>
        </span>
        <span className="hidden max-w-32 truncate text-[11px] font-medium text-slate-500 xl:block" title={user.email}>
          {user.display_name}
        </span>
        <button
          type="button"
          onClick={() => void onSignOut()}
          aria-label={`Sign out ${user.email}`}
          title={`Signed in as ${user.email}. Sign out.`}
          className="flex h-8 items-center gap-1.5 rounded-lg px-2 text-[11px] font-semibold text-slate-600 ring-1 ring-inset ring-slate-200 transition hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
        >
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-3.5 w-3.5" aria-hidden="true"><path d="M8 4H5.5A1.5 1.5 0 0 0 4 5.5v9A1.5 1.5 0 0 0 5.5 16H8m3-3 3-3-3-3m3 3H8" strokeLinecap="round" strokeLinejoin="round" /></svg>
          <span className="hidden sm:inline">Sign out</span>
        </button>
      </div>
    </header>
  );
}
