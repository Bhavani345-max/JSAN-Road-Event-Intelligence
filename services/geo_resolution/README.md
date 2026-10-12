# Location by named place

Locates an event by a Hyderabad place its article names:

```
article text → known place names (gazetteer) → position of that OpenStreetMap feature
```

- `data/hyderabad_places.json` — the gazetteer: named junctions, flyovers and
  underpasses, landmarks (stations, hospitals, colleges, places of worship,
  markets, malls, parks, lakes, the airport), short roads, localities and
  wards of Greater Hyderabad, each with its OpenStreetMap id.
  © OpenStreetMap contributors, ODbL.
- `build_gazetteer.py` — rebuilds that file from the Overpass API:
  `python -m services.geo_resolution.build_gazetteer`. The application itself
  never calls OpenStreetMap.
- `resolver.py` — finds the places a text names. `names.py` makes spellings
  meet ("Khajaguda Jn" = "Khajaguda junction", "Dilsukhnagar" = "Dilsukh
  Nagar"). `KNOWN_AS` in the resolver lists the few names the papers use for
  a feature OpenStreetMap names differently ("Tank Bund" is Tank Bund Road).
- `spot_within` — when the headline names a locality and the headline or
  summary also names a junction, flyover or landmark within 2.5 km of it, the
  event is put at that spot, with the locality kept as `within`.

The result is the position of the *named place*, recorded with the event as
`detection.location`. It is not a match to the road network and not the extent
of a closure: that still needs a road-network engine (PostGIS), for which the
`events.geom` column is in place.

A name that does not point to one spot is left out of the gazetteer (long
roads, names shared by distant localities), and an article that names no known
place in its headline or summary is not located. See
[decision 0006](../../docs/decisions/0006-named-place-location-and-stated-dates.md).
