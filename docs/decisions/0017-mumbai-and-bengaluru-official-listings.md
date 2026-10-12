# 0017 — Mumbai and Bengaluru: official listings without coordinates

Date: 2026-10-08. Status: accepted (Phase 2 of the brief of 7 October 2026,
built after the Phase 1 research in `docs/cities/`).

## Context

The brief of 7 October 2026 asked for Mumbai and Bengaluru proofs of concept
on free, public sources, with a hard stop after source research. The research
([mumbai](../cities/mumbai-source-research.md),
[bengaluru](../cities/bengaluru-source-research.md)) found one usable official
source per city, and both differ from London's and Toronto's feeds in the same
way: **they publish words, not coordinates.**

- Mumbai Traffic Police publish their notifications (orders under s.115 MV
  Act) as a static HTML table of the 50 newest, each with a scanned Marathi
  PDF. The English column is usually a heading ("Traffic Arrangement").
- Bengaluru Traffic Police publish a list of planned works and events on
  their home page, each with a kind, a description, a "near" address (often
  "None") and start and end dates. Their actual advisories go out on X only.

## Decision

**Two city configurations** (`packages/cities/data/mumbai.json`,
`bengaluru.json`): Greater Mumbai and Greater Bengaluru areas, India Standard
Time, scope words, other-city exclusions, discovery searches (defined, not
run: the Google News search still searches Hyderabad only, so Serper credits
are unchanged). Hyderabad stays the default city and comes first in the city
list whatever the file order.

**Two place lists** built from OpenStreetMap by the existing tool
(`python -m services.geo_resolution.build_gazetteer --city mumbai|bengaluru`):
Mumbai 6,538 names, 6,288 with a position; Bengaluru 9,590 names, 8,994 with
a position. The cities' own names are generic, never a location.

**Two official connectors**, both AUTHORITATIVE_OFFICIAL, tier 1, CONNECTED,
run by hand with the 30-record limit like London's and Toronto's:

- `mumbai-traffic-police-notifications` ([details](../data-sources/mumbai-traffic-police-notifications.md)):
  reads the table rows. Type from the notice's own words or none; dates only
  when written day/month/year in the English summary (the issue date is not
  the start); road names as written; a distance verbatim ("100 meter"); the
  PDF link kept byte for byte. Parking-only notices are evidence, not events.
  No absence tracking: the page is the newest 50, not the orders in force.
- `bengaluru-traffic-police-website` ([details](../data-sources/bengaluru-traffic-police-website.md)):
  reads the "Upcoming Events / Press Notes" list. Department Work is
  ROAD_WORKS; Public and Private Event are SPECIAL_EVENT with the kind kept
  as the source's category; start and end as stated, in Bengaluru's zone;
  the "near" address cut before its administrative tail. "None near None"
  lines are not records. The transient traffic alerts are not read.

**Structured records without geometry are located like articles.** A record
an official source states in words (no geometry) is placed at a known place
its title, summary or location names point to, from the city's place list,
as APPROXIMATE (decision 0006), with the OpenStreetMap reference kept. An
address is read from its most exact known part ("Kalidasa Road, Gandhinagar,
Bengaluru Central City Corporation…" → Kalidasa Road). A record naming no
known place is still the city's event when its source publishes for that
city alone (new `SourceEvent.covers_city`), with its location UNRESOLVED and
nothing drawn, for a reviewer to place. The source's own geometry, when it
has any, is never relocated by name; London and Toronto are unchanged.
APPROXIMATE locations remain unapprovable until a reviewer places them (QC
rule, unchanged).

**Three news feeds connected** as discovery-only, tier 4, on the generic RSS
connector, chosen because their items carry text and their robots rules allow
the path: Mid-Day Mumbai, The Siasat Daily (Mumbai tag; the same publisher as
the connected Hyderabad feed) and The Hindu Bengaluru (the same structure as
the connected Hyderabad feed). Hindustan Times, Times of India, Indian
Express, TV9 Kannada and Deccan Herald are in the registry as researched and
not connected, with the reason. No publisher's terms have been legally
reviewed, as before.

**Kept verbatim from the source, new fields:** `stated_period` (the words the
dates were read from, already shown in the console) and `stated_distance`
(a distance in the source's words, shown in the details panel as "Distance
as the source states it", never measured by REI).

## The brief's conflicts, resolved conservatively

- **200 m minimum versus "preserve 20–30 m source closures".** Unchanged
  (decision 0016). Neither new source draws a line, so nothing is measured
  and nothing is dropped for length; a stated distance is kept as text.
  Revisiting the minimum is the user's call.
- **Confidence tiers.** Not added. REI's confidence stays empty (decision
  0005); the source tier, class and location class say what is known.
- **Corridors and multi-stretch events.** Not added. Every road or place the
  source names is listed in `affected_locations`; the drawn geometry is still
  one point or the source's own shape.

## What was deliberately not built

- **No OCR of the Mumbai PDFs.** The real orders (roads, from–to points,
  clock times, alternate routes) are scanned Marathi images. No OCR library
  is installed and pip is broken on this machine; Devanagari OCR quality is
  untested. Until then most Mumbai notices have no location and no dates in
  REI and need the reviewer to open the PDF. This is the single biggest gap.
- **No Bengaluru traffic alerts** (congestion points with coordinates): the
  user's decision whether transient alerts belong in REI.
- **No X / social media**, where the Bengaluru advisories actually are.
- **No scheduling**: both official sources run by hand, like London's and
  Toronto's (`OFFICIAL_FEEDS_SCHEDULED=false`).
- **No re-use permission asked** of either authority; both policies ask for
  a mail before re-publication. Recorded as REVIEW_REQUIRED.
- No GIS import for either city; no routing; no AI extraction.

## Result on 8 October 2026

Backup: `apps/api/.data/backups/rei-2026-10-08-before-mumbai-bengaluru.db`
(198 events: Hyderabad 58, London 48, Toronto 92).

| Source | Records kept | Events | Located | Dated |
| --- | --- | --- | --- | --- |
| Mumbai Traffic Police notifications | 30 (5 parking-only, evidence) | 25 | 1 (Dadar) | 0 in force (the one dated notice, 26/08/2026, had ended) |
| Bengaluru Traffic Police website | 16 (in effect or within a week) | 16 | 7 | 16 |
| Mid-Day Mumbai | 30 | 0 | — | — |
| Siasat Mumbai | 40 | 1 | 1 | 0 |
| The Hindu Bengaluru | 60 | 2 | 1 | 0 |

Of the research's recommended first events: Bengaluru's New Diagonal Road
white-topping (B1) is in, located at Jayanagar, dated 7 Oct 2026 – 4 Jan
2027; the Chandapura NH-48 jam and the Sanjaynagar Main Road works came in
from The Hindu; "Closure of roads in Dadar Division" (E10) is in, at Dadar,
undated. Mumbai's Seezer Road bridge closure (E1, notification 209) is in
but, as the listing's English names no road, it is unlocated and undated:
exactly the PDF gap above. The Sagarpark Road no-parking order (E3) is
evidence only, by the parking rule.

Because most Mumbai notices are undated, the console's current-events rule
(decision 0014) shows only the ones reported in the last seven days; the
rest are stored and reachable through the API.

Tests: 656 Python tests pass (19 new in
`tests/unit/test_mumbai_bengaluru_sources.py`, on the two pages as fetched on
8 October 2026); the console type-checks and its 79 tests pass.

## Addendum, 8 October 2026 (afternoon): where the point goes

The user saw no Mumbai points on the map and asked whether short road blocks
had been filtered out and whether points had been moved. Checked and fixed:

- **No length filter touched either city.** The 200 m minimum (decision 0016,
  the user's rule) applies only when a source draws the closed stretch
  (Toronto, London). Neither new source draws anything: every Mumbai and
  Bengaluru record is classified SOURCE_PROVIDED_EVENT or, for parking-only
  notices, NOT_RELEVANT; none is BELOW_MINIMUM_LENGTH.
- **No existing point moved.** All 198 pre-existing events have the same
  geometry as in the morning's backup. The new points are approximate
  named-place positions, drawn hollow, never presented as exact.
- **Priority corrected.** The source's own location field (Bengaluru's "near"
  address, a road the Mumbai summary names) now outranks a place in the
  title; only then comes a place named in the title or summary; last, a hint
  the source gives only indirectly. One point moved: "5TH MAIN CHAMARAJPET"
  from the ward's centre to Puttanna Chetty Road, the address the source
  gives (about 300 m).
- **The order's PDF file name as a last-resort hint.** Half of the Mumbai
  file names, written by the issuing division, name the locality or division
  ("Notification No 189, Ghatkopar Div", "52. Dadar - angarki sankashti
  chaturthi notification"). They are read as a `fallback` location: used only
  when nothing else places the notice, listed as an affected location only
  when it is a known place, with `found_in` "source" and the file-name words
  kept as the mention. A file name with no place ("DocScanner 6 Oct 2026")
  leaves the notice unlocated and is not listed.
- **Reprocessing re-reads stored official rows.** A connector may offer
  `rebuild_structured(raw)`, which redoes its structured reading from the
  stored row or line; reprocessing uses it, so stored notices follow the
  current rules like articles do. The stored evidence is not altered.

Result after reprocessing (backup `rei-2026-10-08-before-location-priority.db`):
15 events updated, none elsewhere. Mumbai: 16 of 26 events placed (was 2),
all APPROXIMATE at a locality or division; Bengaluru: 8 of 18 (unchanged in
number). **The Mumbai map still shows no point today**: the console shows an
undated notice for seven days after its date (decision 0014), and the only
two Mumbai notices from the last seven days (209 and 208) have no place in
their English text or file name. The 14 placed notices are older and hidden
by that rule. The ways to see Mumbai points are the user's decision: read the
Marathi PDFs (OCR, giving roads and dates), lengthen the window for official
notices, or a reviewer placing them from the PDF.

Noted for review, not decided by me: the Siasat Mumbai event "CJP denied
permission for Oct 2 stir at Shivaji Park" is a public event that did not get
permission, so it is a likely false positive.
