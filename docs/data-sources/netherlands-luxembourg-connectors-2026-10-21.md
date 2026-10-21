# Netherlands and Luxembourg connectors (21 October 2026)

Three official DATEX II v3 feeds, researched on 16 October 2026
(`europe-official-road-sources-2026-10-16.md`), re-verified and connected
on 21 October 2026. The connectors are written but **not registered yet**.
Nothing was written to any database.

| Source id | Feed | Licence | Live dry run, 21 Oct 2026 ≈ 13:35 CEST |
| --- | --- | --- | --- |
| `nl-ndw-actueel-beeld` | NDW current picture, `https://opendata.ndw.nu/actueel_beeld.xml.gz` | CC0 (NDW statement) | 1,224 situations read. 922 skipped as planned works now in force. 24 are not road events. 278 kept: all located, all with a start, 6 with an end. |
| `nl-ndw-planningsfeed-wegwerkzaamheden` | NDW planned roadworks and events, `https://opendata.ndw.nu/planningsfeed_wegwerkzaamheden_en_evenementen.xml.gz` | CC0 (NDW statement) | 14,703 situations read. 672 fall outside the run window. 14,031 kept: 14,030 located, all with a start, 14,004 with start and end. 31 s, process peak 347 MB. |
| `lu-cita-datex2-v36` | CITA, `https://cita.lu/info_trafic/datex/situationrecord36` | CC0 (data.public.lu) | 13 situations read, 13 kept: all located (lines), all with a start, none with an end. |

## Licences, read 21 October 2026

- **NDW.** The open-data portal `https://opendata.ndw.nu/` links its footer
  "Copyright & disclaimer" to `https://www.ndw.nu/copyright`, which redirects
  to `https://www.ndw.nu/service/copyright`. That page says: "Tenzij anders
  vermeld is op de inhoud van deze website de Creative Commons Zero (CC0)
  verklaring van toepassing. Dit houdt in dat hergebruik van de inhoud van
  deze site is toegestaan, tenzij bij een bepaald onderdeel (bijvoorbeeld een
  document) staat aangegeven dat op dat onderdeel een auteursrechtelijke
  beperking van toepassing is." In English: unless stated otherwise, CC0
  applies and reuse is permitted.
  - Two exceptions: images are excluded ("Uitzondering voor beeld"), and
    quoting NDW must not suggest that NDW endorses the derived work.
  - `docs.ndw.nu` links to the same page.
  - No licence written for the situation feeds alone was found, so this
    site-wide statement is the licence.
  - Commercial use: permitted. Attribution: not required. REI credits
    "Bron: NDW" as a courtesy.
- **CITA.**
  - The data.public.lu API for the dataset "Cita : Événements trafic en
    Datex-II v3.6" gives `license: cc-zero`
    (`https://data.public.lu/api/1/datasets/cita-evenements-trafic-en-datex-ii-v3-6/`).
  - The dataset page shows "Creative Commons Zero (CC0)" and links to
    `https://creativecommons.org/publicdomain/zero/1.0/`. Site-wide it says:
    "Sauf indication contraire, tout le contenu de ce site est disponible sous
    Creative Commons CC0."
  - The producer is the Administration des ponts et chaussées.
  - Commercial use: permitted. Attribution: not required.
- **robots.txt.**
  - `opendata.ndw.nu/robots.txt` returns 404, so no rules apply.
  - `www.ndw.nu/robots.txt` and `cita.lu/robots.txt` both say `User-agent: *`
    with no `Disallow`.
  - `data.public.lu/robots.txt` returns 404.
- **Requests made today**, all with the project User-Agent
  `JSAN-REI/1.0 (road event intelligence; RSS reader)`:
  - opendata.ndw.nu: 6
  - www.ndw.nu: 2
  - cita.lu: 3
  - data.public.lu: 3
  - docs.ndw.nu: 1

## How the feeds are read

The shared reader is `backend/connectors/official/datex3_nl_lu.py`.

- **One REI record per DATEX II situation.** A situation's records describe
  one road event: the works, the closure in each direction, the speed limit
  and the diversion.
  - The type comes from the record that says most about the road, in the
    order REI's merge stage uses: closure, bridge, works or event, lane,
    accident, diversion, hazard.
  - Every record's DATEX II type and detail stay in the category words.
- **What is not a road event.** These are not taken:
  - traffic flow (`AbnormalTraffic`);
  - extra capacity (`hardShoulderRunningInOperation`, the rush-hour lane);
  - a road reopened (`roadCleared`).
- **Closures.**
  - A closure is planned when the source says it is works or an event: its
    cause, the situation's works or event records, or the planned feed.
  - It is an emergency closure when the situation reports an accident, an
    obstruction or a fault.
  - Otherwise it keeps its words and gets no type. Example: a carriageway
    closed for "Defecte vrachtwagen" (a broken-down lorry) with no incident
    record.
- **Geometry.**
  - The lines the records draw, with GML `posList` read latitude first.
    Both feeds declare WGS 84 / EPSG:4326. Nothing is projected.
  - A line drawn twice, or once per direction with the same positions in
    reverse order, is kept once.
  - A diversion's route is left out of the event's geometry unless the
    situation is only a diversion. If there are no lines, the first point
    is used.
- **Period.**
  - From the earliest stated start to the latest stated end. There is no end
    if any record states none.
  - Times carry `Z` (NDW) or an offset (CITA). A time without an offset would
    be read in Europe/Amsterdam or Europe/Luxembourg; none was seen.
  - The `validPeriod` sub-periods (for example, the nights the works happen)
    are kept in the stated period, in UTC.
- **Direction.** BOTH_DIRECTIONS only where NDW's own warning says "Weg dicht
  in beide richtingen". CITA's per-direction destinations stay in the title.
- **Current picture versus planned feed.**
  - On 21 October, 945 of the 1,230 current-picture situations were planned
    works now in force. Each record names its planned-feed record in
    `situationRecordCreationReference`: NDW03_…, RWS01_… (the RWS01 copies
    carry a `_WWA` suffix).
  - The current-picture connector leaves these out by default
    (`include_planned_measures=False`), so that one road event is not two.
  - 4 of them named a planned record that the planned feed no longer listed,
    and they are left out too.
- **Contact details.**
  - NDW's planned feed carries contractor and municipal contact lines in its
    comments: names, phone numbers, e-mail addresses. That was about 2,000
    e-mail and 1,000 phone matches on 21 October.
  - Each line holding an e-mail address, a phone number or a contact word
    (contact…, projectleider, telefoon, tel., e-mail, bij calamiteiten) is
    replaced by "[contact details removed by REI]" before anything is kept,
    in the evidence too.
  - A person's name written without any of these (for example, "project van
    <name>") is not caught.
- **Evidence.**
  - Each situation is kept as the fields it states: types, details, times,
    periods, comments, roads, destinations, lines as published, links and
    statuses.
  - ALERT-C location codes and a diversion's own route line are not kept.
    This keeps a planned-feed run to about 350 MB of process memory.
  - `revision_key` ignores `version_time` and `record_versions`.
- **Polling.**
  - Current picture: every 30 minutes.
  - Planned feed: every 180 minutes. It is 16 MB packed and about 215 MB
    unpacked, read as a stream.
  - CITA: every 30 minutes.

## What a reader of the console will see

- **NDW planned feed.** Nearly every event has a start, an end and a line or
  point, so this feed fills the map. It lists about 14,000 events, and a
  first run creates them all.
- **NDW current picture.** Most remaining events are vehicle obstructions,
  accidents and bridge openings with a start and no end. Under REI's display
  rules they stay hidden as unconfirmed.
- **CITA.** No event states an end: the publisher removes an event when it is
  over. All 13 stay hidden as unconfirmed until CITA publishes ends.
- **NDW road names.** Rijkswaterstaat's situations carry no road number, so
  their titles name the district ("RWS Midden-Nederland District Zuid").
  Municipal ones name the street.

## Files

- `backend/connectors/official/datex3_nl_lu.py`: the shared DATEX II v3
  reader.
- `backend/connectors/official/ndw.py`: `ndw_current_source`,
  `NdwCurrentSituationsConnector`, `ndw_planned_source`,
  `NdwPlannedWorksConnector`.
- `backend/connectors/official/cita.py`: `cita_source`,
  `CitaTrafficEventsConnector`.
- `backend/packages/cities/data/netherlands.json` and `luxembourg.json`:
  country entries.
- `backend/tests/unit/test_netherlands_luxembourg.py`: 21 tests.
- Fixtures:
  - `backend/tests/fixtures/ndw_actueel_beeld_2026-10-21.xml`: 26 situations.
  - `backend/tests/fixtures/ndw_planningsfeed_2026-10-21.xml`: 23 situations.
    Its contact lines were replaced by one fictitious line, and one person's
    name and one house number were removed.
  - `backend/tests/fixtures/cita_situationrecord36_2026-10-21.xml`: the whole
    feed, 15 situations.
