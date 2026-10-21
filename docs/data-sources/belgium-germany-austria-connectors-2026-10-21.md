# Belgium (Flanders), Germany (Hamburg) and Austria (Vienna): three connectors, 21 October 2026

Three official sources from the research of 16 October 2026
(`europe-official-road-sources-2026-10-16.md`, sources 3, 9 and 10) are built as
connectors. Each licence was read again today, live, before anything was built.
Nothing is registered or scheduled yet: the registry, `belgium.json` and
`hamburg.json` are left for the user to change (see the last section).

| Source id | Module | Entry | Live, 21 Oct 2026 | Licence | Commercial use |
| --- | --- | --- | --- | --- | --- |
| `flanders-gipod-hindrance` | `connectors/official/gipod.py` | `belgium` | 18,035 motor-traffic zones taken, 18,005 not ended (19 pages) | Modellicentie voor gratis hergebruik v1.0 | yes, with credit |
| `hamburg-roadworks` | `connectors/official/hamburg_roadworks.py` | `hamburg` | 154 works, all kept | Datenlizenz Deutschland – Namensnennung 2.0 | yes, with credit |
| `vienna-roadworks` | `connectors/official/vienna.py` | `vienna` (new, within new `austria`) | 75 works (53 lines, 22 points), all kept | CC BY 4.0 | yes, with credit |

Every kept record has its source's own geometry, a start and an end; every
one lies inside its entry's bbox. No record was written to any database.

## How this was checked

- **User-Agent:** REI's own, `Settings.http_user_agent`
  (`JSAN-REI/1.0 (road event intelligence; RSS reader)`).
- **robots.txt first** on every host, before any other request to it.
- **Requests:** one after another, at least 2 s apart per host during
  development. The GIPOD connector pauses 1 s between pages.
- **Counts per host (development + dry run):**
  - `geo.api.vlaanderen.be`: 8 + 19 = 27. The dry run pages through the whole
    filtered register (19 pages of up to 1,000); it was capped at 30 pages.
  - `api.hamburg.de`: 3 + 1 = 4.
  - `data.wien.gv.at`: 3 + 2 = 5.
  - Terms and metadata hosts: `www.vlaanderen.be` 2, `metadata.vlaanderen.be` 2,
    `digitales.wien.gv.at` 2, `www.data.gv.at` 4, `spdx.org` 2; robots.txt only:
    `www.govdata.de`, `www.dcat-ap.de`, `metaver.de` (one each).
- **Not done:** no logins, keys, CAPTCHAs or proxies. `www.govdata.de` and
  `www.dcat-ap.de` disallow all agents in robots.txt, so neither was read
  further. `metaver.de` answered robots.txt with HTTP 429 and was not asked
  again.
- **Request log:** outside the repo, in the session scratchpad (`beat\log.tsv`).

## 1. GIPOD planned mobility hindrance, Flanders (`flanders-gipod-hindrance`)

Publisher and custodian: Athumi (Vlaams Datanutsbedrijf). Distributor:
agentschap Digitaal Vlaanderen. Both roles are from the metadata record.

- **Request:** `GET https://geo.api.vlaanderen.be/GIPOD/ogc/features/v1/collections/HINDER/items`
  with `f=application/geo+json`, `limit=1000`,
  `crs=http://www.opengis.net/def/crs/OGC/1.3/CRS84` and a CQL filter. The
  connector then follows the API's `next` links (`startIndex`), on its own host
  only; they keep the filter and the CRS.
  - The metadata record names the `/v1/` path. The research's path without
    `/v1/` was not used.
- **robots.txt:** HTTP 404, so no rules apply.
- **Filter (server side, the register's own words):** `Consequences` contains
  "gemotoriseerd verkeer", "Afgesloten", "rijstroken", "Wisselend verkeer",
  "Snelheidsbeperking", "Rijrichting" or "tweerichtingsverkeer".
  - About half of all zones are parking bans or footway and cycle-path
    restrictions only, and are not asked for.
  - The WFS still caps the count at 10,000. Zones with these consequences
    that start on or after 21 November 2026: 1,495.
- **Live, 21 October 2026:** 19 requests, 79 s.
  - 18,035 zones taken; 30 already ended (dropped from the run); 18,005 kept.
    Of these, 11,499 are current and 6,506 upcoming.
  - Lane restriction 13,993; planned road closure 3,892; no type (speed limit,
    reversed direction, two-way traffic) 120.
  - All have a MultiPolygon, a start and an end.
- **Types, from the stated consequences:**
  - "Geen doorgang voor gemotoriseerd verkeer" (with or without "uitgezonderd
    …") and "Afgesloten in 1 rijrichting" make a planned road closure. The
    words are kept, so a one-direction closure reads as one.
  - "Vermindering van rijstroken", "Versmalde rijstroken" and "Wisselend
    verkeer via verkeersborden/verkeerslichten" make a lane restriction.
  - Anything else on motor traffic keeps its words with no type.
- **Times:** `HindranceStart` and `HindranceEnd`, ISO 8601 in UTC with `Z`.
  They are read as written.
- **Other fields:**
  - Severity: "Severe hindrance" when `SevereHindrance` is true, otherwise
    none.
  - Status: `HindranceStatus` ("Gevalideerd").
- **Ids:** the feature id `HINDER.<ZoneId>-<start yymmddHHMM>`. One zone can
  have several periods.
  - 671 of 672 zones seen on both 16 and 21 October kept their id.
  - A moved start gives a new id.
  - A new `HindranceLastModifiedOn` alone is not a revision.
- **Place:** the layer has no street field. When a description begins
  "<postcode> <municipality>, <street>:", that place is the location and the
  title (about 20% of zones). Otherwise the title is
  "GIPOD hindrance <id> (<owner>)" and no place is invented.
- **Personal data:**
  - `HindranceContactOrganisations` holds contact names, e-mail addresses and
    telephone numbers. It is dropped as each page is read and never stored.
  - `HindranceDescription` is free text. In the 1,000 zones looked at, one
    began with a person's name. Descriptions are kept as published (summary
    only, never the title).
- **Licence, read 21 October 2026:**
  - The metadata record `2b4b3bb7-cadc-41a0-b5ae-796a84a20b52`
    (<https://metadata.vlaanderen.be/srv/api/records/2b4b3bb7-cadc-41a0-b5ae-796a84a20b52/formatters/xml>)
    covers this OGC API, `HINDER` included. Its `otherConstraints` name the
    "Modellicentie voor gratis hergebruik"
    (<https://data.vlaanderen.be/id/licentie/modellicentie-gratis-hergebruik/v1.0>).
  - Licence page:
    <https://www.vlaanderen.be/digitaal-vlaanderen/onze-diensten-en-platformen/open-data/voorwaarden-voor-het-hergebruik-van-overheidsinformatie/modellicentie-gratis-hergebruik>
    ("Dit is versie 1.0 van de modellicentie voor gratis hergebruik").
  - Art. 3: "De licentienemer krijgt het niet-exclusieve en wereldwijde recht
    om het product te hergebruiken voor elk rechtmatig doeleinde, met inbegrip
    van het reproduceren, doorgeven, publiceren, aanpassen en commercieel
    exploiteren van het product."
  - Art. 4 asks for three things:
    - credit "zoals wordt gespecificeerd door de licentiegever" (as the
      licensor specifies), or else the licensor's name;
    - never suggesting that REI acts for the licensor or has "enige officiële
      status of goedkeuring";
    - respect for personal-data law.
  - Art. 6: free of charge.
  - REI's credit: "GIPOD: Athumi (Vlaams Datanutsbedrijf), distributed by
    Digitaal Vlaanderen; Modellicentie voor gratis hergebruik v1.0 (link)".
- **Polling:** every 8 hours (three times a day). The register looks six
  months ahead and its metadata says it is updated continually.
- **Volume and memory (for the user's decision):**
  - About 18,000 records a run, roughly 2.3 MB per page, about 45 MB per run.
  - Read locally, 1,000 records took roughly 15–40 MB of Python memory. A full
    run therefore holds a few hundred MB, plus the held versions the pipeline
    loads to compare.
  - The first run creates about 18,000 events.
  - If that is too much, the filter can be narrowed on the server, for example
    to `SevereHindrance = true` or to closures only. That would be a product
    decision; it is not built.
- **Fixture:** `backend/tests/fixtures/gipod_hindrance_2026-10-21.geojson`.
  It holds 22 real zones (18 taken, 4 not taken), with
  `HindranceContactOrganisations` removed and one zone whose description names
  a person left out.

## 2. Hamburg roadworks, Bauweiser (`hamburg-roadworks`)

Freie und Hansestadt Hamburg, Behörde für Verkehr und Mobilitätswende. The
profiles are written by the bodies carrying out the works.

- **Request:** `GET https://api.hamburg.de/datasets/v1/baustellen/collections/baustelle/items?f=json&limit=10000&crs=http://www.opengis.net/def/crs/OGC/1.3/CRS84`.
  - One request; `numberMatched` 154.
  - A list longer than one page is refused.
- **robots.txt:** only `User-agent: spatineo` is disallowed.
- **Live, 21 October 2026:**
  - 154 works (the research counted 161 on 16 October), all points, all with
    both days. 144 are current and 10 upcoming.
  - All 154 ids seen on 16 October were unchanged.
- **Reading:**
  - Every profile is road works.
  - `baubeginn` and `bauende` (dd.mm.yyyy) are whole Hamburg days
    (Europe/Berlin): from 00:00 on the first day to 23:59:59 on the last.
  - `isthotspot` adds "Hotspot" to the category.
  - The summary is `anlass`, `umfang` (the closures, in German), the detour
    and `organisation`.
  - No road is inferred from `titel`.
  - A new `letzteaktualisierung` alone is not a revision.
- **Personal data:** none found. There are no contact fields, and no e-mail
  address or telephone number appears in any text.
- **Licence, read 21 October 2026:**
  - The dataset's own API document
    (<https://api.hamburg.de/datasets/v1/baustellen?f=json>) gives
    `"rel": "license"`, title "Datenlizenz Deutschland Namensnennung 2.0",
    href <https://www.govdata.de/dl-de/by-2-0>. Its `attribution` is "Freie und
    Hansestadt Hamburg, Behörde für Verkehr und Mobilitätswende".
  - The licence page on govdata.de was **not** read: its robots.txt says
    `User-agent: * / Disallow: /`.
  - The text was read instead from the SPDX licence list,
    <https://spdx.org/licenses/DL-DE-BY-2.0.html> (no robots.txt, HTTP 404).
    § 1: "Die bereitgestellten Daten und Metadaten dürfen für die kommerzielle
    und nicht kommerzielle Nutzung insbesondere 1. vervielfältigt, ausgedruckt,
    präsentiert, verändert, bearbeitet sowie an Dritte übermittelt werden; 2.
    mit eigenen Daten und Daten Anderer zusammengeführt und zu selbständigen
    neuen Datensätzen verbunden werden; 3. in interne und externe
    Geschäftsprozesse, Produkte und Anwendungen in öffentlichen und nicht
    öffentlichen elektronischen Netzwerken eingebunden werden."
  - § 2 asks for a source note with three parts: the provider's name, the
    licence name or "dl-de/by-2-0" with a link to its text, and a reference
    to the dataset (URI).
  - § 3: changed data must be marked as changed.
  - REI's credit covers all four: "Freie und Hansestadt Hamburg, Behörde für
    Verkehr und Mobilitätswende; Datenlizenz Deutschland – Namensnennung –
    Version 2.0 (www.govdata.de/dl-de/by-2-0);
    https://api.hamburg.de/datasets/v1/baustellen; data changed (read into REI
    events)".
- **Polling:** every 3 hours.
- **Fixture:** `backend/tests/fixtures/hamburg_roadworks_2026-10-21.geojson`.
  It holds 12 real works; `numberMatched` and `numberReturned` are set to 12.

## 3. Vienna roadworks affecting traffic (`vienna-roadworks`)

Stadt Wien. One source reads two layers.

- **Requests:** `GET https://data.wien.gv.at/daten/geo?service=WFS&request=GetFeature&version=1.1.0&typeName=ogdwien:BAUSTELLENLINOGD&srsName=EPSG:4326&outputFormat=json`,
  then the same with `ogdwien:BAUSTELLENPKTOGD`.
  - The GeoJSON is written longitude first (16.3, 48.2), although it names
    `urn:ogc:def:crs:EPSG::4326`.
  - The connector refuses a response written latitude first, and a layer
    whose `numberMatched` is larger than what it returned.
- **robots.txt:** HTTP 404 on `data.wien.gv.at`. `digitales.wien.gv.at`
  disallows calendar paths only.
- **Live, 21 October 2026:** 53 lines and 22 points (the research counted 53
  and 25). All have both days; 74 are current and 1 upcoming.
- **Ids:**
  - The source renumbers its feature ids and `OBJECTID` at each reload: all 75
    changed between 16 and 21 October.
  - REI's id is the layer plus a hash of the stated district, `BEZEICHNUNG`,
    `BEHINDERUNGSART`, `OBJEKT_BEGINN` and the geometry. All 74 records
    present on both days (52 lines, 22 points) kept that id.
  - A changed end or press text is a revision of the same record; a redrawn
    geometry is a new record.
  - Two works are drawn as several sections with the same name and first day;
    each section is its own record.
- **Reading:**
  - `BEHINDERUNGSART` values with "bau", "arbeiten" or "Rohrlegung" are road
    works (all 75 today); any other kind keeps its words with no type.
  - `OBJEKT_BEGINN` and `OBJEKT_ENDE` ("2026-10-15Z") are whole Vienna days
    (Europe/Vienna).
  - The place and affected road are `BEZEICHNUNG` as written. The summary is
    the kind of works, `PRESSETEXT` and `ANTRAGSTELLER`.
  - Each record links to its layer's data.gv.at entry, because the source has
    no stable item address.
- **Personal data:** `ANSPRECHPERSON` and `ANSPRECHPERSON_TEL` are dropped
  on reading and never stored. About half of the contacts look like named
  people (the rest "Kundenzentrum" or similar), and 74 of 75 records carry a
  telephone number. `ANTRAGSTELLER` holds organisations only (MA28, Wiener Linien,
  "Privater Bauträger" …).
- **Licence, read 21 October 2026.** The caveat in the research is resolved:
  - The terms page <https://digitales.wien.gv.at/ogd-nutzungsbedingungen/>:
    - "Open Government Data der Stadt Wien stehen unter einer „Creative Commons
      Namensnennung 4.0 Lizenz" (CC BY 4.0). LizenznehmerInnen dürfen die Daten
      unter Beachtung folgenden Bedingungen vervielfältigen, verbreiten,
      öffentlich zugänglich machen, kommerziell nutzen, sowie Abwandlungen und
      Bearbeitungen des Werkes bzw. des Inhalts anfertigen."
    - Credit: "Datenquelle: Stadt Wien – data.wien.gv.at".
    - The same page says "In bestimmten Fällen stehen Datensätze unter einer
      „CreativeCommons Namensnennung – Nicht kommerziell 4.0 Lizenz"".
  - The dataset-level licence was therefore checked in the national catalogue
    (`https://www.data.gv.at/api/hub/search/search?q=Baustellen%20Wien&filter=dataset`).
    Both entries list `https://creativecommons.org/licenses/by/4.0/deed.de` on
    every one of their 21 distributions, the WFS and GeoJSON ones included:
    - "Verkehrswirksame Baustellen Linien Wien",
      <https://www.data.gv.at/katalog/datasets/3df7a50f-108d-40bc-a041-e3092fc50a81>
      (updated weekly);
    - "Verkehrswirksame Baustellen Standorte Wien",
      <https://www.data.gv.at/katalog/datasets/88e7ff53-257d-4299-99b5-c659b87b5116>
      (updated daily).

    Neither is CC BY-NC.
  - The terms also forbid uses that support criminal, discriminatory and
    similar activities, and ask users to tell the city where they use the
    data.
- **Polling:** every 3 hours (two requests).
- **Fixture:** `backend/tests/fixtures/vienna_roadworks_2026-10-21.json`.
  - It holds both layers' responses, keyed by layer: 12 lines (the two
    multi-section works among them) and 6 points.
  - `ANSPRECHPERSON` and `ANSPRECHPERSON_TEL` are removed, and the counts are
    set to match.
- **New entries:**
  - `austria.json`: country entry, AT, Europe/Vienna, bbox 46.37–49.02 N,
    9.53–17.17 E.
  - `vienna.json`: city within it, bbox 48.10–48.34 N, 16.17–16.59 E. It
    already lists `vienna-roadworks`.

## Tests

`backend/tests/unit/test_gipod_hamburg_roadworks_vienna.py`: 35 tests, all
passing. No test reaches any service. They check:

- definitions and column limits;
- the Austria/Vienna configuration;
- GIPOD's consequence-to-type reading, its paging, page cap, host check and
  axis-order check;
- that contact people are dropped;
- whole-day periods in Berlin and Vienna;
- Vienna's stable ids under renumbering;
- revision keys that ignore bookkeeping fields;
- the full pipeline for all three sources: events located by the source, every
  stored value within its column, and a renumbered Vienna reload adding and
  revising nothing.

## What the user needs to change (not done here)

`connectors/registry.py`, imports:

```python
from .official.gipod import GipodHindranceConnector, gipod_source
from .official.hamburg_roadworks import HamburgRoadworksConnector, hamburg_roadworks_source
from .official.vienna import ViennaRoadworksConnector, vienna_source
```

In `_official_sources`, inside the `feature_feeds` tuple, after the Hamburg police line:

```python
            # Flanders, Hamburg roadworks and Vienna (21 October 2026).
            (gipod_source, GipodHindranceConnector),
            (hamburg_roadworks_source, HamburgRoadworksConnector),
            (vienna_source, ViennaRoadworksConnector),
```

City files:

- `backend/packages/cities/data/belgium.json`: `"official_sources": ["flanders-gipod-hindrance"]`.
- `backend/packages/cities/data/hamburg.json`: add `"hamburg-roadworks"` after
  `"hamburg-police-traffic-messages"`.
- `vienna.json` already lists `vienna-roadworks`.

## Not built

- Verkeerscentrum Vlaanderen DATEX II (research source 8): not asked for. Its
  lines are in Belgian Lambert 72, which would need reprojection, and REI adds
  no projection library.
- GIPOD's other collections (`OMLEIDING` diversions, `INNAME` occupations,
  `*_PUNT` points): not asked for.
