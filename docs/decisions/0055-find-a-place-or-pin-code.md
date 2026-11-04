# 0055 — Find a place or PIN code on the map

**Status:** 4 November 2026. Code local, tested, for the user to review and push.

## Context

The user, 4 November 2026: "keep a option to type the place or pincode of the
place in the country or in the city … it is easy process to find the required
place in the tool".

## Decision

- **Map toolbar → "Find place"** (magnifier): type a place, street or postcode
  (an Indian PIN such as 500032, "SW1A 1AA", "00-950"), press Enter, choose a
  result; the map moves there (fits the place's area, or zooms to 15 for a point)
  and drops a pin with its name. A new choice replaces the pin; changing city
  removes it. On phones the panel fits the narrow map (icons-only toolbar).
- **Where it searches**: the chosen country (its ISO code) and, for a city, its
  box first; each result says when it lies outside the chosen city. With all
  countries shown, it searches everywhere.
- **Two lookups, both OpenStreetMap** (`app/services/place_search.py`, route
  `GET /api/places/search?q=&city=&local_only=`):
  - REI's own OSM place lists (the cities with a gazetteer: Hyderabad and the
    other Indian cities) answer **while typing** (250 ms after the last key), and
    come first in results: local data, no outside request.
  - OpenStreetMap's geocoder (Nominatim) answers **on Enter only**. Its usage
    policy (operations.osmfoundation.org/policies/nominatim, read 4 November
    2026): "an absolute maximum of 1 request per second" for all users of an
    application; a User-Agent "identifying the application"; search-as-you-type
    "you must not implement … using the API"; "Results must be cached on your
    side"; attribution. So: requests serialised at one every 1.1 s for the whole
    API, User-Agent "JSAN-REI/1.0 (road event intelligence; place search)",
    answers kept in memory for a day (1,000 at most), "Search © OpenStreetMap
    contributors" under the results. A postcode is asked as `postalcode=`.
- Nothing found is stored as an event; the search only moves the map.
- The suggestions while typing never cancel or replace the search Enter asked
  for (found in the browser check and fixed before release).

## Conditions

The public Nominatim service may change or withdraw access, and its policy
says commercial applications "should keep that in mind when relying on this API
for serving paying customers". If REI's console is opened to customers in
numbers, run REI's own Nominatim (or a licensed geocoder) behind the same route.

## Verified

`tests/api/test_place_search.py` (postcodes recognised; PIN asked as a postcode
within the country, with the city's box; the city's place list first and alone
while typing; one request a second; answers remembered; refusal; route);
real lookups (500032 → Ward 105 Gachibowli; "Gachibowli" → REI's places first;
Warszawa Centralna); browser check on a throwaway API and database (Poland,
Hyderabad, phone width; no console errors). Frontend: 272 tests, type check,
lint.
