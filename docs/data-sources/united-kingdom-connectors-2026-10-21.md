# United Kingdom: new official connectors, 21 October 2026

Follow-up to `europe-official-road-sources-2026-10-16.md` (sources 2, 12 and
15). London's TfL connector already existed and is unchanged.

| Source | Source id | Result |
| --- | --- | --- |
| Scottish Road Works Register disruptions export | `scotland-srwr-disruptions` | **Built** (`backend/connectors/official/srwr.py`) |
| Traffic Wales roadworks RSS | — | **Not built: awaiting permission** (terms silent on commercial use) |
| TrafficwatchNI roadworks RSS | — | **Not built:** no coordinates in any item |

**Method.** Everything was fetched live on 21 October 2026 between 10:59 and
11:06 UTC.
- **User-Agent:** REI's own (`Settings.http_user_agent`).
- **robots.txt:** read on every host before anything else.
- **Requests:** sequential and at least 2.5 s apart. They were:
  - `downloads.srwr.scot`: 5 (robots.txt, the file listing, then the dry run's
    listing, file link and its redirect)
  - `traffic.wales`: 4 pages
  - `roadworks.scot`: 2
  - `www.trafficwatchni.com`: 2
  - `rss.trafficwatchni.com`: 2
  - the SRWR blob store: 1 download
- **Samples:** one trimmed sample, saved as a test fixture. Nothing else was
  fetched again.

## 1. SRWR disruptions export (Scotland): built

**Licence, read 21 October 2026:**
- <https://roadworks.scot/publications/scottish-road-works-register-open-data>:
  "Open Data from the SRWR is available under the Open Government Licence v3".
- OGL v3 allows commercial and non-commercial use with attribution.
- The page gives no attribution wording, so the records carry the licence's
  default statement: "Contains public sector information licensed under the
  Open Government Licence v3.0 (Scottish Road Works Register, Office of the
  Scottish Road Works Commissioner)."

**The same page describes the export:**
- It is "a summary of the activities which could have a disruptive effect on
  the road network … a daily extract … which includes Road Works, Events,
  Permissions, but not Potential Works."
- The SRWR "is updated daily overnight".

**robots.txt:**
- `roadworks.scot` disallows only Drupal admin, search and user paths.
- `downloads.srwr.scot` has no robots.txt (404).

**How a run works:**
1. `GET /disruptions-export/api/v1/files/` lists the last 7 daily zips.
2. `GET /file/<newest>/` returns a signed download link, valid about 10
   minutes. The link is never stored or logged.
3. The zip is downloaded (7.3 MB).
4. `CurrentActivities.csv` (25 MB) is streamed row by row with the csv module
   over a text wrapper on the zip member.

A row's British National Grid shape can be longer than the csv module's
128 KB field limit. The limit is raised only while the file is read, then
restored.

**Mapping.** Every value comes from the row:

| REI field | Taken from |
| --- | --- |
| Point | `Latitude`, `Longitude` (WGS 84) |
| Start / end | `StartDateTimeUTC` / `EndDateTimeUTC` |
| Severity (source's words) | `TrafficImpact` |
| Status (source's words) | `ActivityStatus` |
| Category | `Category` / `LicenceType` / `TrafficManagement` |
| Place | `Street`, `Locality`, `Town` |
| Id | `ActivityReference#PhaseNumber` |
| Published time | `LastUpdatedDateTimeUTC` |

The `GeometryFull` WKT is in British National Grid (EPSG:27700). It is kept in
the stored row as evidence but not converted, because REI has no tested
OSGB36 transform.

**Event type:**

| Activity | REI type |
| --- | --- |
| `Category` "Event" | Special event |
| Road Closure or Slip Closure, category Emergency | Emergency road closure |
| Road Closure or Slip Closure, any other category | Planned road closure |
| Lane Closure, Hard Shoulder Closure, Contraflow, Road Narrowing | Lane restriction |
| Any other works category | Road works |
| Anything else (a permission under traffic lights, say) | No type; the reviewer decides |

**Not taken:**
- Rows whose traffic management is "No Obstruction On C/W Or F/W" or "Works
  Entirely On The Footway". The source states that the carriageway is
  untouched.
- Activities whose end has passed but that are still listed. They count as
  observed, not kept.

**Live dry run, 21 October 2026.** One `fetch()`, export
`SRWRDisruptionsExport20261021.zip`, nothing written to any database.
- **Rows:** 21,866 in the CSV. 2,993 were not taken (1,509 footway, 1,484 no
  obstruction), leaving 18,873 observed. 855 of those have ended, so
  **18,018 were kept**: 4,813 in force and 13,205 upcoming.
- **Fields:** all 18,018 are located and all have a start and an end.
- **Types:**
  - Road works: 9,250
  - Planned road closure: 5,749
  - Lane restriction: 2,078
  - No type: 592
  - Special event: 320
  - Emergency road closure: 29
- **Status:**
  - Proposed: 7,860
  - Advance Planning: 4,648
  - In Progress: 2,740
  - Recorded: 1,500
  - Commenced: 759
  - Potential: 511
- **Run cost:** 13 s, about 190 MB peak Python memory. The CSV is streamed;
  the memory is the 18,018 records the connector interface returns.
- **Revisions:** between the 16 and 21 October exports, no row changed
  without its `LastUpdatedDateTimeUTC` changing. 3,170 of 19,422 rows were
  updated in those five days. The revision key is therefore the whole row.

**For the user to decide:**
- **Volume.** About 18,000 events on the first run, and some hundreds revised
  each day. That is far more than any other feed.
- **End equal to start.** 1,685 kept activities (9%) give the same start and
  end: midnight local time, `PhaseDuration` 1 or 0. They look like date-only
  entries. They are kept exactly as stated, so each ends the moment it starts
  and is hidden as expired on its own day. Reading them as whole days would be
  an interpretation, so it was not done.
- **"Potential" status.** 511 rows are "Potential", although the page says the
  export excludes potential works. They are kept, with the status in the
  source's own words.

**Files:**
- `backend/connectors/official/srwr.py`
- `backend/tests/unit/test_srwr.py` (11 tests)
- `backend/tests/fixtures/srwr_current_activities_2026-10-21.csv`: 21 real
  rows from today's export. Rows with an email address, a phone number or a
  postcode were not picked. Every promoter is an organisation.

## 2. Traffic Wales roadworks RSS: awaiting permission (not built)

Its terms do not state commercial use either way. Under REI's rule, silent
terms mean awaiting permission.

**Evidence, read 21 October 2026:**
- <https://traffic.wales/developers>:
  - "Traffic Wales traffic information is available to use in third party
    applications. Terms and conditions apply and vary according to the type of
    data feed … Traffic Wales website terms and conditions, privacy policy and
    copyright policies apply. Traffic Wales must be credited as the data
    source. Access may be revoked if usage causes degradation to our services."
  - For RSS: "No registration is required."
  - Nothing on commercial use.
- <https://traffic.wales/copyright-statement>:
  - "You may use and re-use the information featured in this website
    (excluding logos, maps and data therein) free of charge … under the terms
    of the Open Government Licence."
  - Then, under "Road traffic alert data and CCTV images": "If you wish to
    reproduce our road traffic alert data or CCTV images, we encourage you to
    use the supported methods described in our Developers page."
  - So it is not clear that the OGL covers the feed data.
- <https://traffic.wales/terms-and-conditions>:
  - Disclaimers, coverage and hyperlinking only. Nothing on commercial reuse.
  - Alerts include data "sourced … from Highways England", which is third-party
    data.
- **robots.txt:** `/feeds/` is not disallowed.
- **Not fetched today:** the feed itself (it is not being built).

**To unblock:** written confirmation from Traffic Wales that the RSS may be
used in a commercial product. The developers page names a contact route.

## 3. TrafficwatchNI roadworks RSS: not built (no geometry)

**Terms, read 21 October 2026.**
<https://www.trafficwatchni.com/twni/terms-and-conditions>: "Traffic feeds may
be freely used on commercial sites subject to the following conditions: DfI
Traffic Information and Control Centre is credited as the information source.
All URLs in the feed are preserved and remain functional." The terms permit
REI's use.

**robots.txt:** 404 on both hosts.

**Why not built.** The live feed today (1.02 MB) holds 1,789 items, and none
has coordinates: no `georss`, `geo:` or latitude/longitude element or
attribute. The location is only the title ("ROAD, STREET, TOWN"). REI hides
unlocated events and keeps unlocated feeds off (decision 0029), so it was
skipped.

## Registry (to be added by whoever edits `registry.py`)

```python
from .official.srwr import SrwrDisruptionsConnector, srwr_source
```

In `_official_sources`, in the `feature_feeds` tuple:

```python
            # United Kingdom, Scotland (21 October 2026).
            (srwr_source, SrwrDisruptionsConnector),
```

In `backend/packages/cities/data/united-kingdom.json`:

```json
"official_sources": ["scotland-srwr-disruptions"]
```
