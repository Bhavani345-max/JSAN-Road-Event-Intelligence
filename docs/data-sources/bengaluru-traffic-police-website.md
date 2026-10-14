# Bengaluru Traffic Police website: upcoming events and works

- **Source id:** `bengaluru-traffic-police-website` · **Class:** AUTHORITATIVE_OFFICIAL · **Tier:** 1 · **City:** Bengaluru
- **Endpoint:** `GET https://btp.karnataka.gov.in/en` (no key, no login)
- **Connector:** `connectors/official/bengaluru_traffic_police.py`
- **Status:** CONNECTED, run by hand in the test phase:
  `python backend/cli/ingest_source.py bengaluru-traffic-police-website`.
- **Research:** [docs/cities/bengaluru-source-research.md](../cities/bengaluru-source-research.md)

## What it gives

The home page's "UPCOMING EVENTS / PRESS NOTES" panel: a server-rendered
list of planned works and events, one line each in a fixed form:

```
Department Work : White Topping Work at New Diagonal Road, Jayanagar. near 7th Main Road,
Byrasandra, Bengaluru South City Corporation, Bengaluru, Bengaluru Urban, Karnataka, 560011,
India | Start : 00:00 Hrs 07-10-2026 and End : 04-01-2027
```

Kinds seen: "Department Work", "Public Event", "Private Event". Items have no
id, link, PDF or coordinates; most say "near None". The panel is repeated
in a scrolling card and a "View All" dialog; the dialog (the whole list) is
read. 39 lines on 8 October 2026.

The same page's "TRAFFIC ALERTS" (congestion points with coordinates,
breakdowns, "construction occurred at") are transient and **not read**: whether
REI should carry such alerts is the user's decision. The force's actual
advisories (diversions, one-ways) are published on X only, which REI does
not read.

## How REI reads it

| Line part | REI |
| --- | --- |
| kind + description | title ("Department Work: White Topping Work at New Diagonal Road, Jayanagar") |
| description near address (the address cut before its administrative tail) | description |
| Department Work → ROAD_WORKS; Public Event, Private Event → SPECIAL_EVENT | event type |
| kind | `source_category` |
| "Start : HH:MM Hrs DD-MM-YYYY" | start, in Bengaluru's time zone |
| "End : DD-MM-YYYY" | end of that day |
| the whole "Start … End …" phrase | `stated_period` |
| the "near" address ("7th Main Road, Byrasandra") | an affected location, located by its most exact known part |
| the line itself | evidence (`raw.line`) and the item's identity (SHA-256), since the source gives none |
| — | attribution "Source: Bengaluru Traffic Police (btp.karnataka.gov.in), Upcoming Events / Press Notes." |

**Location.** No coordinates. An item is placed at a known place its title
or address names (the Bengaluru place list built from OpenStreetMap, 8,994
located names), recorded as APPROXIMATE, drawn hollow and not approvable
until a reviewer places it. The address's administrative tail ("Bengaluru
South City Corporation, Bengaluru Urban, Karnataka, 560011, India") is not
a place. A name that is many features ("7th Main Road", "Freedom Park") is
known but not one spot, so it stays unresolved and the next part of the
address is tried. An item naming no known place stays unlocated for a
reviewer. A line with neither a description nor a place ("None near None")
states nothing a reviewer could check and is not a record.

**Absence.** The list is the whole current list, so the connector reports
what it saw; an item missing for three refreshes is flagged for review,
never ended (decision 0011).

## Terms and limits

- Centre for e-Governance copyright policy (site footer): information "can
  be re-published in any media form free of any charge only with prior
  permission" by email. Recorded, not resolved: `terms_status`
  REVIEW_REQUIRED, commercial use UNKNOWN.
- robots.txt allows everything. No rate limit is published. A run makes one
  request (215 KB); the source is set to poll every six hours if scheduled.

## Verified 8 October 2026

39 lines on the live page (saved as `backend/tests/fixtures/btp_homepage_2026-10-08.html`):
26 records (13 "None near None" lines left out), all with a start and an
end, 15 located by a named place. A run keeps the items in effect or starting
within a week, so later-October venue events wait for a later run. Live run
result: see the [decision record](../decisions/0017-mumbai-and-bengaluru-official-listings.md).
