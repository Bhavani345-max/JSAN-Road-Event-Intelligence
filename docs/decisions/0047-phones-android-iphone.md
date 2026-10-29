# 0047 — The website on phones: Android, iPhone and the rest

**Status:** 29 October 2026. Code local, tested, for the user to push. Web
only; no API, database or Railway change.

## Context

The user asked (29 October 2026) whether REI works on Android, then: "I want
this website to support Android and all other phones; an app is not required."
REI stays a website opened in the phone's browser. Nothing is installed, so
there is no web app manifest and no offline mode.

A check that day in an emulated Android phone found that REI already worked on
a phone held upright: map above the list, details as a sheet from the bottom, no
sideways scrolling. Three things fell short:

- **Small controls.** Buttons, city chips, review buttons and the details close
  button were 28–32 px; Apple asks for 44 pt and Android for 48 dp.
- **A phone held sideways.** From 768 px wide the desktop layout applies, and
  the map key covered most of the map. On iPhones it is worse: Safari keeps the
  notch area clear, so an iPhone 14 sideways is 750 × 340 px, under 768. It got
  the upright layout, with a 143 px map above a 141 px list.
- **Map dots.** A tap counted only within 6 px of a dot's edge, which is fine
  for a mouse but hard to hit with a finger.

iPhone Safari also zooms into any form field with text under 16 px when it is
tapped, and REI's locked screen then stays zoomed.

## Decision

### Touch screens: controls a finger can hit (`app/globals.css`)

On screens whose main pointer is a finger (`pointer: coarse`: phones and
tablets of any make):

- every button, every link laid out as a box, and every select and text field
  is at least 44 × 44 px. Links inside a sentence keep their size. The map's
  zoom buttons grow with them;
- text fields and selects use 16 px text, so Safari does not zoom;
- a tap on the map hits a dot, line or area within 18 px instead of 6
  (`EventMap.hitBox`).

Screens used with a mouse or trackpad are unchanged.

### A phone held sideways: map beside the list

There are two new layout variants:

- `wide`: at least 768 px wide, or at least 640 px wide and no taller than
  520 px. This replaces `md` for the console's side-by-side layout.
- `sideways`: at least 640 px wide and no taller than 520 px. 520 px is the
  height of the sign-in page's existing "very short screens" step.

On a phone held sideways:

- the list sits beside the map and narrows to 360 px, so the map keeps room;
- event details (and Add an event) open as a card **over the list**, not over
  the map, so the event stays visible on the map, as map apps do sideways;
- the map key is hidden, as it already is on a phone held upright;
- the header's PoC badge shows only "PoC", so the title still fits.

A screen under 640 px wide and short (old small phones held sideways) keeps
the upright layout.

### Header on a phone held upright

Below 640 px wide only the JSAN mark shows. The name "JSAN Road Event
Intelligence" is kept for screen readers. With the larger buttons it would
otherwise be cut to a few letters ("J…" on an iPhone SE for an administrator).

### Two fixes found while testing (the user asked for them the same day)

- **Number tiles on narrow phones.** "Scheduled" is 52 px wide at the tiles'
  11 px, but a tile on a 360–390 px phone has 45–51 px of room, so it showed
  "Schedu…" and "To revie…". The tile row is now a container: narrower than
  23rem, its tiles get 6 px side padding instead of 8 and 10 px labels. Every
  label then fits from a 360 px phone up, sideways too. Wider rows are
  unchanged. A 320 px phone (iPhone SE 1st gen, 2016) still cuts "Scheduled"
  and "To review" slightly; the full name stays in the tooltip.
- **Place names under a pin.** The `placeLabels` layer (a place the source
  names with a role, such as closed, affected or diversion route) set no
  `text-font`. MapLibre then asked OpenFreeMap for its default font ("Open
  Sans Regular, Arial Unicode MS Regular"), got a 404, and drew no names, on
  every device. The layer now uses the basemap's own font (`labelFont`), as
  the cluster and city labels already did.

### Unchanged

Desktop and laptop layouts, data, roles, every API call, and the sign-in page,
which already handled short and narrow screens. The console's single locked
screen also stays: on every phone only the list (and the details card) scrolls.

## Supported browsers

Tailwind CSS 4, which the site is built with, needs Safari 16.4+ (iOS 16.4,
March 2023), Chrome 111+, Firefox 128+, and Samsung Internet on a recent
Chromium. Phones updated in the last few years have these. Older browsers are
not supported.

## Tests

Playwright with touch taps and each phone's screen size, against a copy of the
local database served by a throwaway API on port 8011, deleted afterwards:

- **Chrome (Android):** Pixel 7 and Galaxy S24, upright and sideways.
- **WebKit, Safari's engine (iPhone):** iPhone 14 upright and sideways, iPhone
  SE (3rd gen) upright and sideways, iPhone 15 Pro Max.
- **Desktop Chrome with a mouse,** as the control.

On each phone the test signed in, opened the console, the review queue and an
event's details, tapped 20 px from a map dot's centre, opened the country list
and the profile dialog, and for administrators the User management page. It
then measured sideways scrolling, controls under 44 px, field text size, and
where the details card sits.

Every phone passed: no sideways scrolling, no control under 44 px, fields at
16 px, and the off-centre tap opened the event. On desktop the layout and
control sizes were as before, and the same off-centre click with a mouse opened
nothing, as intended.

The only page error was WebKit reporting `/api/auth/me` "due to access control
checks" when the test navigated in the middle of that request. The app catches
that failure.

The two fixes were checked as follows:

- **Tile labels:** measured with no label cut on the Galaxy S24, iPhone SE (3rd
  gen), iPhone 14 and Pixel 7 sideways (10 px), and on the Pixel 7 and desktop
  (11 px, as before).
- **Place names:** the map tap that had asked for the missing font now loads
  only the basemap's Noto Sans (200, no 404), and the names draw under the pin
  ("Aramghar Crossroads", "Pillar Number 131 · near event").

Web tests (239), type check and lint pass.

WebKit on Windows is not iOS Safari: it draws this site's semibold text lighter
than an iPhone does. Nothing was tried on a physical phone.
