# 0033 — Open-ended events, five Indian metro cities, South Africa, GDELT, news terms

**Status:** local only, 16 October 2026. Not committed, not deployed. Waits for
the user's review and approval.

## Context

On 16 October 2026 the user asked:

1. To use GDELT (gdeltproject.org) as a global discovery source.
2. Why South Africa shows no events.
3. To show an event whose source states a start but no end ("if start date is
   there and end date is not there consider"). Until then the console hid
   any event missing a start or an end (decision 0029).
4. For more news feeds for India, more Indian cities, "all the metropolitan
   cities", and why Hyderabad has fewer events and sources than a few days
   before.

A second brief the same day required: include only sources whose terms permit
REI's (commercial) use; record every rejected source with its reason; no
bypassing of access restrictions; leave everything local until approved.

## Decision

### Events with a start and no end are shown (`services/lifecycle/current.py`)

- The console shows a located event with a stated start that has not ended.
  An event with no stated start is still unconfirmed and hidden.
- A start with no end means "until further notice":
  - an official record (`source_provided`) is shown until its source reports
    it over or a reviewer closes it, as for an end date;
  - an event read from an article (`keyword_rules`, `ai_reading`) is shown
    for `OPEN_END_TEXT_DAYS` = 30 days after its stated start, then hidden as
    expired. A reviewer can extend it. Nothing is deleted.
- The database filter (`app/repositories/events._shown_filters`) and the
  per-city counts apply the same rule; the 30-day check reads the detection
  record (`_hidden_by_detection`). The requirements scorecard (R4, R5) follows.

### Five Indian metro cities and South Africa's metro areas

- City files `delhi`, `chennai`, `kolkata`, `pune`, `ahmedabad`
  (`backend/packages/cities/data/`), each with scope terms, the cities that
  crowd its news out, and an OpenStreetMap place list built with
  `build_gazetteer` (located names: Delhi 7,184; Chennai 4,986; Pune 3,378;
  Kolkata 3,243; Ahmedabad 1,790).
- South Africa (a country file) has a place list over seven metro areas
  (`gazetteer_areas`: Johannesburg, Ekurhuleni, Tshwane, Cape Town,
  eThekwini, Nelson Mandela Bay, Mangaung): 13,931 located names. A name used
  in more than one metro has no position, so it is never placed by guess.
  Scope terms name the metros and their authorities (JMPD, Johannesburg Roads
  Agency, SANRAL ...).
- `build_gazetteer` tries three Overpass servers in turn (the main one
  answered 502 or 500 during the builds) and merges several areas.
- Detection rules, version 2026-10-16: `roadworks`, `detour`, `stop/go`
  (South African wording). Nothing else changed.

### GDELT news search (`connectors/discovery/gdelt.py`)

- One source per city with a place list (`gdelt-<city>`): the DOC 2.0 API,
  ArtList JSON, the last day, one request per city every 2 hours. All GDELT
  requests in the process share one pace: at least 6 seconds apart (GDELT
  asks for 5). A refusal (HTTP 429) or a message instead of results fails
  that poll; it is retried at the next poll, never at once.
- Query: `"<City>" (<10 road phrases>) sourcecountry:<FIPS> sourcelang:english`
  (FIPS: India IN, South Africa SF). South Africa searches its whole press
  with its own phrases.
- A result is kept only if its headline or address names the city and its
  headline names no other city; publishers whose terms forbid automated
  access and the publisher the user removed are left out before anything is
  stored.
- **Publisher pages:** an article is read from its page only when the
  publisher's terms permit it (`READABLE_PUBLISHERS`: sanews.gov.za,
  pib.gov.in). From any other publisher only GDELT's own result is kept
  (headline, address, the time GDELT saw it); its page is never requested.
- GDELT's data may be used commercially with a citation and a link
  (gdeltproject.org/about.html#termsofuse); recorded as the source's
  attribution.
- **Off by default** (user's decision after the evaluation below):
  `GDELT_SEARCH_ENABLED` defaults to false, and the local `.env` says so
  explicitly. Off, the searches are registered as VALIDATED and inactive,
  with no connector: the scheduler cannot poll them. `true` switches them on.

### Publisher terms (`connectors/restricted.py`, `connectors/registry.py`)

Research of 16 October 2026: `docs/data-sources/india-national-feeds-2026-10-16.md`,
`india-local-and-official-sources-2026-10-16.md`, `south-africa-sources-2026-10-16.md`.

- **Added to RESTRICTED_PUBLISHERS** (terms forbid automated access,
  scraping, or storing their pages; quoted in code): indiatimes.com (Times of
  India, Economic Times, Bangalore Mirror), hindustantimes.com, livemint.com,
  livehindustan.com, indianexpress.com, deccanherald.com, freepressjournal.in,
  timesnownews.com, news18.com, indiatoday.in, moneycontrol.com, theprint.in,
  lokmattimes.com. This also stops the (local-only) Google News search and AI
  reading from using them. Evidence stored earlier is kept.
- **Awaiting permission, not connected:** The New Indian Express city feeds
  (Hyderabad, Bengaluru, Chennai, Delhi, Mumbai, Kolkata) and Millennium Post
  (Delhi, Kolkata). Verified working; their terms pages hold only privacy
  text, so nothing permits commercial use. One test poll each was run on 16
  October before the "permitted only" brief (292 articles, 5 events kept as
  evidence).
- **Connected:** SAnews (South African Government News Agency), free to use
  with credit; its policy addresses media, so a confirmation is advisable
  before commercial launch.
- **REMOVED_PUBLISHERS:** thehansindia.com (decision 0026) is left out of the
  GDELT search. The Google News search and AI reading are unchanged, as
  decision 0026 recorded.
- **Mid-day disconnected** (the user's decision, 16 October 2026): its terms
  grant personal use only and exclude incorporating content into an
  information retrieval system. Registered without a connector
  (`RESTRICTED_SOURCES`), `mid-day.com` added to `RESTRICTED_PUBLISHERS`;
  its stored articles and events are kept. Telangana Today and NewsMeter are
  unchanged (terms silent).
- **The New Indian Express and Western Cape** stay pending until written
  permission.

### Sources the registry does not know; AI reading only for connected sources

- `IngestionService.tools_for_source` raises `UnknownSource` for a source the
  registry does not know, instead of using Hyderabad's rules (a registered
  source without a city is still Hyderabad's). Reprocessing leaves such items
  as they are (`ReprocessResult.unknown_source`); AI reading skips them.
- AI reading sends an article to the model only when its source is connected
  (`IngestionService.ai_may_read`): never one awaiting permission, restricted,
  removed (this now includes The Hans India's stored articles) or unknown.

### One article listed twice in one poll

A search source (DISCOVERY) keeps the first of several new results with the
same headline in one poll (syndicated copies on several sites); a publisher's
own feed is not compared this way.

### RSS reader

The article body is the first non-empty content element (The New Indian
Express puts an empty image description first).

## Evaluation, 16 October 2026 (local database, real data)

- **GDELT DOC API refused 33 of 44 requests** (HTTP 429): 24 of 34 during the
  research (09:48–10:31 UTC; four request pairs of the research overlapped,
  under 5 seconds apart), and 9 of 10 in the controlled run (10:47:12–10:57:50
  UTC, 69–74 seconds apart, after a 15-minute pause). The one answer
  (Kolkata) held no articles. A 7-day search holds only about 23 hours of
  Indian articles. The GEO API answers 404.
- **Saved responses through the real pipeline:** Delhi 18 results, of which 7
  are from publishers whose terms forbid automated access (they were the 7
  real road-event headlines), 1 does not name Delhi, 10 kept headline-only,
  0 road-event candidates. Mumbai (2 and 25 results), Pune (1), the South
  Africa metro query (0) and Kolkata (0): nothing kept. South Africa broad
  query (`traffic sourcecountry:SF`, 17): 2 kept, 0 candidates; its only
  road-related headlines name a suburb (Krugersdorp, Wadeville) or a short
  form ("Bloem") outside the scope terms, and none is a closure.
- **Recommendation:** do not rely on the GDELT DOC API now; switch it off by
  default (GDELT_SEARCH_ENABLED=false) until the API answers reliably or
  GDELT's ngram files are evaluated. Its value under the "permitted only"
  rule is headline leads for review, never dates or positions.
- **Mixed-version side effect:** the local API running the code from before
  this change processed the test-poll articles of sources it did not know
  with Hyderabad's rules (its `tools_for_source` falls back to the default
  city for an unknown source). Its AI reading read 292 articles with the
  wrong city and rejected the 5 events of the test poll ("No longer
  detected as a road event"). The new code knows these sources; the
  fallback for an unknown source should still be removed.
- **Duplicate headlines in one poll:** syndicated copies (same headline,
  different sites) found in one GDELT poll are stored separately; the
  pipeline compares headlines only with articles already stored.

## Not done

- Relative dates ("today", "on Saturday") are not read (the user's decision).
  Measured on 16 October 2026 under a strict rule (publisher's own time with
  a zone, word in headline or summary, one word only, not past tense, not
  published midnight–4 am, weekday 1–6 days ahead): of 65 open text events
  without a start, 52 have no relative word up front, 10 name the
  publication's own weekday (this week or next?), 1 has two, 2 pass, and of
  those one is long over (10 May) and the other's "on Monday" is when an
  official inspected the site, not the road measure. None can be dated safely.

## Correction of the wrong AI readings (applied locally, 16 October 2026, with the user's approval)

- The local API was restarted at 11:50:55 UTC on the current code (database
  `backend/.data/rei.db`, no DATABASE_URL anywhere; GDELT off). Backup first:
  `backend/.data/backups/rei-2026-10-16-before-ai-reading-correction.db`.
- `backend/cli/correct_ai_readings.py` (`app/services/ai_reading_correction.py`),
  check-only by default, applied at 11:52 UTC to an exact list of records:
  - the 314 AI readings written 09:57–11:50:45 UTC by the API on older code
    for sources it did not know (The New Indian Express 240, Millennium Post
    52, SAnews 10, GDELT 12) were moved, unchanged, to
    `classification_details["ai_superseded"]` with the reason, the time and the
    article's classification at the time. Nothing was deleted;
  - the 5 events that API rejected (EVT-114A304F2CA7, EVT-1E62A2ABD127,
    EVT-4545E2387EEC, EVT-A2F3B9A60D33, EVT-B0F2937F33A8) were re-derived with
    their own city's rules: a third version, VALIDATION_REQUIRED, "Detected
    again as a road event with keyword rules (...)". Versions 1 and 2 are kept.
    Their sources stay awaiting permission: nothing is reconnected.
- Re-derivation keeps `ai_superseded` (`reprocess_service._record_classification`).
- Verified against the backup: 314 of 314 readings kept identical; no other
  article changed; 11,676 → 11,681 event versions, none altered. `--undo`
  on a copy of the database put all 314 articles back exactly as they were
  and rejected the 5 events again with a fourth version.
- SAnews (connected, permitted) is read again by AI reading with South
  Africa's rules; the other 304 articles are not sent (their sources are not
  connected).
- No coordinates are taken from GDELT (its GEO API is offline, and city-level
  points are not road events).
- Western Cape's 47 located closures (start dates, no ends) now pass the
  display rule but wait for written permission for commercial use.
- Nothing is committed, pushed or deployed; no Railway setting is changed.
