# 0051 — Console UI phase 2: cards, map toolbar, details sections, Analytics, dark mode

**Status:** 30 October 2026. Local, uncommitted, for the user to review. One new
read-only API endpoint; no migration, no ingestion, auth, GIS or data change.

## 1. Event cards

The 64×64 thumbnail stays. Card changes:

- The headline is 15 px, at most two lines, with the full text on hover.
- Spacing is consistent between rows, and the card has a subtle ring and
  shadow.
- Hover and selection change only shadows and rings, never size or position,
  so the list never shifts.
- The GIS badge is square-cornered with a pin, so it never reads as the round
  validation-status pill.
- Truncated places and lines show their full text on hover.

## 2. Map toolbar (`features/map/components/MapToolbar.tsx`)

One floating bar at the map's top left: **Map | Satellite · Filters · Layers**.
Its panels open below it and push the legend down, never covering it or the
details panel.

- **Filters are the console's own state.** The categories are the backend's
  event types present in the loaded events. A new location filter offers the
  location statuses: source provided, GIS resolved, GIS review pending,
  approximate, corrected by a reviewer, QC approved, and not located. The
  sidebar's Filters panel shows both (one state), and the list, the tiles and
  the map all follow it.
- **Counts.** Each choice's count is taken with every other filter applied, so
  the chosen counts add up to the list's.
- **No stale choices.** Changing place resets every filter. A choice that the
  loaded events no longer hold (another view, a reload) is left out rather than
  silently emptying the list.
- **"Traffic congestion" is not offered:** REI has no such category.
- **Layers.** Event markers, clusters (MapLibre's `setClusterOptions`) and an
  optional heatmap. Clustering only changes how markers are drawn, never the
  events, their ids or any count. The heatmap is drawn under every event layer
  and is never hit-tested, so markers stay selectable through it.

## 3. Event details

The details are in four collapsible sections:

- **Event overview.**
- **Source evidence:** the image only under decision 0050's permission rules.
- **Location and GIS:** coordinates, location class, places, map matching,
  Street View.
- **Validation history.**

The history is the event's recorded versions, from the existing
`GET /api/events/{id}`. Each step is named only from its status change or its
recorded reason: detected, sent to QC, validated, rejected, closed, returned to
validation, location corrected, end date extended, severity set, merged, or
updated by the source. REI records no separate "published" step, and none is
shown.

The Human review footer gains a fold toggle. Its actions, their API calls and
their permissions are unchanged. The body scrolls on its own
(`overscroll-contain`).

## 4. Analytics (`/analytics`, `GET /api/events/analytics`)

A new endpoint is needed because the existing count endpoints cannot filter by
date, category, status or source, and have no counts by day or by location
status. Computing these in the browser would mean loading every event, which
crashed production on 29 October (decision 0048).

The endpoint is read only:

- It reads one pass of light columns, never an event's full record or its
  article.
- It counts with the console's own rules (`_tally_names`, `map_rule`), so its
  numbers equal the coverage counts.

**Definitions,** also returned by the API and shown on the page:

- **Total events:** stored events not merged into another (a merged report is
  part of its event; merged reports are counted separately).
- **Status groups, mutually exclusive, adding up to Total:**
  - awaiting validation: DISCOVERED, EXTRACTED, GEO_RESOLVED,
    VALIDATION_REQUIRED, QC_PENDING;
  - validated: APPROVED, SCHEDULED, ACTIVE, MONITORING, EXTENDED, MODIFIED,
    REOPENED;
  - closed: EXPIRED, CANCELLED, SUPERSEDED;
  - rejected: REJECTED.
- **Subsets, overlapping the groups and never added to them:**
  - published: validated events the operations map shows now;
  - in the review queue: events awaiting validation that the queue lists now;
  - GIS pending: not located, approximate, or a road-network match awaiting
    review.
- **Days:** an event's day is the day REI stored it, in the selected city's or
  country's time zone (UTC for all countries). The date range selects on the
  same days: `[start 00:00, end + 1 day 00:00)` in that zone, converted to UTC.

**Verification:** on the local database, every total and breakdown equalled an
independent SQL count and the existing coverage counts.

**Charts:** plain SVG/HTML with no library. There are 7:

- events over time;
- by city;
- by category;
- validation progress;
- source performance;
- GIS resolution;
- status.

Each has hover tooltips, direct value labels and a table view. Status colours
(validated green, awaiting blue, rejected red, closed violet) pass the palette
checks in light and dark: lightness, chroma, colour-blind separation, and
contrast of at least 3:1 on the surface. Status is never shown by colour alone.

## 5. Dark appearance

A light/dark toggle sits in the header (also on Analytics and Users). Light is
the default, and the choice is kept in this browser. An inline script in the
root layout sets `<html data-theme="dark">` before the first paint, so there is
no flash.

The recolouring is one stylesheet block (`app/globals.css`, generated from
Tailwind's own colour values):

- The neutral scale and status tints are re-stepped for a navy surface.
- White surfaces become navy.
- Brand text is lightened in the colour theme's own hue.
- Inside the blue sidebar the tints keep their light values, because they are
  text on blue there.

MapLibre's controls, attribution and popups are restyled. Map tiles and
satellite imagery are untouched, and the sign-in page is unchanged.

Measured contrast on the card surface `#111d31`:

| Text | Contrast |
|---|---|
| Muted | 5.1:1 |
| Secondary | 6.6:1 |
| Links | 7.6:1 |
| Headings | 14.5:1 |
