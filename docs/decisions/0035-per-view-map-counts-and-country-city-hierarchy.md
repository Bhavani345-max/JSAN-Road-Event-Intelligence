# 0035 — Map counts per view, and countries with the cities within them

**Status:** local only, 16 October 2026. Not committed, not deployed. Waits for
the user's review.

## Context

The read-only review of decision 0034 (16 October 2026, 14:05 UTC) found:

- The new coverage line and each source's row said "N on the map", adding the
  review queue's map (events awaiting review) and the operations map
  (validated events) together, whatever the view. In the default operations
  view the United States read "3979 on the map" beside an empty map and "No
  current events": events awaiting review looked like events on the
  operations map.
- A saved WZDx test response (Indiana DOT) held a named employee's work name
  and e-mail, copied from the feed's own contact fields.
- Toronto stood beside Canada as a peer in the city list, and choosing Canada
  left out Toronto's events, sources and counts (the same for the United
  States and New York City). The data was already right: Toronto's city file
  says country CA, its source says country CA and city `toronto`, and its
  events record the city "Toronto".

The user asked (16 October 2026) to fix all three locally.

## Decision

### Each map counted on its own

- `EventRepository.tally` counts `on_map_review` (events awaiting review that
  the review queue's map shows) and `on_map_operations` (validated events the
  operations map shows) and no longer any sum of the two. Events hidden from
  a map are counted per map: `hidden_review_<rule>` and
  `hidden_operations_<rule>`.
- `GET /api/events/coverage`: per entry `on_map_review`, `on_map_operations`,
  `hidden_review`, `hidden_operations` (the combined `on_map` and `hidden` are
  gone). `GET /api/sources`: `on_map_review_count` and
  `on_map_operations_count` replace `on_map_count`.
- The console's coverage line follows the view on screen: "N on this map ·
  validated, in effect or upcoming" (operations) or "N on this map ·
  awaiting review, not yet confirmed" (review queue); then detected, awaiting
  review, validated, rejected, closed; then what is not on this map and why.
  In the operations view every event awaiting review is listed there as "not
  confirmed", with how many the review queue's map shows. A source's row says
  "N on this map" for the view on screen.

### No personal data in the saved WZDx response

`backend/tests/fixtures/wzdx_indot_sample_2026-10-16.geojson`: the two
`contact_name` and `contact_email` values (feed information and data source)
are now "Example Contact" and `contact@example.com`. Nothing else changed
(checked by comparing the parsed documents). The other fixtures of 16 October
hold no e-mail address or person's name; Tokushima's numbers are road
offices' telephone lines, given with the office's name.

The local database's stored evidence of the live Indiana poll still holds the
feed as received; it was not changed.

### Countries and the cities within them

- A city file may say `"level": "country"`: Australia, Canada, Finland,
  France, Japan, South Africa and the United States do. A country has at most
  one such entry (checked when the files load). The cities with the same
  country code lie within it: Toronto within Canada, New York City within the
  United States. India, the United Kingdom, Germany and Belgium have no
  country entry; their cities stand under their country's name.
- `packages/cities`: `country_entry(city)`, `cities_within(country)`,
  `area_of(entry)`. `GET /api/cities` gives each entry's `level` and
  `parent_id`.
- `GET /api/events?city=canada` lists Canada's own events and Toronto's;
  `city=toronto` Toronto's only. The same for search (`q`) and
  `GET /api/merge-candidates?city=`. Events keep the city they were recorded
  with; nothing is copied, moved or deleted.
- `GET /api/events/summary` and `/coverage` keep one row per entry, each its
  own events, so all cities together count every event once; the console
  adds a country's cities to it.
- Console: the selector groups entries by country ("Canada (incl. Toronto)",
  then "Toronto" under Canada); the overview of all cities lists each country
  with its cities indented under it, a country's number being what choosing
  it lists; a country's map bubble counts its cities too; the coverage line
  and the source list of a country cover its cities, and a city never lists
  its country entry's sources (Toronto does not list DriveBC). Links such as
  `/?city=toronto` and `/?city=delhi` are unchanged.

No migration: the level is in the city files, not in the database.

## Not done here

- No database, Railway or production change; nothing committed or pushed.
- No country entry was invented for India, the United Kingdom, Germany or
  Belgium (no national source is configured for them).
