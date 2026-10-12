# Placing events on the map: evaluation of 9 October 2026

How REI puts an event's marker on the map was chosen by scoring candidate
methods against an answer key built from real articles, changing the method,
and scoring again until it stopped improving. The harness and answer key are
in `tools/placement_eval/` and can be rerun.

## The answer key

All 68 text events in the database that were not merged; the 11 rejected ones
were left out, leaving 57. For each, the article was read and the true
location of the road impact written down (`tools/placement_eval/gold.py`):

- 48 events with a place: its reference point taken from OpenStreetMap and
  Google Maps where the two agree (within about 400 m wherever both know the
  place), with a radius for "exact" that is larger for a park, a lake, a long
  road or an area. One is uncertain: the Vaishali Nagar railway underpass,
  which neither source names; Hafeezpet station is used.
- 1 event where no point is right (a Bengaluru rain story naming no road).
- 8 city-wide stories (immersion deployments, rainfall) that are not scored.

## The rubric

| Result | Meaning | Points |
|---|---|---|
| Exact | within the place's radius | 3 |
| Close | within about 1 km | 2 |
| Area | within about 3 km | 1 |
| Missed | no marker, though the article names a placeable place | 0 |
| Wrong | more than 3 km away: another place | -3 |
| Rightly none | no marker where none is right | 3 |
| Should be none | a marker where none is right | -2 |

A wrong marker scores below a missing one: a reviewer can see that an event
has no position, but a confident marker in the wrong place misleads.

Maximum: 147 (49 scored events).

## Results

| Method | Score | Exact | Close | Area | Missed | Wrong |
|---|---|---|---|---|---|---|
| Before (the app on 9 October) | 104 | 33 | 2 | 4 | 7 | 2 |
| OSM with name variants and area-qualified same-name places | 108 | 33 | 4 | 4 | 5 | 2 |
| + first-named place first, weak matches need support, agencies skipped | 110 | 34 | 2 | 4 | 7 | 1 |
| + Google Maps (Serper /places) when OSM has nothing or a weak match | 121 | 38 | 2 | 3 | 4 | 1 |
| + whole names in articles without an AI reading | 128 | 40 | 2 | 1 | 5 | 0 |
| Google first, OSM when Google has nothing | 122 | 38 | 3 | 2 | 4 | 1 |
| Both; the one nearer the article's area when they disagree | 119 | 37 | 2 | 4 | 4 | 1 |
| Google /maps whenever /places has nothing | 128 | 39 | 3 | 2 | 4 | 0 |
| **Chosen: + /maps only when nothing else places the event** | **132** | **41** | **3** | **0** | **4** | **0** |

The chosen method is the app's own code (`services/geo_resolution/placement.py`),
scored through the same harness.

## What each round fixed

- **Same-name places.** "Holy Trinity Church Road" in an article about
  Bolarum went to another Holy Trinity Church 22.5 km away. OSM also has
  "Holy Trinity Church, Bolarum"; a qualified name whose area the article
  names now wins.
- **Junction words.** "Indira Gandhi Rotary" is OSM's "Indira Gandhi Statue";
  "Old PS Saifabad" is "Old PS Saifabad Jn" (it had gone to an "Old Police
  Station" in Madhapur, 7 km away).
- **Weak matches.** "Sanjaynagar Main Road" matched only a locality called
  "Sanjay Nagar" 15 km away. A road or junction matched only to a whole
  locality is used only when another place of the article is within 3 km.
- **Agencies.** "MMRDA" put a Thane crane accident at the MMRDA office in
  BKC, 20 km away. Agency names are not places.
- **Google Maps.** It knows names OSM lacks: Lok Bhavan (the renamed Raj
  Bhavan), Shalibanda X Road, Ramnagar Gundu, Srinagar Colony, the Hitech
  City railway station, Vishwakarma Colony in Suraram.
- **Google's mistakes.** It almost never says "not found". It answered the
  Bolarum army roads with railway stations and a building called "Road",
  "Iqbal Minar" with a place 80 km away, "Government Printing Press Junction"
  with a press 6 km away, and "Bengaluru roads" with the city itself. An
  answer is therefore used only inside the city, and only when its name or
  address carries the name's own words (not the city's name).
- **Order.** The first-named place of the highest role wins, a spot before a
  locality; a more "specific" place named later (Jubilee Check Post in a KBR
  Park story) no longer takes over.
- **Whole names.** In articles without an AI reading, "City Hospital" inside
  "Lake City Hospital" is skipped, and "Hitech City" followed by "railway
  station" is read as the station.
- **Safety, found on the real database.** A district rainfall story's
  "Medchal" was first dropped as far from the article's other places and then
  placed by the wide /maps search at a bus stop called "Medchal". Localities
  are no longer dropped that way, and the wide search is used only for names
  nothing else could find.

## What is still missed

| Event | Why |
|---|---|
| Vaishali Nagar underpass (two reports) | neither OSM nor Google names the underpass |
| Thane crane accident | Thane is outside the Mumbai place list; no point beats the wrong one |
| Heavy rain, Sheikhpet flyover jam | the flyover is named only in the body of an article without an AI reading |

## Cost and limits

- Google answers are cached (`apps/api/.data/google_places_cache.json`); a
  name is never asked twice. The evaluation used about 220 Serper credits;
  applying the method to the stored events used 9 more.
- Daily cap: `PLACE_LOOKUP_DAILY_CREDITS` (60). /places costs 1 credit, /maps 3.
- The answer key was also the set the method was tuned on. Articles read from
  now on are the real test; rerun the harness with new events added to the key.
- Google's terms restrict storing Google Maps coordinates and showing them on
  a non-Google map. The user accepted this on 9 October 2026; the source of
  every position is recorded with the event.
