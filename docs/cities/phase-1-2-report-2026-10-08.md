# Three Indian city PoCs: Phase 1–2 report (research and source classification)

Date: 8 October 2026. This is the report the brief of 8 October 2026 asks for
in section 25, written at the stop point of section 26: research and
classification are complete; large-scale ingestion has **not** started and
waits for the user's go.

The three research documents it rests on, one per city, each in the brief's
per-source format with the GREEN / YELLOW / BLUE / RED classification:

- [hyderabad-source-research.md](hyderabad-source-research.md) (31 sources today + 10 carried from 2 Oct)
- [mumbai-source-research.md](mumbai-source-research.md) (25 sources)
- [bengaluru-source-research.md](bengaluru-source-research.md) (22 sources)

They were produced by three research runs made with the project's own HTTP
client, one request a second per host, robots.txt honoured, no access control
bypassed, no private API called, nothing installed, nothing connected. The
lead reviewer re-verified the three claims the report leans on most, with
five further requests on 8 October at 17:33 IST: the TGRAC ArcGIS directory
and its road-network layer answer as described (empty `copyrightText`, the
listed fields); the Mumbai Traffic Police date form returns the whole archive
(1,605 rows, "Total :1605") whatever range is asked; the Bengaluru Traffic
Police page served the same events list (39 items by the connector's parser)
and the same four congestion points still stamped 11:45, with the breakdown
items gone. Page 3 of Mumbai notification 209 was read
as an image: it is the English order ("Mogra Nala Bridge on Caesar Road …
until 31/05/2027"), so the bilingual-PDF finding is confirmed.

What was also done on 8 October before this stop, because the brief states
them as rules, not research: the 200 m length filter is withdrawn (64 real
closures restored), official records with no stated end are no longer expired
by age, history is reachable in the console, and source distances are stored
in words and in metres ([decision 0018](../decisions/0018-no-length-filter-no-invented-expiry-history-visible.md)).

## Per-city summary

| | Hyderabad | Mumbai | Bengaluru |
| --- | --- | --- | --- |
| Sources researched | 31 today (+10 from 2 Oct, not re-verified) | 25 | 22 |
| GREEN | 1 (OpenStreetMap data under ODbL, via an extract) | 0 | 0 |
| YELLOW | 5 (Hyderabad City Police press notes; TGRAC road network; TGRAC inundation points; NDMA SACHET; TGDPS rainfall) | 4 (Traffic Police Public Notice List; Mumbai Police press notes; MMRDA; OpenCity) | 1 (BTP website: events list and alerts panel) |
| BLUE (discovery only) | 12 (Telangana Open Data as context; 11 news feeds) | 6 | 6 |
| RED | 13 | 14 | 15 |
| PERMISSION_REQUIRED | 15 | 7 | 7 |
| Production candidates | 1 unconditional (OSM extract); 2 conditional (police press notes if the listing resumes; TGRAC reference layers under written permission). **No official source can be connected for live events today** | 1 (Traffic Police listing: connected, run by hand; YELLOW until the permission question is answered; only partly useful until the PDFs are read) | 1 conditional (BTP website: connected, run by hand; production only after written permission) |
| Discovery sources usable | 6 connected feeds + 5 more (TOI, Indian Express titles, Hyderabad Mail, Telangana Tribune, TV9 Telugu) | 6 (Mumbai Police notes, MMRDA, Mid-Day, Mumbai Live, Lokmat, OpenCity) | 6 (The Hindu connected; TOI, Bangalore Mirror, TV9 Kannada, New Indian Express, Citizen Matters) |
| Real current/upcoming events read in the research | 14 (13 tier 4, 1 with a tier 1 pairing) | 12 current/upcoming (21 real events quoted, 8 tier 1) | 19 (12 tier 1 from the BTP list, 2 two-source) |
| Real events held in REI now (current, per the lifecycle rule) | 26 (60 stored: 11 rejected by reviewers/rules, 1 merged, 22 ended) | 25 (26 stored) | 18 (18 stored) |
| …of which with a map point | 20 (all approximate) | 15 (all approximate) | 8 (all approximate) |
| Recommended first 30 | **Not reachable honestly today**: 26 current in REI, 14 read in research with overlap; see "Recommended events" | **Not reachable**: 25 in REI (10 untyped, 0 dated) + 12 from research; the PDFs hold the rest | **Not reachable**: 18 in REI + the Race Course Road closure and Chandapura from news |

The target of 30 per city is reported as not met, as the brief instructs:
Hyderabad has 26 current events of uneven quality (12 untyped), Mumbai 25
official notices whose English headings give no road or date for most, and
Bengaluru 18. The limitation is the sources, not the pipeline: no Hyderabad
authority publishes events in a readable form; Mumbai's authority does, but
inside scanned PDFs; Bengaluru's authority publishes a works list with dates
but mostly without a place, and its real advisories go to X only.

## The sixteen questions of section 25

1. **Best official source per city.** Hyderabad: none live. The only official
   page that ever carried advisories (Hyderabad City Police press notes, PDF,
   English, born-digital) stopped in December 2025. Mumbai: the Traffic
   Police Public Notice List (every s.115 order since 2009; already
   connected). Bengaluru: the Traffic Police website's "Upcoming Events /
   Press Notes" list (already connected); its "Traffic Alerts" panel is the
   only tier 1 source in the three cities with exact coordinates.
2. **Best road-network source.** OpenStreetMap for all three, taken from an
   extract rather than the public Overpass endpoints (the main instance
   disallows `/api/` for crawlers; two mirrors failed on 8 Oct). TGRAC's
   Telangana road network is official, dated April 2024, coarse, holds no
   GHMC urban street (0 features in the Gachibowli test box against 164 OSM
   ways) and is non-commercial by its disclaimer: a reference for official
   names and classes of NH/SH/MDR/ODR under written permission, not a
   replacement. Karnataka GIS forbids commercial use outright and no road
   layer was found. No Maharashtra road layer was found (data.gov.in is 403
   to automated clients on both days).
3. **Best news/discovery sources.** Hyderabad: Telangana Today (500 items,
   full text) and NewsMeter (highest road-infrastructure density; no terms
   page); TV9 Telugu for Telugu. Mumbai: Mid-Day (full text, Mumbai-only;
   personal use only) and Mumbai Live (full text, infrastructure-heavy, the
   most permissive robots rules seen; terms page not found). Bengaluru: The
   Hindu (connected), Times of India (link-back condition), TV9 Kannada
   (full Kannada text).
4. **Sources with exact coordinates.** Bengaluru Traffic Police alerts
   (lat/lon per congestion point, hour-scale lifetimes). TGRAC's 23 named
   inundation points (reference, permission needed). None in Mumbai.
5. **Sources with road distance.** Mumbai Traffic Police notices (in words:
   72 of 1,605 archive rows, more in the PDFs) and Mumbai Police press notes
   ("५०० मिटर"); news sometimes (Sanjaynagar 2.56 km; Jubilee Hills corridor
   4.3 km; H-CITI 3.3 km; Mehdipatnam skywalk 390 m). Stored verbatim and in
   metres since decision 0018.
6. **Sources with start/end dates.** Bengaluru BTP list (every item); Mumbai
   notices (always in the PDF, in the English column only 12 of 207 rows in
   2026 against 107 of 259 in 2024); news when stated ("8 to 14 October",
   "60 days from October 5").
7. **Sources with source-provided geometry.** None in the three cities
   (London and Toronto remain the only ones). TGRAC provides polylines of the
   network, not of events.
8. **Sources requiring OCR.** Mumbai Traffic Police PDFs: scans, no text
   layer, 200–272 dpi (one at ~70 dpi, likely unreadable); one older order is
   born-digital but in legacy non-Unicode Marathi fonts, which is no easier.
   Mumbai Police press notes: scans, ~200 dpi. The newest notice (209) is
   bilingual, with the full English order on pages 3–4: if that habit holds,
   Latin-script OCR covers the newest orders. Hyderabad: none (police PDFs
   are born-digital English). Bengaluru: none among usable sources.
9. **Sources requiring permission.** Hyderabad: City Police press notes,
   Cyberabad website, TGRAC (both layers), and all 11 news feeds. Mumbai:
   Traffic Police listing, Mumbai Police notes, MMRDA, OpenCity, Mid-Day,
   Mumbai Live, Lokmat. Bengaluru: BTP website, ASTraM, TOI, Bangalore
   Mirror, TV9 Kannada, New Indian Express, Citizen Matters.
10. **Unsuitable for automation (RED).** Hyderabad: HTP website, Cyberabad
    website and Traffic Pulse, Rachakonda (DNS fails), GHMC, HMDA, R&B
    TSROADS, the road-cutting portal (CAPTCHA login), Hindustan Times (empty
    feed), NDTV, News18, Sakshi, Eenadu. Mumbai: BMC portal and disaster
    site, MSRDC, MMRC, data.gov.in, Indian Express, Hindustan Times, Times of
    India, Siasat, Free Press Journal, Loksatta, The Print, News18, NDTV.
    Bengaluru: ASTraM, KSP, BBMP (unreachable two days), GBA (unreachable
    today; the only permissive policy found), data.gov.in, KGIS, KPWD, KRDCL,
    BDA, BMRCL, Indian Express, Deccan Herald, Prajavani, Vijaya Karnataka,
    Udayavani.
11. **Real events collected (in REI, 8 Oct 17:30 IST).** Hyderabad 60 stored,
    26 current; Mumbai 26 stored, 25 current; Bengaluru 18 stored, 18 current.
    Every one has its source record, URL, publication and retrieval time,
    evidence, tier, extraction method and location class.
12. **Duplicates.** 19 "same event?" candidates pending review, 1 merged
    automatically, 5 rejected, 1 superseded (all cities; the pending ones are
    mostly Hyderabad news pairs and Mumbai notice/press-note pairs are not yet
    matched because the press notes are not connected).
13. **Events requiring human location correction.** Hyderabad 48 (33
    approximate, 15 unlocated); Mumbai 26 (16, 10); Bengaluru 18 (8, 10).
    Approximate points are drawn hollow and cannot be approved until placed.
14. **Events with exact source geometry.** 0 in the three cities (London 48,
    Toronto 92).
15. **Events with GIS-resolved geometry.** 0. The GIS Resolution Engine exists
    for Hyderabad (PostGIS, OSM road network of 6 Oct) and proposes junction
    nodes for review; none has been confirmed by a reviewer. Mumbai and
    Bengaluru have no road network imported yet.
16. **Events that cannot currently be located.** Hyderabad 15, Mumbai 10,
    Bengaluru 10.

## Recommended events (real, read on 8 October; none fabricated)

Hyderabad, current or upcoming: Vaishali Nagar underpass diversions 8–14 Oct
(Cyberabad Traffic Police via Telangana Today); Bolarum cantonment roads
closed since 31 Aug (5–8 km detours); KBR Park one-way made permanent
(two-source); H-CITI flyovers and underpass to April–May 2027 (3.3 km);
Mehdipatnam skywalk 390 m with diversions (tier 1 pairing, Dec 2025 PDF);
Paradise–Bowenpally utility shifting; counterflow bus lane trial JNTU–Financial
District (two-source, upcoming); Jubilee Hills–NFCL elevated corridor 4.3 km
(upcoming); Gymkhana–Shamirpet corridor (upcoming); LB Nagar–Hayathnagar
corridor 6 km (proposal). Plus the 26 current events already in REI.

Mumbai, current or upcoming: Caesar Road / Mogra Nala Bridge closed to
31/05/2027 with two alternate routes (tier 1, English PDF); Coastal Road and
Sea Link permanent entry/exit restrictions (tier 1); Belasis ROB southbound
closed (tier 1, end date in a legacy-font PDF); BKC Connector reverse lane
(tier 1); Thane Navratri restrictions 11–20 Oct (tier 4; outside
Brihanmumbai); Yari Road–Lokhandwala flyover works to Dec 2027; Goregaon–Airoli
double-decker bridge 1.6 km; Worli flyover and subway to Jan 2027; 275 roads
of pending concretisation (citywide). Plus the 25 notices already in REI, 10 of
them untyped because their English heading says only "Traffic Arrangement".

Bengaluru, current or upcoming: Race Course Road closed between Maurya and
Hare Krishna Road junctions, 60 days from 5 Oct, with alternate routes
(two-source, attributed to BTP press release and GBA); New Diagonal Road
Jayanagar white-topping to 4 Jan 2027 (tier 1, in REI); 5th Main Chamarajpet
white-topping to 26 Oct (tier 1, in REI); Twin Tunnel soil testing, Hebbal, to
31 Jan 2027 (tier 1); Shivananda Junction works 5–20 Oct (tier 1); Channasandra
night works to 28 Dec (tier 1); Freedom Park gathering 8 Oct (tier 1 + tier 4);
Decathlon Sarjapur Road 10 Oct and NICE Road 11 and 25 Oct early-morning public
events (tier 1); Chandapura NH-44 underpass works and standing water
(three-source); Sanjaynagar Main Road white-topping 2.56 km to end November;
vehicle-class restrictions on four flyovers since 4 Sep; the venue events of
10–31 Oct (tier 1).

## Legal flags for the user (section 2 of the brief)

- **No source in the three cities is GREEN for production.** Every official
  listing that works (Mumbai, Bengaluru) sits under a "permission by e-mail"
  policy, and nobody has written. Until someone does, both stay YELLOW and run
  by hand.
- **The Siasat Daily** (connected for Hyderabad since 2 Oct and for Mumbai
  since 8 Oct) now states in its terms that scrapers, crawlers and AI/LLM use
  are prohibited and that use is "personal, non-commercial". The Mumbai
  research marks it RED; the Hyderabad research marks it BLUE with permission
  required. Every other connected publisher's terms are also personal or
  non-commercial (The Hindu and Deccan Chronicle explicitly forbid scraping;
  NewsMeter has no terms page; Telangana Today's terms could not be read).
  Whether REI's internal discovery use is permitted is a legal question that
  only the user can settle; nothing was disconnected on my own.
- **Mumbai Live** has the most permissive robots rules of any publisher seen
  and no terms page at all: a candidate, but only after asking.
- TGRAC and Karnataka GIS: non-commercial by their own wording.

## What Phase 4 onwards would do, on the user's go

1. **Mumbai archive backfill**: one POST returns all 1,605 notices since
   2009 (507 with a date in the English column). Changes the data's shape;
   the user decides whether history is wanted.
2. **OCR for Mumbai PDFs**: Tesseract is the only option that fits this
   machine (signed installer; EasyOCR and PaddleOCR need pip wheels that are
   broken or blocked here). Installing it is the user's decision; no accuracy
   is known until tried. First test: the 20 newest notices, counting how many
   are bilingual, English-script OCR first, Marathi second. OCR output stays
   extracted evidence needing validation.
3. **Permission e-mails** to Mumbai Traffic Police (listing), the Centre for
   e-Governance / BTP (lists and alerts), and, if the user wants Telugu/Kannada
   discovery, TV9; and the legal decision on the connected publishers.
4. **Bengaluru alerts**: whether to carry the transient congestion points (the
   only exact coordinates available).
5. **Road networks for Mumbai and Bengaluru**: OSM extracts into PostGIS with
   the snapshot date stored (the brief's s.18), then the GIS Resolution Engine
   on both; the Hyderabad engine is in place.
6. **More Hyderabad discovery**: TV9 Telugu and Hyderabad Mail feeds (terms to
   review), and Telugu keyword rules; the Serper searches for Mumbai and
   Bengaluru are defined but not run (credits are the user's cost).
7. Re-test from another network the hosts that were unreachable here (BBMP,
   GBA, Rachakonda police, MSRDC, data.gov.in).

Nothing in this phase approved an event, published anything, replaced a road
network, or deleted evidence.
