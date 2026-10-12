# 0008 — Wider search, more wordings, and the most exact place the article names

**Status:** accepted, 6 October 2026. Extends [0006](0006-named-place-location-and-stated-dates.md).

## Why

The Google News source had yielded 5 events from 79 results. Three things
held it back, none of them a shortage of searches:

1. Google ranks Delhi's and Bengaluru's road news above Hyderabad's even for
   a "Hyderabad traffic" search, so most results were about other cities.
2. The searches covered the past week only, and the papers report few new
   road measures in any one week.
3. Real Hyderabad road articles were not detected because the wording was not
   a rule ("blocked roads", "one-way", "traffic alert", "vehicles barred"),
   or the article was out of scope because it named a locality rather than
   the city ("Sangareddy-Patancheru"), or the place was spelled differently
   from OpenStreetMap ("Dilsukhnagar", "Lakdikapul") or missing from the
   gazetteer (Tank Bund, Quthbullapur, the airport).

## Decision

- **Searches target Hyderabad and exclude the crowding cities.** Twelve
  searches, each naming Hyderabad and one kind of measure, with
  `-Delhi -Bengaluru …` appended. Polling every 8 hours searches the past
  week; `apps/api/search_sweep.py` searches the past month (or year) by hand.
  A result whose headline names another city, or that is not in Latin
  script, is dropped before any page is read.
- **More wordings are strong signals.** Roads blocked or barricaded, one-way,
  no entry, traffic alert, traffic regulations and arrangements, route
  diversions, alternative routes, vehicles barred, closed for repairs, road
  dug up, cave-ins, "avoid the route", "restrictions imposed". The rule stays:
  one strong signal *and* a named place.
- **Scope by place as well as by city.** A headline that names another city
  (and not Hyderabad) is out of scope whatever the summary says. A headline
  that names a known Hyderabad locality, ward or junction is in scope even if
  "Hyderabad" is not written. "Mumbai Highway" and the like are roads, not
  cities.
- **More explicit date wordings.** "From October 10 to 18", "October 10-18",
  "till October 18" (an end alone) and "on October 2" (one day) are read, in
  the headline or summary for the last two. Weekdays, "this weekend" and
  times of day are still not.
- **A bigger gazetteer, and the spot within the locality.** The gazetteer
  now includes wards, stations, hospitals, colleges, places of worship,
  markets, malls, the airport and dams, and knows joined and split spellings
  ("Dilsukhnagar" / "Dilsukh Nagar") and a short list of names the papers use
  for a feature OpenStreetMap names differently ("Tank Bund" → Tank Bund
  Road). When the headline names a locality and the headline or summary also
  names a junction, flyover or landmark within 2.5 km of it, the event is put
  at that spot and `detection.location.within` records the locality. A spot
  named only in the body is not used: it may be a diversion route.

## What is still not done

- The marker is still the position of the named place on OpenStreetMap, not
  the surveyed extent of a closure. Road-network matching (PostGIS) is still
  held back. The "Correct location" review action remains the way to put an
  event at an exact spot the article does not name.
- Reports of the same event from different publishers are still separate
  events. The sweep makes this more visible (four articles on the KBR Park
  one-way system). Merging is still held back.
- Nothing is dated from vague wording. An advisory "for the festival" with
  no dates is shown as a recent report for seven days and then not at all.
- Serper's free credits are a one-time 2,500; the polling settings use 36 a
  day. See [the source notes](../data-sources/google-news-search.md).
