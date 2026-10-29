"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { ALL_CITIES, citiesIn, countryOf, type City } from "@/features/cities/cities";
import CountryPicker from "@/features/cities/CountryPicker";
import { canManageAccounts } from "@/features/auth/permissions";
import type { AuthUser } from "@/features/auth/types";
import { initials } from "@/features/profile/profile";
import ProfileDialog from "@/features/profile/ProfileDialog";
import { useWaitingRegistrations } from "@/features/users/useWaitingRegistrations";

interface HeaderProps {
  /** The configured countries and cities (not "All countries"). */
  cities: City[];
  /** The one chosen, or All countries. */
  city: City;
  onCityChange: (cityId: string) => void;
  user: AuthUser;
  onSignOut: () => Promise<void>;
  /** The account after it changed its own name or email. */
  onUserChange: (user: AuthUser) => void;
}

const SELECT_CLASS =
  "h-7 max-w-44 cursor-pointer rounded-full bg-brand-50 pl-2.5 pr-7 text-[11px] font-semibold text-brand-700 ring-1 ring-inset ring-brand-100 outline-none focus-visible:ring-2 focus-visible:ring-brand-400";

export default function Header({ cities, city, onCityChange, user, onSignOut, onUserChange }: HeaderProps) {
  // Countries first (decision 0036); a chosen country's cities in a second list.
  const country = countryOf(city, cities);
  const within = citiesIn(country, cities);
  const [profileOpen, setProfileOpen] = useState(false);
  // Administrators: User management, with the confirmed registrations waiting (decision 0045).
  const isAdmin = canManageAccounts(user);
  const waiting = useWaitingRegistrations(isAdmin);
  return (
    // Above the map's panels, so the country list opens over them.
    <header className="z-30 flex h-14 shrink-0 items-center justify-between gap-3 border-b border-slate-200 bg-white px-4">
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
          {/* On a phone held upright only the JSAN mark shows: the country and
              account buttons leave the name no more than a few letters. */}
          <h1 className="truncate text-[15px] font-semibold tracking-tight text-brand-800 max-sm:sr-only">
            JSAN Road Event Intelligence
          </h1>
          {cities.length > 0 ? (
            <div className="flex shrink-0 items-center gap-1.5">
              {/* The chosen country's flag and name; opened, a search over the countries (decision 0043). */}
              <CountryPicker cities={cities} country={country} onChange={onCityChange} />
              {/* Phones choose the city in the sidebar (its city buttons): no room here. */}
              {country && within.length > 0 && (
                <label className="hidden items-center sm:flex">
                  <span className="sr-only">City in {country.name}</span>
                  <select
                    value={city.id}
                    onChange={(event) => onCityChange(event.target.value)}
                    className={SELECT_CLASS}
                  >
                    <option value={country.id}>{`All of ${country.name}`}</option>
                    {within.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.name}
                      </option>
                    ))}
                  </select>
                </label>
              )}
            </div>
          ) : (
            <span className="hidden shrink-0 rounded-full bg-brand-50 px-2 py-0.5 text-[11px] font-medium text-brand-700 ring-1 ring-inset ring-brand-100 sm:inline">
              {city.id === ALL_CITIES.id ? ALL_CITIES.name : `${city.name} PoC`}
            </span>
          )}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2 sm:gap-2.5">
        <span
          className="hidden items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-[11px] font-semibold tracking-wide text-amber-700 ring-1 ring-inset ring-amber-300 sm:flex"
          title="Events come from real sources and await human validation. None is a confirmed road event until a reviewer validates it, even when the source is official."
        >
          <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
          PoC
          <span className="hidden font-normal tracking-normal text-amber-700/80 md:inline sideways:hidden">
            · real source events, pending validation
          </span>
        </span>
        {isAdmin && (
          <Link
            href="/users"
            aria-label={waiting > 0 ? `User management: ${waiting} registration${waiting === 1 ? "" : "s"} waiting` : "User management"}
            title="User management: registrations, accounts, password resets"
            className="relative flex h-8 items-center gap-1.5 rounded-lg px-2 text-[11px] font-semibold text-slate-600 ring-1 ring-inset ring-slate-200 transition hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          >
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-3.5 w-3.5" aria-hidden="true"><circle cx="7.5" cy="7" r="2.75" /><path d="M2.5 16c.6-2.6 2.6-4 5-4s4.4 1.4 5 4M13 4.6a2.75 2.75 0 0 1 0 4.9M14.5 12.3c1.6.5 2.7 1.8 3 3.7" strokeLinecap="round" /></svg>
            <span className="hidden lg:inline">Users</span>
            {waiting > 0 && (
              <span className="absolute -right-1.5 -top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-amber-500 px-1 text-[10px] font-bold text-white">
                {waiting}
              </span>
            )}
          </Link>
        )}
        <button
          type="button"
          onClick={() => setProfileOpen(true)}
          aria-haspopup="dialog"
          aria-label={`Profile and settings for ${user.display_name}`}
          title={`${user.display_name} (${user.email}): profile, password and theme colour`}
          className="flex h-8 max-w-44 items-center gap-2 rounded-full py-1 pl-1 pr-1 text-[11px] font-semibold text-slate-700 ring-1 ring-inset ring-slate-200 transition hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 xl:pr-3"
        >
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-600 text-[10px] font-semibold text-white">
            {initials(user)}
          </span>
          <span className="hidden truncate xl:block">{user.display_name}</span>
        </button>
        <button
          type="button"
          onClick={() => void onSignOut()}
          aria-label={`Sign out ${user.email}`}
          title={`Signed in as ${user.email}. Sign out.`}
          className="flex h-8 items-center gap-1.5 rounded-lg bg-brand-600 px-2.5 text-[11px] font-semibold text-white shadow-sm transition hover:bg-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
        >
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-3.5 w-3.5" aria-hidden="true"><path d="M8 4H5.5A1.5 1.5 0 0 0 4 5.5v9A1.5 1.5 0 0 0 5.5 16H8m3-3 3-3-3-3m3 3H8" strokeLinecap="round" strokeLinejoin="round" /></svg>
          <span className="hidden sm:inline">Sign out</span>
        </button>
      </div>
      <ProfileDialog
        open={profileOpen}
        onClose={() => setProfileOpen(false)}
        user={user}
        onUserChange={onUserChange}
      />
    </header>
  );
}
