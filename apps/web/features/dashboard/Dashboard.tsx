"use client";

import dynamic from "next/dynamic";
import { useCallback, useMemo, useState, useSyncExternalStore } from "react";
import Header from "@/components/layout/Header";
import {
  ALL_CITIES,
  ALL_CITIES_ID,
  DEFAULT_CITY_ID,
  useCities,
} from "@/features/cities/cities";
import EventDetailsPanel from "@/features/events/components/EventDetailsPanel";
import EventFilters from "@/features/events/components/EventFilters";
import EventList, { type EventListState } from "@/features/events/components/EventList";
import StatsBar from "@/features/events/components/StatsBar";
import {
  DEFAULT_FILTERS,
  filterEvents,
  hasActiveFilters,
  inCity,
  keepCurrent,
  matchesLocally,
  type EventFilters as Filters,
} from "@/features/events/filters";
import { useEventSearch } from "@/features/events/hooks/useEventSearch";
import { useEvents } from "@/features/events/hooks/useEvents";
import {
  EVENT_STATUSES,
  isLocated,
  type Position,
  type RoadEvent,
} from "@/features/events/model";
import { setCityTimeZones, setDisplayTimeZone } from "@/features/events/presentation";
import { computeEventStats } from "@/features/events/stats";
import BasemapToggle from "@/features/map/components/BasemapToggle";
import MapLegend from "@/features/map/components/MapLegend";
import AddEventPanel from "@/features/qc/components/AddEventPanel";
import ReviewActions from "@/features/qc/components/ReviewActions";
import type { Basemap } from "@/lib/config";
import SourceStatusBar from "./components/SourceStatusBar";
import { useConnectedSources } from "./sources";

// MapLibre needs the browser (WebGL, workers), so the map is client-only.
const EventMap = dynamic(() => import("@/features/map/components/EventMap"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse bg-slate-100" />,
});

const NO_EVENTS: RoadEvent[] = [];
// The address does not change while the console is open.
const subscribeToNothing = () => () => {};
const NO_IDS: ReadonlySet<string> = new Set();

export default function Dashboard() {
  const { state, reload, refresh: refreshEvents } = useEvents();
  const { sources: allSources, refresh: refreshSources } = useConnectedSources();
  const cities = useCities();
  // A link can open the console on a city (/?city=london); choosing one in
  // the header overrides it.
  const linkedCityId = useSyncExternalStore(
    subscribeToNothing,
    () => new URLSearchParams(window.location.search).get("city"),
    () => null,
  );
  const [chosenCityId, setCityId] = useState<string | null>(null);
  // All cities together unless one is chosen (or named in the link).
  const cityId = chosenCityId ?? linkedCityId ?? ALL_CITIES_ID;
  const cityOptions = useMemo(() => [ALL_CITIES, ...cities], [cities]);
  const city = cityOptions.find((candidate) => candidate.id === cityId) ?? ALL_CITIES;
  const allCities = city.id === ALL_CITIES_ID;
  const isDefaultCity = city.id === DEFAULT_CITY_ID;
  // Each event's times are shown in its own city's zone; times with no city
  // (filters) in the selected city's, or India Standard Time for all cities.
  // Set before anything below renders a time.
  setCityTimeZones(cities);
  setDisplayTimeZone(city.timeZone);
  // The city's own sources, and those about no city in particular.
  const sources = useMemo(
    () =>
      allCities
        ? allSources
        : allSources.filter((source) => source.city === null || source.city === city.id),
    [allSources, city.id, allCities],
  );
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [basemap, setBasemap] = useState<Basemap>("map");
  // Whether the form for entering an event by hand is open.
  const [isAdding, setIsAdding] = useState(false);
  // While a reviewer corrects an event's location, map clicks choose the spot.
  const [picking, setPicking] = useState(false);
  const [pickedPoint, setPickedPoint] = useState<Position | null>(null);
  const changePicking = useCallback((active: boolean) => {
    setPicking(active);
    setPickedPoint(null);
  }, []);
  // The API's search also covers the full article text behind each event.
  const serverMatches = useEventSearch(filters.search);

  const loadedEvents = state.status === "ready" ? state.events : NO_EVENTS;
  const loadedAt = state.status === "ready" ? state.loadedAt : null;
  // By default completed, rejected and old events do not reach the list, the
  // map or the counts: the console shows upcoming, ongoing and recently
  // reported events. "Show history" brings the rest back.
  const allEvents = useMemo(
    () =>
      loadedAt
        ? keepCurrent(loadedEvents, loadedAt, filters.showHistory).filter(
            (event) => allCities || inCity(event, city.name, isDefaultCity),
          )
        : NO_EVENTS,
    [loadedEvents, loadedAt, city.name, isDefaultCity, allCities, filters.showHistory],
  );
  const visibleEvents = useMemo(
    () => filterEvents(allEvents, filters, serverMatches),
    [allEvents, filters, serverMatches],
  );
  // Events found only because their article text matched the search.
  const articleMatchIds = useMemo(
    () =>
      filters.search.trim() === ""
        ? NO_IDS
        : new Set(
            visibleEvents
              .filter((event) => !matchesLocally(event, filters.search))
              .map((event) => event.id),
          ),
    [visibleEvents, filters.search],
  );
  const stats = useMemo(() => computeEventStats(visibleEvents), [visibleEvents]);
  const statusOptions = useMemo(
    () => EVENT_STATUSES.filter((status) => allEvents.some((event) => event.status === status)),
    [allEvents],
  );
  const locatedCount = useMemo(() => visibleEvents.filter(isLocated).length, [visibleEvents]);
  const visibleTypes = useMemo(
    () => visibleEvents.flatMap((event) => (event.eventType ? [event.eventType] : [])),
    [visibleEvents],
  );
  // Connected sources, plus any other source that events came from (manual entry).
  const sourceOptions = useMemo(() => {
    const options = sources.map(({ id, name }) => ({ id, name }));
    for (const { source } of allEvents) {
      if (!options.some((option) => option.id === source.id)) {
        options.push({ id: source.id, name: source.name });
      }
    }
    return options;
  }, [sources, allEvents]);

  // An event hidden by the filters is no longer selected.
  const selectedEvent = visibleEvents.find((event) => event.id === selectedEventId) ?? null;

  const listState: EventListState =
    state.status === "ready"
      ? {
          status: "ready",
          events: visibleEvents,
          now: state.loadedAt,
          isFiltered: hasActiveFilters(filters),
        }
      : state;

  // After a source check or a review decision, reload without a loading flash.
  const refreshAll = useCallback(() => {
    refreshEvents();
    refreshSources();
  }, [refreshEvents, refreshSources]);

  const selectEvent = useCallback((eventId: string | null) => {
    setSelectedEventId(eventId);
    if (eventId) setIsAdding(false);
  }, []);

  return (
    <div className="flex h-dvh flex-col bg-white text-slate-900">
      <Header
        cities={cityOptions}
        city={city}
        onCityChange={(id) => {
          setCityId(id);
          setSelectedEventId(null);
          setIsAdding(false);
          setFilters(DEFAULT_FILTERS);
        }}
      />
      <main className="flex min-h-0 flex-1 flex-col-reverse md:flex-row">
        {/* The whole sidebar scrolls when the window is too short to show it all;
            the source list and the event list keep their own scrollbars inside it. */}
        <aside className="rei-sidebar-scroll flex min-h-0 flex-1 flex-col overflow-y-auto bg-linear-to-b from-brand-600 to-brand-700 md:w-[420px] md:flex-none">
          <div className="space-y-3 border-b border-white/15 p-4 md:shrink-0">
            <StatsBar
              stats={state.status === "ready" ? stats : null}
              unfilteredTotal={allEvents.length}
            />
            <SourceStatusBar sources={sources} onChecked={refreshAll} />
            <EventFilters
              filters={filters}
              statusOptions={statusOptions}
              sourceOptions={sourceOptions}
              onChange={setFilters}
            />
            {/* Manual entries are located with Hyderabad's place list: for its city only. */}
            {(isDefaultCity || allCities) && (
            <button
              type="button"
              onClick={() => {
                setIsAdding(true);
                setSelectedEventId(null);
              }}
              className="flex h-9 w-full cursor-pointer items-center justify-center gap-1.5 rounded-lg bg-white/10 text-xs font-semibold text-white ring-1 ring-inset ring-white/20 transition hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70"
            >
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-3.5 w-3.5" aria-hidden="true">
                <path d="M8 3v10M3 8h10" strokeLinecap="round" />
              </svg>
              Add an event manually
            </button>
            )}
          </div>
          {/* Never shorter than a few events, so the list stays usable; set in
              from the edge so its scrollbar is not mistaken for the sidebar's. */}
          <div className="md:flex md:min-h-[26rem] md:flex-1 md:flex-col md:pr-2">
            <div className="rei-sidebar-scroll p-4 md:min-h-0 md:flex-1 md:overflow-y-auto md:pr-2">
              <EventList
                state={listState}
                selectedEventId={selectedEvent?.id ?? null}
                articleMatchIds={articleMatchIds}
                onSelect={selectEvent}
                onClearFilters={() => setFilters(DEFAULT_FILTERS)}
                cityName={allCities ? "any city" : city.name}
                onRetry={() => {
                  reload();
                  refreshSources();
                }}
              />
            </div>
          </div>
        </aside>

        <section className="relative h-[42dvh] shrink-0 md:h-auto md:flex-1">
          <EventMap
            events={visibleEvents}
            selectedEventId={selectedEvent?.id ?? null}
            onSelectEvent={selectEvent}
            basemap={basemap}
            cityView={city.view}
            picking={picking}
            pickedPoint={pickedPoint}
            onPickPoint={setPickedPoint}
          />
          <div className="pointer-events-none absolute left-3 top-3 flex flex-col items-start gap-2">
            <div className="pointer-events-auto">
              <BasemapToggle value={basemap} onChange={setBasemap} />
            </div>
            <div className="hidden md:block">
              <MapLegend eventTypes={visibleTypes} />
            </div>
          </div>
          {state.status === "ready" && visibleEvents.length > 0 && locatedCount === 0 && (
            <p
              role="note"
              className="pointer-events-none absolute bottom-10 left-1/2 w-max max-w-[calc(100%-1.5rem)] -translate-x-1/2 rounded-full bg-white/95 px-3.5 py-1.5 text-center text-xs font-medium text-slate-600 shadow-md ring-1 ring-slate-900/10"
            >
              None of these events names a place it can be located by.
            </p>
          )}
          {picking && (
            <p
              role="note"
              className="pointer-events-none absolute left-1/2 top-3 w-max max-w-[calc(100%-1.5rem)] -translate-x-1/2 rounded-full bg-brand-700 px-3.5 py-1.5 text-center text-xs font-medium text-white shadow-md"
            >
              Click the map at the exact spot of the event
            </p>
          )}
          {isAdding && (
            <div className="fixed inset-x-0 bottom-0 z-20 flex max-h-[80dvh] flex-col md:absolute md:inset-x-auto md:bottom-auto md:right-3 md:top-3 md:max-h-[calc(100%-1.5rem)] md:w-[380px]">
              <AddEventPanel
                onClose={() => setIsAdding(false)}
                onCreated={(eventId) => {
                  setIsAdding(false);
                  setSelectedEventId(eventId);
                  refreshAll();
                }}
              />
            </div>
          )}
          {selectedEvent && !isAdding && (
            <div className="fixed inset-x-0 bottom-0 z-20 flex max-h-[60dvh] flex-col md:absolute md:inset-x-auto md:bottom-auto md:right-3 md:top-3 md:max-h-[calc(100%-1.5rem)] md:w-[380px]">
              <EventDetailsPanel
                event={selectedEvent}
                onClose={() => setSelectedEventId(null)}
                footer={
                  // Keyed so a pending/failed state never carries over to another event.
                  <ReviewActions
                    key={selectedEvent.id}
                    event={selectedEvent}
                    onUpdated={refreshAll}
                    pickedPoint={pickedPoint}
                    onPickingChange={changePicking}
                  />
                }
              />
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
