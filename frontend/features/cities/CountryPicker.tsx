"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import { ALL_CITIES, countryChoices, searchCountries, type City, type CountryMatch } from "./cities";
import CountryFlag from "./CountryFlag";

interface CountryPickerProps {
  /** The configured countries and cities (not "All countries"). */
  cities: City[];
  /** The country chosen; null for all countries. */
  country: City | null;
  onChange: (id: string) => void;
}

const PANEL_WIDTH = 288;

/** Where the list opens: below the button, kept on screen on a phone, its list fitting the screen's height. */
function panelPlace(button: HTMLElement) {
  const rect = button.getBoundingClientRect();
  const width = Math.min(PANEL_WIDTH, window.innerWidth - 16);
  const left = Math.min(Math.max(8, rect.left), window.innerWidth - width - 8);
  const top = rect.bottom + 6;
  return { left, top, width, listHeight: Math.max(120, Math.min(288, window.innerHeight - top - 72)) };
}

function GlobeIcon({ className }: { className: string }) {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" className={className} aria-hidden="true">
      <circle cx="8" cy="8" r="6.25" />
      <path d="M1.75 8h12.5M8 1.75c1.7 1.8 2.5 3.9 2.5 6.25S9.7 12.45 8 14.25C6.3 12.45 5.5 10.35 5.5 8S6.3 3.55 8 1.75Z" strokeLinejoin="round" />
    </svg>
  );
}

/**
 * The country choice in the header: the chosen country's flag and name; opened,
 * a search box over the list of countries (decision 0043). Typing filters by
 * name, code, other name (UK, USA) or a city of the country; arrow keys move,
 * Enter chooses, Escape closes.
 */
export default function CountryPicker({ cities, country, onChange }: CountryPickerProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const [place, setPlace] = useState({ left: 8, top: 56, width: PANEL_WIDTH, listHeight: 288 });
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listId = useId();
  const optionId = (index: number) => `${listId}-option-${index}`;

  const choices = useMemo(() => countryChoices(cities), [cities]);
  const results: CountryMatch[] = useMemo(
    () => [...(query.trim() === "" ? [{ choice: ALL_CITIES }] : []), ...searchCountries(choices, cities, query)],
    [choices, cities, query],
  );
  const chosenId = country?.id ?? ALL_CITIES.id;

  function openPanel() {
    if (buttonRef.current) setPlace(panelPlace(buttonRef.current));
    setQuery("");
    // The list starts with All countries, then the countries: highlight the chosen one.
    setActive(Math.max(0, choices.findIndex((choice) => choice.id === chosenId) + 1));
    setOpen(true);
  }

  function close(focusButton: boolean) {
    setOpen(false);
    if (focusButton) buttonRef.current?.focus();
  }

  function choose(match: CountryMatch | undefined) {
    if (!match) return;
    close(true);
    if (match.choice.id !== chosenId) onChange(match.choice.id);
  }

  useEffect(() => {
    if (!open) return;
    inputRef.current?.focus();
    // A click anywhere else closes the list.
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (!panelRef.current?.contains(target) && !buttonRef.current?.contains(target)) setOpen(false);
    };
    const onResize = () => {
      if (buttonRef.current) setPlace(panelPlace(buttonRef.current));
    };
    document.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("resize", onResize);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("resize", onResize);
    };
  }, [open]);

  // Keep the highlighted country in view while moving with the arrow keys.
  const activeId = optionId(active);
  useEffect(() => {
    if (open) document.getElementById(activeId)?.scrollIntoView({ block: "nearest" });
  }, [open, activeId]);

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const step = event.key === "ArrowDown" ? 1 : -1;
      setActive((index) => Math.min(Math.max(index + step, 0), results.length - 1));
    } else if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      setActive(event.key === "Home" ? 0 : results.length - 1);
    } else if (event.key === "Enter") {
      event.preventDefault();
      choose(results[active]);
    } else if (event.key === "Escape") {
      event.preventDefault();
      close(true);
    } else if (event.key === "Tab") {
      setOpen(false);
    }
  }

  const label = country?.name ?? ALL_CITIES.name;
  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`Country: ${label}. Change country`}
        title="Choose or search a country"
        onClick={() => (open ? close(false) : openPanel())}
        onKeyDown={(event) => {
          if (!open && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
            event.preventDefault();
            openPanel();
          }
        }}
        className="flex h-7 max-w-48 cursor-pointer items-center gap-1.5 rounded-full bg-brand-50 pl-2 pr-2 text-[11px] font-semibold text-brand-700 ring-1 ring-inset ring-brand-100 transition outline-none hover:bg-brand-100 focus-visible:ring-2 focus-visible:ring-brand-400"
      >
        {country ? <CountryFlag code={country.country} size={13} /> : <GlobeIcon className="h-3.5 w-3.5 shrink-0" />}
        <span className="truncate">{label}</span>
        <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.6" className={`h-3 w-3 shrink-0 transition ${open ? "rotate-180" : ""}`} aria-hidden="true">
          <path d="m3 4.5 3 3 3-3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && (
        <div
          ref={panelRef}
          style={{ left: place.left, top: place.top, width: place.width }}
          className="fixed z-50 overflow-hidden rounded-xl bg-white text-slate-900 shadow-xl ring-1 ring-slate-900/10"
        >
          <div className="border-b border-slate-100 p-2">
            <label className="relative block">
              <span className="sr-only">Search countries</span>
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" aria-hidden="true">
                <circle cx="7" cy="7" r="4.5" />
                <path d="m10.5 10.5 3 3" strokeLinecap="round" />
              </svg>
              <input
                ref={inputRef}
                type="text"
                role="combobox"
                aria-expanded="true"
                aria-controls={listId}
                aria-autocomplete="list"
                aria-activedescendant={results.length > 0 ? activeId : undefined}
                autoComplete="off"
                spellCheck={false}
                placeholder="Search a country or city"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setActive(0);
                }}
                onKeyDown={onKeyDown}
                className="h-8 w-full rounded-lg bg-slate-50 pl-8 pr-2 text-xs text-slate-900 ring-1 ring-inset ring-slate-200 outline-none placeholder:text-slate-400 focus:bg-white focus:ring-2 focus:ring-brand-400"
              />
            </label>
          </div>
          <ul id={listId} role="listbox" aria-label="Countries" style={{ maxHeight: place.listHeight }} className="overflow-y-auto p-1">
            {results.map((match, index) => {
              const selected = match.choice.id === chosenId;
              return (
                <li
                  key={match.choice.id}
                  id={optionId(index)}
                  role="option"
                  aria-selected={selected}
                  // Keep the focus in the search box.
                  onMouseDown={(event) => event.preventDefault()}
                  onMouseMove={() => setActive(index)}
                  onClick={() => choose(match)}
                  className={`flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-xs ${
                    index === active ? "bg-brand-50 text-brand-800" : "text-slate-700"
                  } ${selected ? "font-semibold" : ""}`}
                >
                  {match.choice.id === ALL_CITIES.id ? (
                    <GlobeIcon className="h-4 w-4 shrink-0 text-slate-500" />
                  ) : (
                    <CountryFlag code={match.choice.country} size={13} />
                  )}
                  <span className="min-w-0 flex-1 truncate">
                    {match.choice.name}
                    {match.city && <span className="font-normal text-slate-500"> · {match.city}</span>}
                  </span>
                  {selected && (
                    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" className="h-3.5 w-3.5 shrink-0 text-brand-600" aria-hidden="true">
                      <path d="m3.5 8.5 3 3 6-7" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </li>
              );
            })}
            {results.length === 0 && (
              <li role="presentation" className="px-2.5 py-3 text-center text-xs text-slate-500">
                No country matches &ldquo;{query.trim()}&rdquo;
              </li>
            )}
          </ul>
        </div>
      )}
    </>
  );
}
