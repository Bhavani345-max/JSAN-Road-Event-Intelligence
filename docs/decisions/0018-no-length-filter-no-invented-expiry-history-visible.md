# 0018 — No length filter, no invented expiry, history reachable

Date: 2026-10-08. Status: accepted. Supersedes the 200 m minimum of
[0016](0016-minimum-road-block-length-and-public-events.md) and the
"no way to reach hidden events" part of
[0014](0014-current-only-review-and-storage-retention.md).

## Context

The brief of 8 October 2026 (three Indian city PoCs) states three rules that
differ from what was built on 5 and 7 October:

- s.8, marked CRITICAL: "Do NOT filter out real events merely because the
  affected road is shorter than 100 metres or 200 metres … Source-provided
  distance always wins. Store source distance, source unit, normalized
  metres, geometry provenance."
- s.16: "Do not use an arbitrary 7-day or 30-day expiry rule to decide
  whether an event is real … If the source says 'Till further orders' do not
  invent an end date. If an official source disappears: do NOT automatically
  mark the event ended."
- s.17: "Do not hide legitimate current events simply because they are
  short. Historical/expired events may be hidden by default, but must remain
  accessible through filters/history."

The same morning the user had asked whether short road blocks were being
filtered out (see the addendum to [0017](0017-mumbai-and-bengaluru-official-listings.md)).

## Decision

**The length minimum is off.** `MIN_ROAD_BLOCK_LENGTH_M` is 0
(`packages/source_models/road_block.py`); nothing is dropped for length by
the connectors, the classifier or reprocessing. The measurement itself is
kept and now recorded on every event built from a source that draws a line:
`detection.source_geometry_length_m`, the length of the source's own
geometry (its line, else the stretches it marks closed), measured on that
geometry and never used to drop the event. The console shows it as "Length
of the stretch the source draws: N m". Closures rejected under 0016 are
restored by reprocessing (they were rejected by reprocessing, so it brings
them back as VALIDATION_REQUIRED; nothing was deleted). Public-event
closures were never subject to the minimum.

**Source distance, unit and metres.** `stated_distance` (the source's words,
since 0017) is joined by `stated_distance_m`, the same number in metres read
from the stated unit (m, metre, km, मीटर, कि.मी.). The words stay the record;
20 m is kept as 20 m. Geometry provenance is the existing location class
(SOURCE_PROVIDED, HUMAN_CORRECTED, GIS_RESOLVED, APPROXIMATE, UNRESOLVED).

**No invented expiry for official records.** An event an official source
states itself (`detection.method = "source_provided"`) that gives no end
("Till Next Order") stays current until its source reports it ended, its
source stops listing it and a reviewer closes it (the absence flag of 0011,
never an automatic end), or a reviewer rejects, cancels or expires it. The
7-day (30 for works) window now applies only to news reports that state no
times, and only as the console's default view, not as a test of whether the
event is real. Same rule in `services/lifecycle/current.py` and the
console's `isCurrent`.

**History is reachable.** A "Show history (ended, rejected and old events)"
box in the console's filters brings back everything the default view hides.
Off by default. The user's choice of 5 October (hide them fully) is replaced
by the brief's rule.

## What this changes for the user

- Toronto and London: the short utility closures of 7 October are events
  again (as drawn, with their measured length shown). The Toronto run keeps
  short closures from now on; the 30-record cap per run is unchanged.
- Mumbai: the 25 Traffic Police notices are current until a reviewer or the
  source says otherwise, so their approximate points now show on the map.
  Some are orders for days that have passed (the listing's English states
  no dates; the PDFs do). That is the OCR gap of 0017, and the reviewer can
  reject or expire them.
- Nothing is deleted, no evidence is altered, and no event was approved.

## Result on 8 October 2026

Backup `apps/api/.data/backups/rei-2026-10-08-before-no-minimum.db`.
Reprocessing: 64 events restored (62 Toronto, 2 London; all rejected on
7 October for their length), 36 updated (the measured length and the
distance in metres recorded), 0 rejected, nothing created or deleted.
100 events now carry the length of the source's own line; 59 of them are
under 100 m and 64 under 200 m, kept as drawn. Hyderabad events are
unchanged. Tests: 657 Python, 81 console, all passing.
