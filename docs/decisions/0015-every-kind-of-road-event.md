# 0015 — Every kind of road event the user listed

Date: 2026-10-07. Status: accepted.

## Context

The user listed the kinds of event REI must cover: marathons, parades,
sporting events, road construction, temporary road closures, lane
restrictions, police diversions, flooding, emergency closures, public events,
VIP movements, temporary turn restrictions, bridge/tunnel restrictions,
weather-related closures and other short-duration road-network changes.

Before this change the news rules detected most of them only through general
wording ("traffic restrictions"), gave several no type (marathon, VIP, sport,
lane, turn, bridge, emergency, weather), and missed some wordings entirely
(turn closures, lane closures, "traffic police issue advisory").

## Decision

- **Five new event types**: MARATHON, SPORTING_EVENT, VIP_MOVEMENT,
  TURN_RESTRICTION, WEATHER_CLOSURE. Console labels: PUBLIC_PROCESSION is
  "Procession / Parade", SPECIAL_EVENT is "Public Event".
- **New strong signals** (a measure on the road), each typed: lane closed,
  turn closed (U-turn, free left, "no right turn"), flyover/bridge/underpass/
  tunnel closed, road flooded, closed after an accident/collapse/burst, and
  "traffic police … advisory".
- **Words that name the event** (marathon, run, parade, procession, IPL,
  match, stadium, VIP visit, convoy, festival, Numaish, Bathukamma, after an
  accident, tree fall, waterlogging) carry a `names_event` flag: their type
  wins over the measure's ("diversions for the marathon" is a marathon).
  They never make a story a road event alone: the strong-signal and
  named-place rules are unchanged, so "Marathon registrations open" or
  "Sunrisers win at Uppal" stay out.
- **Kept**: a plain "road closure" still states no type (planned or
  emergency is not said); works with a diversion are still a diversion.
- **Search**: the 12 Google News searches were widened (marathon, IPL,
  match, stadium, parade, celebrations, convoy, U-turn, lane closed) without
  adding searches: still 36 Serper credits a day.
- Pitfalls found while testing and excluded: "storm water drain" and "storm
  drain" are not storms; "to prevent accidents" is not an accident.

## Result on 7 October 2026

Re-applied to the 1,512 stored articles: no new events (the past five days'
papers had no missed stories of these kinds), 15 events re-typed — e.g. PM
Modi's visit restrictions → VIP Movement, heavy rain → Weather Closure,
Ganesh immersion closures → Procession / Parade. Backup:
`apps/api/.data/backups/rei-2026-10-07-before-all-event-types.db`.

Official feeds (TfL, Toronto) keep their own category mapping.
