# REI web console

Next.js app showing REI events for Hyderabad: event list, filters, statistics,
details with source evidence, human review actions, a source filter and
source health area covering every registered source, and a MapLibre map.

```bash
npm install
npm run dev        # http://localhost:3000 — needs the API running (python backend/run.py)
```

Scripts: `npm test`, `npm run typecheck`, `npm run lint`, `npm run build`.
Optional settings are described in `.env.example`.

## How it gets data

The browser calls same-origin `/api/...`; `next.config.ts` forwards those
requests to the REI API (`API_BASE_URL`, default `http://127.0.0.1:8000`).
Events come only from the API. There is no demo data.

## Structure

```
app/                         Next.js entry (layout, page, global styles)
components/layout/           Shared layout (header)
features/
  dashboard/                 Page composition, source status bar
  events/                    Event model, filters, stats, list, details, API access
  map/                       MapLibre map, legend, basemap toggle, GeoJSON conversion
  qc/                        Human review actions
lib/                         API client, map configuration
types/api.ts                 Wire types of the REI API
```

`features/events/model.ts` is the event model the UI works with;
`features/events/api/eventRepository.ts` is the only place that knows the
API's wire format.

## Map behaviour

- Only events that have geometry are drawn. An event without geometry shows
  "GIS resolution pending" in the list and details; no geometry is made up.
- Solid lines are events in effect; dashed lines are scheduled or unconfirmed.
- The Map / Satellite toggle shows imagery underneath the basemap's labels.

## Notes

- MapLibre GL JS v6 loads its worker as a separate ES module.
  `scripts/copy-maplibre-worker.mjs` copies it into `public/maplibre/` before
  `dev` and `build` (the folder is git-ignored).
- Brand colours are the `brand-*` tokens in `app/globals.css`; `brand-600`
  (#00558c) is the blue of the JSAN logo (`public/jsan-mark.png`).
