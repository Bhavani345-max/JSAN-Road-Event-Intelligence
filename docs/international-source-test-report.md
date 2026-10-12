# International source test report

Run on 6 October 2026, against REI's working database (backed up first to
`apps/api/.data/backups/rei-2026-10-06-before-multicity.db`). Every event
counted here is a real event from a real source. No synthetic event was
added to the database; test fixtures stay under `tests/`.

Each official feed was run by hand twice. A run keeps at most 30 records: those
in effect now or starting within seven days, most recently updated first. This
setting (`OFFICIAL_FEED_MAX_RECORDS`) keeps each test city small, as the brief
asked.

## Summary

| | Hyderabad | London | Toronto |
| --- | --- | --- | --- |
| Sources tested | 6 publisher feeds, Serper search | Transport for London | City of Toronto |
| Source class | Publisher, discovery (tier 4) | Official (tier 1) | Official (tier 1) |
| Events in the database | 51 | 31 | 30 |
| Shown in the console now | 20 | 31 | 30 |
| Real events | 51 | 31 | 30 |
| With coordinates | 30 | 31 | 30 |
| With road geometry (line or area) | 0 | 8 (polygons) | 30 (lines) |
| With a road name | 15 | 31 | 30 |
| With a direction | 0 | 6 | 30 |
| With start and end | 7 | 31 | 30 |
| Location: source provided | 0 | 31 | 30 |
| Location: approximate (named place) | 29 | 0 | 0 |
| Location: corrected by a reviewer | 1 | 0 | 0 |
| Location: not located | 21 | 0 | 0 |
| Needing GIS for road-segment geometry | All 51 | 23 (point only) | 0 |
| Needing human review | All open ones (41) | 31 | 30 |
| Duplicate records on a second run | 0 | 0 (29 already held, 1 new) | 0 (30 already held) |
| Same event reported more than once | At least 5 (see below) | 0 | 0 |
| False positives (my judgement) | 2 clear, 3 borderline | 0 | 0 |
| Source failures | 0 | 0 | 0 |

"Needing human review": every event starts as `VALIDATION_REQUIRED`,
whatever its source. None was approved. An approximate location cannot be
approved without a reviewer correcting it first.

## Hyderabad

Sources: Telangana Today, The Hindu, Deccan Chronicle, The Siasat Daily,
NewsMeter and The Hans India (publisher RSS), plus Google News results through
Serper (discovery). All six feeds polled successfully on 6 October after the
changes, and Serper on its schedule.

Event types: traffic diversion 9, road construction 8, flooding 6, public
procession 5, not classified 23.

Reprocessing on 6 October created two events. The reprocess tool now uses the
same classifier as live ingestion, which since 6 October also accepts a
headline naming a known Hyderabad locality. These are "Sangareddy–Patancheru:
a nightmarish journey for road users" (works on NH-65, a real road event) and
"Wrong-side driving increased on Jubilee Hills one-way route" (a false
positive: enforcement, matched by "one-way").

**Reported more than once.** Reports are still not merged across sources. The
KBR Park one-way system appears in five articles from four publishers, and the
Khajaguda Junction diversions in two.

**False positives among the 20 shown (my judgement, not a reviewer's):**

- Clear: "Wrong-side driving increased on Jubilee Hills one-way route"
  (enforcement), and "Nallagandla traffic alert: Aparna Neo Mall signals
  restored" (the problem has ended).
- Borderline: three articles on GHMC revising the KBR Park flyover plans.
  These are plans, though the one-way system they discuss is a real measure.

**Location.** Every located Hyderabad event is approximate: it sits at the
position of a place the article names, drawn as a hollow marker. One event, the
H-CITI works in Gachibowli, carries the location a reviewer set on 5 October,
which was preserved. 21 events name places with no known position and are not
drawn. 11 events name more than one place, and each is now listed with its own
state.

## London (Transport for London)

The first run stored 30 of 116 disruptions; the second stored 1 new one and
recognised 29 as already held.

| | Count |
| --- | --- |
| Road works (utility, TfL, borough, construction) | 27 |
| Accident (vehicle collision) | 1 |
| Road hazard (asset fault) | 1 |
| Not classified (TfL category with no clear REI type, e.g. police activity) | 2 |

- TfL's severity, kept in TfL's words: Minimal 22, Serious 6, Moderate 1,
  No impact 2. REI's own severity is left empty.
- Geometry: 8 events carry TfL's area polygon, and 23 TfL's point. Two carry
  TfL's street segments as lines, with direction and lane closure per street.
- Direction: 6 events, set only where every street TfL lists states the same
  one.
- Every event has TfL's start and end, and the attribution "Powered by TfL
  Open Data".

## Toronto (City of Toronto road restrictions)

The first run stored 30 of 2,047 records, full closures first; the second run
stored none new.

- All 30 are planned road closures, each with the City's polyline, both
  directions affected, a start and an end, and the City's impact level in its
  own words ("Low").
- One quirk was handled: some records send the work type as a fragment of a
  JSON table (`{"tabledata":[{"Option":"Toronto Water"…`), and REI reads the
  name out of it.

## What the run shows

1. **Official sources answer the questions news cannot.** London and Toronto
   events all have dates, and the source's own geometry and road names. Most
   have a direction. Hyderabad's news events mostly lack these, because the
   articles do.
2. **Even official geometry is not always road geometry.** 23 London events
   are points. Matching them to road segments needs the GIS Resolution Engine,
   which is not built. Its interface is.
3. **An approximate location stays visibly approximate.** It is drawn hollow,
   labelled "Approximate", and cannot be approved until a reviewer places it.
4. **De-duplication works per source, not across them.** No record was stored
   twice. The same real-world event reported by several publishers is still
   several events.
5. **Hyderabad has no official source to test.** That is a finding about
   Hyderabad's authorities, not a gap in REI.

## Not verified

- ~~The map canvas.~~ Verified later the same day by driving Chrome through
  its debugging protocol in real time. All three cities render with no errors.
  Hyderabad's approximate markers are hollow. London shows TfL's area band and
  street segment along Waterloo Road. Toronto's closures carry the City's
  details. (The earlier failure was the screenshot method's simulated clock,
  not the console.)
- TfL's and Toronto's update frequency.

## Limitations found

- ~~A record the source updates later is not re-read.~~ Fixed the same day
  ([decision 0010](decisions/0010-official-source-revisions.md)): revisions are
  stored append-only and applied to events in review. A follow-up run stored
  14 real Toronto revisions (closures that came into effect). TfL's timestamp-only
  touches are ignored. A record that disappears from a feed is still not
  treated as an end.
- Events a reviewer acted on before 6 October keep their earlier detection
  data. Their location class is worked out when they are read, but they carry
  no list of affected places.
- Manual entries and the place search are Hyderabad's only. The console hides
  "Add an event manually" in other cities.

## Cross-source merging, run on 6 October 2026

Run on the real database (backed up first to
`apps/api/.data/backups/rei-2026-10-06-before-merging.db`); see
[decision 0011](decisions/0011-cross-source-merging-and-feed-absence.md).

| | Count |
| --- | --- |
| Pairs compared | 2,152 |
| Merge candidates recorded | 17 |
| Merged automatically | 1 |
| Requiring review (pending) | 15 |
| Superseded (overtaken by the automatic merge) | 1 |
| Rejected | 0 (no reviewer has decided yet) |
| Events deleted | 0 (125 events and 1,467 evidence records before and after) |

- **Merged automatically:** "Hyderabad: Why has one-way traffic system around
  KBR Park been made permanent", the same NewsMeter article held twice (from
  NewsMeter's feed and through Google News search). It is now one event
  showing both sources; the NewsMeter record is still reachable on its own
  with its evidence and history.
- **Kept separate for review:**
  - the other KBR Park reports (Siasat, Telangana Today);
  - the two Khajaguda Junction reports (both already reviewed);
  - the NH-65 diversions at Patancheru and at Isnapur, with a location
    conflict;
  - the DLF Gate closure and the CMC H-CITI works, with conflicting end dates
    and locations;
  - the Tank Bund reports, probably different festivals;
  - several Ganesh-festival reports.
- **Conflicts detected:** geometry (NH-65; DLF and H-CITI) and end time (DLF
  and H-CITI).
- **Not matched:** The Hans India's KBR Park report (reviewed before named
  places were recorded; it names "KBR Park flyover" only), and a KBR Park
  report from 16 September (more than two weeks earlier).
