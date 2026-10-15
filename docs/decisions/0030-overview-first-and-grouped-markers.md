# 0030 — An overview of all cities first; nearby markers grouped when zoomed out

**Status:** accepted, 15 October 2026.

## Context

With Canada and Australia added (decision 0029), "All cities" opened on more
than 6,000 markers across the world. It loaded every event (about 13 pages of
500), and drew rings of markers with lines at every zoom: decision 0029
spread events sharing a spot around it. The user sent a screenshot (Brittany,
regional zoom) and asked to show no points on opening, only those of the
country or city chosen, so the console looks neat and clean.

## Decision

- **"All cities" is an overview.** The map shows one bubble per configured
  country or city with how many events the current view lists (operations
  or review queue). The bubble is grey at 0, and clicking it opens that
  place. The side panel lists the same places with their counts, and the
  tiles add them up. No event is loaded or drawn. The counts come from
  `GET /api/events/summary?view=…`, which uses the same rules as the lists
  (tested to equal each city's list total). It loads in under a second.
- **A chosen country or city shows its own events.** Zoomed out (up to zoom
  13), markers near each other are drawn as one numbered circle (MapLibre
  clustering). Clicking it zooms in until they come apart.
- **Spreading events that share a spot** around it, with a line to the spot,
  now happens only at street level (zoom 14 and closer), where it helps to
  pick one. Zoomed out, the numbered circle replaces the ring.
- Nothing about the events changes: positions, geometry and the details
  panel are as before; only the drawing is grouped.

## Consequences

- Opening the console is fast and the map is readable at every zoom.
- The event list and filters appear once a place is chosen; a link
  `/?city=<id>` still opens a place directly.
- The overview's numbers are the operations view's (approved, current or
  upcoming) or the review queue's, whichever is chosen. In production most
  places show 0 until events are approved.
- Tests: `frontend/features/cities/overview.test.ts`,
  `frontend/features/map/stacking.test.ts` (no spreading below street
  level), and `backend/tests/api/test_console_lists.py` (overview counts
  equal the lists).
