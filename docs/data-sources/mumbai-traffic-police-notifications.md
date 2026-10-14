# Mumbai Traffic Police notifications

- **Source id:** `mumbai-traffic-police-notifications` · **Class:** AUTHORITATIVE_OFFICIAL · **Tier:** 1 · **City:** Mumbai
- **Endpoint:** `GET https://mtperp.mahatrafficechallan.gov.in/PublicNotice.htm` (no key, no login)
- **Connector:** `connectors/official/mumbai_traffic_police.py`
- **Status:** CONNECTED, run by hand in the test phase:
  `python backend/cli/ingest_source.py mumbai-traffic-police-notifications`.
- **Research:** [docs/cities/mumbai-source-research.md](../cities/mumbai-source-research.md)

## What it gives

A static HTML table ("Public Notice List") of the 50 newest notifications
the Mumbai Traffic Police issue under section 115 of the Motor Vehicles Act
(1,605 since 2009; 207 in 2026 to 5 October). Each row:

- the notice number ("Notification No 209/DCP/West/Traffic/Temp/2026");
- the date it was issued and its validity ("Till Next Order" on every row);
- a subject and a one-line English summary (often the same words);
- a link to the signed order as a PDF.

The PDFs are scanned Marathi images with no text layer. They are the real
order (roads, junctions, from–to points, dates and clock times, alternate
routes); the listing's English is usually only a heading. **REI does not read
the PDFs**: no OCR library is installed on the development machine and
Devanagari OCR quality is untested. The PDF link is kept with every event as
its source reference, for the reviewer.

## How REI reads it

| Listing field | REI |
| --- | --- |
| subject + notice number | title ("Traffic Restrictions and Alternative Routes (Notification 209/2026)") |
| English summary | description |
| the notice's own words: marathon, procession, VVIP, bridge/ROB, excavation/works, diversion/alternate route, closed, no turn, one way | event type; **none** when the words do not say ("Traffic Arrangement") |
| subject | `source_category` |
| "Till Next Order" | `source_status` |
| a date written day/month/year in the summary ("on 26/08/2026", "until 31/05/2027", "from … to …") | start/end, with the words kept as `stated_period`; **no date otherwise** (the issue date is not the start) |
| road names written in the summary ("Poonya Shlok Ahilyabai Bridge", "Mumbai Central Junction") | `affected_locations`, unresolved, and `affected_road` |
| a distance written in the summary ("100 meter") | `stated_distance`, verbatim |
| PDF link, percent-encoded byte for byte | source reference |
| — | attribution "Source: Mumbai Traffic Police notifications (Public Notice List, Brihanmumbai Police)." |

**Location.** The listing has no coordinates. An event is placed at a known
place the title or summary names (the Mumbai place list built from
OpenStreetMap, 6,288 located names), recorded as APPROXIMATE, drawn hollow
and not approvable until a reviewer places it: "Closure of roads in Dadar
Division" sits at Dadar. A notice that names no known place is still the
city's event (the source publishes for Mumbai only: `covers_city`), with its
location UNRESOLVED and nothing drawn, for a reviewer to place from the PDF.

**Parking-only notices** (no parking, pay-and-park suspended, odd–even
parking) state no change to the road network. They are stored as evidence
and go through the ordinary keyword detection, not taken as road events.

**No absence tracking.** The page is the 50 newest notices, not the orders
in force, so a notice dropping off it says nothing about the order ending.
The connector reports no `observed_ids`; nothing is ever counted missing.

## Terms and limits

- No terms and no robots.txt on this host. The departmental website's policy:
  material "may be reproduced free of charge after taking proper permission
  by sending a mail to us", with the source acknowledged. Whether that
  applies to this listing, and whether REI's intended use needs the mail, is
  **unresolved**: `terms_status` REVIEW_REQUIRED, commercial use UNKNOWN.
- No rate limit is published. A run makes one request (36 KB); the source is
  set to poll every six hours if it is ever scheduled.

## Verified 8 October 2026

50 rows parsed from the live page (saved as
`backend/tests/fixtures/mumbai_public_notices_2026-10-08.html`): 41 road notices and
9 parking-only. Of the 41, 23 state a type in their English words, 5 name a
known place, 1 states a date. The rest need the PDF. Live run result: see the
[decision record](../decisions/0017-mumbai-and-bengaluru-official-listings.md).

## Addendum, 8 October 2026

- **PDF file name as a hint.** The order's file name, as the division saved it
  ("Notification No 189, Ghatkopar Div 1"), often names the locality or
  division. It is read as a fallback location: the notice is placed by it only
  when the English summary names no known place, approximately, with the
  file-name words kept. With it, 16 of 26 stored notices have a point.
- **Re-reading.** `rebuild_structured(raw)` redoes the connector's reading of
  a stored row, so `backend/cli/reprocess.py` applies rule changes to stored
  notices too. The row itself is never altered.
- **Why the map may still be empty.** Undated notices show for seven days
  after their date (decision 0014). Dates come only from the English summary,
  which rarely states them; the PDFs hold them.
