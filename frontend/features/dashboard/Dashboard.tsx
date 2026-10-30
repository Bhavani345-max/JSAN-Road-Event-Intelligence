"use client";

import dynamic from "next/dynamic";
import { useCallback, useMemo, useState, useSyncExternalStore, type CSSProperties } from "react";
import Header from "@/components/layout/Header";
import { useAuth } from "@/features/auth/AuthGate";
import { canReview, canRunSources } from "@/features/auth/permissions";
import {
  ALL_CITIES,
  ALL_CITIES_ID,
  areaIds,
  citiesIn,
  countryOf,
  DEFAULT_CITY_ID,
  useCities,
} from "@/features/cities/cities";
import CityOverviewList from "@/features/cities/CityOverviewList";
import CountryCities from "@/features/cities/CountryCities";
import { sumStats, toCityBubbles, useCityCounts } from "@/features/cities/overview";
import EventDetailsPanel from "@/features/events/components/EventDetailsPanel";
import EventFilters from "@/features/events/components/EventFilters";
import EventList, { type EventListState } from "@/features/events/components/EventList";
import StatsBar from "@/features/events/components/StatsBar";
import {
  DEFAULT_FILTERS,
  filterEvents,
  hasActiveFilters,
  matchesLocally,
  setFilterCount,
  UNCLASSIFIED,
  withoutStaleChoices,
  type EventListView,
  type EventFilters as Filters,
  type TypeChoice,
} from "@/features/events/filters";
import { LIST_STEP } from "@/features/events/api/eventRepository";
import { useEventSearch } from "@/features/events/hooks/useEventSearch";
import { useEvents } from "@/features/events/hooks/useEvents";
import {
  EVENT_STATUSES,
  EVENT_TYPES,
  isLocated,
  LOCATION_STATUSES,
  locationStatusOf,
  type EventType,
  type LocationStatus,
  type Position,
  type RoadEvent,
} from "@/features/events/model";
import {
  getEventTypeColor,
  getEventTypeLabel,
  LOCATION_STATUS_LABELS,
  setCityTimeZones,
  setDisplayTimeZone,
} from "@/features/events/presentation";
import { computeEventStats } from "@/features/events/stats";
import MapLegend from "@/features/map/components/MapLegend";
import MapToolbar from "@/features/map/components/MapToolbar";
import { DEFAULT_MAP_LAYERS, type MapLayers } from "@/features/map/layers";
import AddEventPanel from "@/features/qc/components/AddEventPanel";
import ReviewActions from "@/features/qc/components/ReviewActions";
import { themeStyle, useTheme } from "@/features/theme/themes";
import type { Basemap } from "@/lib/config";
import CoverageSummary from "./components/CoverageSummary";
import SourceStatusBar from "./components/SourceStatusBar";
import { count, emptyListMessage, partialListNote, sourcesForCity, useCoverage, useSources } from "./sources";

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
  const { user, signOut, updateUser } = useAuth();
  // The colour theme chosen in this browser recolours everything brand-* below.
  const theme = useTheme();
  // The API enforces these too; the console leaves out what it would refuse.
  const mayReview = canReview(user);
  const mayRunSources = canRunSources(user);
  const { sources: allSources, refresh: refreshSources } = useSources();
  const { coverage, refresh: refreshCoverage } = useCoverage();
  const cities = useCities();
  // A link can open the console on a country or city (/?city=india,
  // /?city=london); choosing one in the header overrides it.
  const linkedCityId = useSyncExternalStore(
    subscribeToNothing,
    () => new URLSearchParams(window.location.search).get("city"),
    () => null,
  );
  const [chosenCityId, setCityId] = useState<string | null>(null);
  // All countries together unless one is chosen (or named in the link).
  const cityId = chosenCityId ?? linkedCityId ?? ALL_CITIES_ID;
  const cityOptions = useMemo(() => [ALL_CITIES, ...cities], [cities]);
  const city = cityOptions.find((candidate) => candidate.id === cityId) ?? ALL_CITIES;
  const allCities = city.id === ALL_CITIES_ID;
  const isDefaultCity = city.id === DEFAULT_CITY_ID;
  // The API lists a country's events with its cities' (decision 0035).
  const cityFilter = allCities ? null : city.id;
  // What the choice covers: a city, or a country entry and its cities; null for all.
  const area = useMemo(() => areaIds(city, cities), [city, cities]);
  // Countries first (decision 0036): the chosen country and its cities to choose from.
  const country = countryOf(city, cities);
  const countryCities = useMemo(() => citiesIn(country, cities), [country, cities]);
  const [view, setView] = useState<EventListView>("current_upcoming");
  // All countries: an overview of counts and one bubble per country; a
  // country's events are loaded and drawn only once it is chosen.
  const overview = allCities;
  const showCountryCities = !overview && country !== null && countryCities.length > 0;
  const { state, reload, refresh: refreshEvents, showMore, loadingMore } = useEvents(view, cityFilter, !overview);
  // The list holds more than was loaded (the newest LIST_STEP first).
  const listTotal = state.status === "ready" ? state.total : 0;
  const partial = state.status === "ready" && state.events.length < state.total;
  // The per-entry counts: the overview's, each city's number once a country is
  // open, and the exact tiles of a list not loaded whole.
  const { state: countsState, refresh: refreshCounts } = useCityCounts(
    view,
    overview || showCountryCities || partial,
  );
  const cityBubbles = useMemo(
    () => (overview && countsState.status === "ready" ? toCityBubbles(cities, countsState.counts) : null),
    [overview, countsState, cities],
  );
  // Each event's times are shown in its own city's zone; times with no city
  // (filters) in the selected entry's, or India Standard Time for all countries.
  // Set before anything below renders a time.
  setCityTimeZones(cities);
  setDisplayTimeZone(city.timeZone);
  // The sources of what the choice covers, and those about no city in particular.
  const sources = useMemo(
    () => sourcesForCity(allSources, area === null ? null : { ids: area, country: city.country }),
    [allSources, area, city.country],
  );
  const [chosenFilters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [basemap, setBasemap] = useState<Basemap>("map");
  const [mapLayers, setMapLayers] = useState<MapLayers>(DEFAULT_MAP_LAYERS);
  // Whether the form for entering an event by hand is open.
  const [isAdding, setIsAdding] = useState(false);
  // While a reviewer corrects an event's location, map clicks choose the spot.
  const [picking, setPicking] = useState(false);
  const [pickedPoint, setPickedPoint] = useState<Position | null>(null);
  const changePicking = useCallback((active: boolean) => {
    setPicking(active);
    setPickedPoint(null);
  }, []);
  // The API's search also covers the full article text behind each event, and
  // the events the list has not loaded: its matches replace the loaded ones.
  const serverSearch = useEventSearch(chosenFilters.search, view, cityFilter);
  const serverMatches = useMemo(
    () => (serverSearch ? new Set(serverSearch.events.map((event) => event.id)) : null),
    [serverSearch],
  );

  const loadedEvents = state.status === "ready" ? state.events : NO_EVENTS;
  const loadedAt = state.status === "ready" ? state.loadedAt : null;
  // The API classifies and filters events before counts, list rendering, or
  // map rendering. The same returned page is the source for each surface.
  const allEvents = loadedAt ? loadedEvents : NO_EVENTS;
  const searchedEvents = serverSearch ? serverSearch.events : allEvents;
  // One filter state for the sidebar's Filters and the map toolbar. A choice
  // the loaded events no longer hold (another view, a reload) is left out
  // rather than silently emptying the list; changing place resets them all.
  const filters = useMemo(
    () =>
      state.status === "ready"
        ? withoutStaleChoices(chosenFilters, searchedEvents, [
            ...sources.map((source) => source.id),
            ...searchedEvents.map((event) => event.source.id),
          ])
        : chosenFilters,
    [state.status, chosenFilters, searchedEvents, sources],
  );
  const visibleEvents = useMemo(
    () => filterEvents(searchedEvents, filters, serverMatches),
    [searchedEvents, filters, serverMatches],
  );
  // The toolbar's choices with how many events each would show, given every
  // other filter: chosen ones add up to the list's count.
  const typeOptions = useMemo(() => {
    const counts = new Map<TypeChoice, number>();
    for (const event of filterEvents(searchedEvents, { ...filters, eventTypes: [] }, serverMatches)) {
      const type = event.eventType ?? UNCLASSIFIED;
      counts.set(type, (counts.get(type) ?? 0) + 1);
    }
    return [...EVENT_TYPES, UNCLASSIFIED].map((type) => ({
      value: type as TypeChoice,
      label: type === UNCLASSIFIED ? "Unclassified" : getEventTypeLabel(type as EventType),
      color: getEventTypeColor(type === UNCLASSIFIED ? null : (type as EventType)),
      count: counts.get(type as TypeChoice) ?? 0,
    }));
  }, [searchedEvents, filters, serverMatches]);
  const locationOptions = useMemo(() => {
    const counts = new Map<LocationStatus, number>();
    for (const event of filterEvents(searchedEvents, { ...filters, locations: [] }, serverMatches)) {
      const status = locationStatusOf(event);
      if (status) counts.set(status, (counts.get(status) ?? 0) + 1);
    }
    return LOCATION_STATUSES.map((status) => ({
      value: status,
      label: LOCATION_STATUS_LABELS[status].label,
      tone: LOCATION_STATUS_LABELS[status].tone,
      count: counts.get(status) ?? 0,
    }));
  }, [searchedEvents, filters, serverMatches]);
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
  const filtered = hasActiveFilters(filters);
  // A list not loaded whole: its tiles are the API's counts for the place (the
  // same rules), so they stay exact; with filters, they count what is loaded.
  const areaStats = useMemo(
    () =>
      partial && !filtered && countsState.status === "ready"
        ? sumStats(countsState.counts.filter((entry) => area === null || area.includes(entry.cityId)))
        : null,
    [partial, filtered, countsState, area],
  );
  const stats = useMemo(() => computeEventStats(visibleEvents), [visibleEvents]);
  const listNote = partialListNote({
    loaded: allEvents.length,
    total: listTotal,
    search: serverSearch ? { loaded: serverSearch.events.length, total: serverSearch.total } : null,
    filtered,
  });
  const statusOptions = useMemo(
    () => EVENT_STATUSES.filter((status) => allEvents.some((event) => event.status === status)),
    [allEvents],
  );
  const locatedCount = useMemo(() => visibleEvents.filter(isLocated).length, [visibleEvents]);
  // The map draws only events with a location and a stated start that are not
  // over; the review list also holds the others (decision 0038).
  const mapEvents = useMemo(() => visibleEvents.filter((event) => event.mapEligible), [visibleEvents]);
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

  // An empty list says why: the filters hide the loaded events, or the
  // coverage counts tell no events apart from events this view does not list.
  const emptyList = useMemo(
    () =>
      emptyListMessage({
        placeName: city.name,
        view,
        filtered: hasActiveFilters(filters) && allEvents.length > 0,
        coverage,
        areaIds: area,
      }),
    [city.name, view, filters, allEvents.length, coverage, area],
  );
  const listState: EventListState =
    state.status === "ready"
      ? { status: "ready", events: visibleEvents, now: state.loadedAt, empty: emptyList }
      : state;

  // After a source check or a review decision, reload without a loading flash.
  const refreshAll = useCallback(() => {
    refreshEvents();
    refreshCounts();
    refreshSources();
    refreshCoverage();
  }, [refreshEvents, refreshCounts, refreshSources, refreshCoverage]);

  const changeCity = useCallback((id: string) => {
    setCityId(id);
    setSelectedEventId(null);
    setIsAdding(false);
    setFilters(DEFAULT_FILTERS);
  }, []);

  const selectEvent = useCallback((eventId: string | null) => {
    setSelectedEventId(eventId);
    if (eventId) setIsAdding(false);
  }, []);

  return (
    // Keep the overall page fixed; only the left blue sidebar scrolls.
    <div
      className="rei-app console-screen flex h-dvh flex-col overflow-hidden bg-white text-slate-900"
      style={themeStyle(theme) as CSSProperties}
    >
      <Header
        cities={cities}
        city={city}
        onCityChange={changeCity}
        user={user}
        onSignOut={signOut}
        onUserChange={updateUser}
      />
      <main className="flex min-h-0 flex-1 flex-col-reverse wide:flex-row">
        {/* The entire left blue sidebar scrolls; the page and map stay fixed. */}
        <aside className="rei-sidebar-scroll flex min-h-0 flex-1 flex-col overflow-x-hidden overflow-y-auto bg-linear-to-b from-brand-600 to-brand-700 wide:w-[420px] wide:flex-none sideways:w-[360px]">
          <div className="space-y-3 border-b border-white/15 p-4 wide:shrink-0">
            {showCountryCities && country && (
              <CountryCities
                country={country}
                cities={countryCities}
                selectedId={city.id}
                counts={countsState}
                onSelect={changeCity}
              />
            )}
            {overview ? (
              <StatsBar
                stats={countsState.status === "ready" ? sumStats(countsState.counts) : null}
                unfilteredTotal={countsState.status === "ready" ? sumStats(countsState.counts).total : 0}
              />
            ) : (
              <StatsBar
                stats={state.status !== "ready" || (partial && !filtered && !areaStats) ? null : (areaStats ?? stats)}
                unfilteredTotal={partial ? listTotal : allEvents.length}
              />
            )}
            <div className="flex min-h-9 items-center justify-between gap-3">
              <h2 className="text-xs font-semibold text-white">
                {view === "validation" ? "Needs validation" : "Current and upcoming road events"}
              </h2>
              <button
                type="button"
                onClick={() => {
                  setView(view === "validation" ? "current_upcoming" : "validation");
                  setSelectedEventId(null);
                }}
                className="shrink-0 rounded px-1.5 py-1 text-xs font-semibold text-white/90 underline decoration-white/50 underline-offset-2 transition hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70"
              >
                {view === "validation" ? "Back to operations" : "Open review queue"}
              </button>
            </div>
            <CoverageSummary coverage={coverage} areaIds={area} view={view} />
            <SourceStatusBar sources={sources} view={view} onChecked={refreshAll} canRun={mayRunSources} />
            {!overview && (
              <EventFilters
                filters={filters}
                statusOptions={statusOptions}
                sourceOptions={sourceOptions}
                onChange={setFilters}
              />
            )}
            {/* Manual entries are located with Hyderabad's place list: for its city only. */}
            {isDefaultCity && mayReview && (
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
          {/* Event list continues in the same scrollable blue sidebar. */}
          <div className="p-4">
            <div>
              {overview ? (
                <CityOverviewList
                  state={countsState}
                  cities={cities}
                  view={view}
                  onSelect={changeCity}
                  onRetry={() => {
                    refreshCounts();
                    refreshSources();
                    refreshCoverage();
                  }}
                />
              ) : (
                <>
                  {listNote && <p className="mb-3 text-[11px] leading-4 text-brand-100">{listNote}</p>}
                  <EventList
                    state={listState}
                    selectedEventId={selectedEvent?.id ?? null}
                    articleMatchIds={articleMatchIds}
                    onSelect={selectEvent}
                    onClearFilters={() => setFilters(DEFAULT_FILTERS)}
                    onRetry={() => {
                      reload();
                      refreshSources();
                      refreshCoverage();
                    }}
                  />
                  {partial && !serverSearch && (
                    <button
                      type="button"
                      onClick={showMore}
                      disabled={loadingMore}
                      className="mt-3 flex h-9 w-full cursor-pointer items-center justify-center rounded-lg bg-white/10 text-xs font-semibold text-white ring-1 ring-inset ring-white/20 transition hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70 disabled:cursor-wait disabled:opacity-70"
                    >
                      {loadingMore
                        ? "Loading…"
                        : `Show ${count(Math.min(LIST_STEP, listTotal - allEvents.length))} more`}
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        </aside>

        <section className="relative h-[42dvh] shrink-0 wide:h-auto wide:flex-1">
          <EventMap
            events={mapEvents}
            selectedEventId={selectedEvent?.id ?? null}
            onSelectEvent={selectEvent}
            basemap={basemap}
            cityView={city.view}
            picking={picking}
            pickedPoint={pickedPoint}
            onPickPoint={setPickedPoint}
            cityBubbles={cityBubbles}
            onSelectCity={changeCity}
            accent={theme.palette[600]}
            layers={mapLayers}
          />
          {/* Above the map's own controls (attribution, scale), below the details panel. */}
          <div className="pointer-events-none absolute left-3 top-3 z-10 flex max-w-[calc(100%-1.5rem)] flex-col items-start gap-2">
            <MapToolbar
              basemap={basemap}
              onBasemapChange={setBasemap}
              layers={mapLayers}
              onLayersChange={setMapLayers}
              typeOptions={typeOptions}
              selectedTypes={filters.eventTypes}
              onTypesChange={(eventTypes) => setFilters({ ...filters, eventTypes })}
              locationOptions={locationOptions}
              selectedLocations={filters.locations}
              onLocationsChange={(locations) => setFilters({ ...filters, locations })}
              onClearAll={() => setFilters({ ...filters, eventTypes: [], locations: [] })}
              matchCount={visibleEvents.length}
              onMapCount={mapEvents.length}
              otherFilterCount={
                setFilterCount(filters) -
                (filters.eventTypes.length > 0 ? 1 : 0) -
                (filters.locations.length > 0 ? 1 : 0) +
                (filters.search.trim() ? 1 : 0)
              }
              filtersDisabled={overview}
            />
            <div className="hidden wide:block sideways:hidden">
              <MapLegend eventTypes={visibleTypes} overview={overview} />
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
            <div className="fixed inset-x-0 bottom-0 z-20 flex max-h-[80dvh] flex-col wide:absolute wide:inset-x-auto wide:bottom-auto wide:right-3 wide:top-3 wide:max-h-[calc(100%-1.5rem)] wide:w-[380px] sideways:fixed sideways:left-2 sideways:right-auto sideways:top-16 sideways:bottom-2 sideways:max-h-none sideways:w-[344px]">
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
            <div className="fixed inset-x-0 bottom-0 z-20 flex max-h-[60dvh] flex-col wide:absolute wide:inset-x-auto wide:bottom-auto wide:right-3 wide:top-3 wide:max-h-[calc(100%-1.5rem)] wide:w-[380px] sideways:fixed sideways:left-2 sideways:right-auto sideways:top-16 sideways:bottom-2 sideways:max-h-none sideways:w-[344px]">
              <EventDetailsPanel
                event={selectedEvent}
                onClose={() => setSelectedEventId(null)}
                footer={
                  mayReview ? (
                    // Keyed so a pending/failed state never carries over to another event.
                    <ReviewActions
                      key={selectedEvent.id}
                      event={selectedEvent}
                      onUpdated={refreshAll}
                      pickedPoint={pickedPoint}
                      onPickingChange={changePicking}
                    />
                  ) : (
                    <p className="border-t border-slate-200 px-5 py-3 text-xs text-slate-500">
                      View-only account: review decisions are made by an administrator.
                    </p>
                  )
                }
              />
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
