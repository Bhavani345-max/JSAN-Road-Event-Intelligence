# 0036 — Countries first: every city within its country

**Status:** local only, 19 October 2026. Not committed, not deployed. Waits for
the user's review.

## Context

Decision 0035 grouped cities under their country where a country entry
existed (Canada with Toronto, the United States with New York City). India,
the United Kingdom, Germany and Belgium had no entry, so their cities stood on
their own in the selector, and the header listed countries and cities side by
side.

On 19 October 2026 the user asked to "remove the cities from the website but
when we select India we can get the data/events from all the cities of India
by using the sources of cities", for every country: the cities' sources keep
collecting, each city counts under its country, and choosing a country shows
its cities and their events.

## Decision

### Every city lies within a country entry

- New country entries (`backend/packages/cities/data/`): `india`,
  `united-kingdom`, `germany`, `belgium`. Each has `"level": "country"`, a
  map view of the whole country, and no source of its own
  (`official_sources` empty, no place list): choosing it covers its cities'
  sources and events (India: Hyderabad, Ahmedabad, Bengaluru, Chennai, Delhi,
  Kolkata, Mumbai, Pune).
- `load_cities()` now refuses a city whose country has no entry, so a city
  added later always falls under its country.
- `GET /api/cities` gives every city a `parent_id`. `GET /api/events?city=india`
  lists the events of every Indian city (and Hyderabad's records from before
  cities existed); `city=hyderabad` still lists Hyderabad's only. Summary and
  coverage keep one row per entry (India's own row is 0); the console adds a
  country's cities to it, as for Canada.
- Events, sources and the database are unchanged: events keep the city they
  were recorded with. The only side effect of the new entries is the one
  every entry has: the registry lists a Google News RSS source for it
  (`google-news-rss-india`, ...), BLOCKED by Google's terms and never polled.

### The console offers countries, then their cities

- Header: the first list offers **All countries** and the countries by name,
  no city. Once a country is chosen, a second list offers "All of India" and
  its cities.
- Sidebar: "Cities in India" lists the same choices with what each lists in
  the view on screen (from `GET /api/events/summary`): "All of India 17 ·
  Hyderabad 13 · Bengaluru 3 · Mumbai 1 · ..." in the review queue.
- Overview of all countries: one card and one map bubble per country, each
  counting its cities' events too ("India · 8 cities"); cities get none.
- Links keep working: `/?city=delhi` opens India with Delhi chosen;
  `/?city=india` opens India.

## Verified

- Tests: backend (country entries, the refusal, India's list, search, summary
  per entry), frontend (country choices, a city's country, a country's
  cities, bubbles per country, per-choice counts); type check and lint.
- In headless Chrome against an API on a copy of the local database (GET
  only): All countries lists 11 countries and no city; choosing India shows
  the eight cities and India's events from Hyderabad, Bengaluru and Mumbai on
  one map; the Hyderabad chip narrows to Hyderabad; `/?city=delhi`,
  `/?city=united-kingdom` and Canada's review queue as described; the header
  fits at phone width.

## Not done here

- No new source was connected: India's coverage is still what its cities'
  connected sources give (Hyderabad's news feeds; most Indian publishers'
  terms forbid automated use, decisions 0024, 0032, 0033). Adding a city of
  any country is a city file plus, for a new country, its entry; sources still
  need terms that permit REI's use.
- No database, Railway or production change; nothing committed or pushed.
