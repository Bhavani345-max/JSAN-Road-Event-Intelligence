import { useEffect, useRef, useState } from "react";
import { placeNote, searchPlaces, type FoundPlace } from "../placeSearch";

// Suggestions from REI's own place lists come this long after the last key press.
const TYPING_DEBOUNCE_MS = 250;

interface PlaceSearchPanelProps {
  /** The chosen city or country (its id), or null for all countries. */
  cityId: string | null;
  /** Its name, for "Search in Hyderabad". */
  scopeLabel: string | null;
  onChoose: (place: FoundPlace) => void;
  className: string;
}

/**
 * Type a place or a postcode (a PIN code such as 500032) in the chosen country
 * or city, press Enter, choose a result: the map moves there.
 */
export default function PlaceSearchPanel({ cityId, scopeLabel, onChoose, className }: PlaceSearchPanelProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<FoundPlace[]>([]);
  const [scope, setScope] = useState<string | null>(scopeLabel);
  const [state, setState] = useState<"idle" | "typing" | "searching" | "searched" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  // The suggestions while typing and the search on Enter are separate: a
  // suggestion never replaces or cancels what Enter asked for.
  const typingRef = useRef<{ timer?: ReturnType<typeof setTimeout>; controller?: AbortController }>({});
  const searchRef = useRef<AbortController | null>(null);
  // The text Enter last searched for: no suggestions for it afterwards.
  const searchedRef = useRef<string | null>(null);

  useEffect(() => {
    inputRef.current?.focus();
    const typing = typingRef.current;
    return () => {
      clearTimeout(typing.timer);
      typing.controller?.abort();
      searchRef.current?.abort();
    };
  }, []);

  const stopTyping = () => {
    clearTimeout(typingRef.current.timer);
    typingRef.current.controller?.abort();
  };

  // While typing: REI's own place list of the city, if it has one (no outside request).
  useEffect(() => {
    const text = query.trim();
    if (text.length < 2 || !cityId || text === searchedRef.current) return;
    const typing = typingRef.current;
    clearTimeout(typing.timer);
    typing.timer = setTimeout(() => {
      typing.controller?.abort();
      const controller = new AbortController();
      typing.controller = controller;
      searchPlaces(text, cityId, { localOnly: true, signal: controller.signal })
        .then((answer) => {
          if (controller.signal.aborted) return;
          setResults(answer.results);
          setScope(answer.scope);
          setState("typing");
        })
        .catch(() => undefined);
    }, TYPING_DEBOUNCE_MS);
    return () => clearTimeout(typing.timer);
  }, [query, cityId]);

  const search = () => {
    const text = query.trim();
    if (text.length < 2) return;
    stopTyping();
    searchedRef.current = text;
    searchRef.current?.abort();
    const controller = new AbortController();
    searchRef.current = controller;
    setState("searching");
    setError(null);
    searchPlaces(text, cityId, { signal: controller.signal })
      .then((answer) => {
        if (controller.signal.aborted) return;
        setResults(answer.results);
        setScope(answer.scope);
        setState("searched");
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return;
        setError(reason instanceof Error ? reason.message : "The search failed.");
        setState("error");
      });
  };

  return (
    <div className={className} role="dialog" aria-label="Find a place">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          search();
        }}
        className="flex items-center gap-1.5"
      >
        <input
          ref={inputRef}
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Place, street or PIN code"
          aria-label="Place, street or PIN code"
          maxLength={100}
          className="min-w-0 flex-1 rounded-lg bg-white px-2.5 py-1.5 text-xs text-slate-900 ring-1 ring-slate-200 outline-none placeholder:text-slate-400 focus:ring-2 focus:ring-brand-400"
        />
        <button
          type="submit"
          disabled={query.trim().length < 2 || state === "searching"}
          className="shrink-0 cursor-pointer rounded-lg bg-brand-600 px-2.5 py-1.5 text-xs font-semibold text-white outline-none transition hover:bg-brand-700 focus-visible:ring-2 focus-visible:ring-brand-400 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {state === "searching" ? "Searching…" : "Search"}
        </button>
      </form>
      <p className="mt-1.5 text-[11px] text-slate-500">
        {scope ? `In ${scope}` : "In all countries"} · press Enter to search
        {cityId ? "" : ". Choose a country first to search only there"}.
      </p>

      {state === "error" && error && <p className="mt-2 text-[11px] text-rose-700">{error}</p>}
      {state === "searched" && results.length === 0 && (
        <p className="mt-2 text-[11px] text-slate-500">Nothing found. Try another spelling, a nearby landmark or the PIN code.</p>
      )}
      {results.length > 0 && state !== "error" && (
        <ul className="mt-2 divide-y divide-slate-100">
          {results.map((place, index) => {
            const note = placeNote(place, scope);
            return (
              <li key={`${index}:${place.source}:${place.latitude},${place.longitude}`}>
                <button
                  type="button"
                  onClick={() => onChoose(place)}
                  className="block w-full cursor-pointer rounded-md px-1.5 py-1.5 text-left outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-brand-400"
                >
                  <span className="block truncate font-semibold text-slate-800">{place.name}</span>
                  <span className="block truncate text-[11px] text-slate-500">
                    {[place.detail || place.kind, note].filter(Boolean).join(" · ")}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {state === "typing" && results.length > 0 && (
        <p className="mt-1.5 text-[11px] text-slate-400">From REI&rsquo;s place list. Press Enter for streets and PIN codes.</p>
      )}
      <p className="mt-2 border-t border-slate-100 pt-2 text-[10px] text-slate-400">
        Search © OpenStreetMap contributors
      </p>
    </div>
  );
}
