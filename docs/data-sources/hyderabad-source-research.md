# Hyderabad source research

Research date: **2 October 2026**. Every finding below comes from a check made
on that date: the site or feed was fetched, or the provider's documentation was
read. Where something could not be established, it says so. Nothing here is
assumed.

"Machine-readable access" means REI could obtain the content with a program
without scraping pages meant for people.

The same sources are recorded in the source registry
(`connectors/registry.py`, `connectors/discovered.py`) and are returned by
`GET /api/sources`.

## Summary

| Source | Authority level | Machine-readable | Status |
| --- | --- | --- | --- |
| Telangana Today | Tier 4 (news) | RSS | CONNECTED |
| The Hindu | Tier 4 (news) | RSS | CONNECTED |
| Deccan Chronicle | Tier 4 (news) | RSS | CONNECTED |
| The Siasat Daily | Tier 4 (news) | RSS | CONNECTED |
| NewsMeter | Tier 4 (news) | RSS | CONNECTED |
| The Hans India | Tier 4 (news) | RSS | CONNECTED until 14 Oct 2026; removed (decision 0026) |
| The Times of India (Hyderabad) | Tier 4 (news) | RSS | DISCOVERED |
| Hyderabad Mail | Tier 4 (news) | RSS | DISCOVERED |
| Telangana Tribune | Tier 4 (news) | RSS | DISCOVERED |
| Hyderabad Traffic Police | Tier 1 | None found | MANUAL ONLY |
| Hyderabad City Police press notes | Tier 1 | None (PDF notices) | DISCOVERED |
| Cyberabad Police | Tier 1 | None found | MANUAL ONLY |
| Cyberabad Traffic Pulse | Tier 1 | None | MANUAL ONLY |
| Rachakonda Police | Tier 1 | Could not be checked | NOT USABLE |
| GHMC | Tier 1 | None found | MANUAL ONLY |
| HYDRAA | Tier 1 | None found | MANUAL ONLY |
| TGDPS live rainfall | Tier 1 | HTML table only | DISCOVERED |
| Open Data Telangana | Tier 1 | Dataset downloads | DISCOVERED |
| NDMA SACHET alerts (Telangana) | Tier 1 | RSS (CAP) | DISCOVERED |
| IMD Meteorological Centre Hyderabad | Tier 1 | None (PDF bulletins) | DISCOVERED |
| NHAI | Tier 1 | None found | MANUAL ONLY |
| HMDA | Tier 1 | None (HTML notices) | DISCOVERED |
| TGSRTC | Tier 2 | None found | MANUAL ONLY |
| Hyderabad Metro Rail | Tier 2 | RSS (corporate news) | NOT USABLE |
| Rajiv Gandhi International Airport | Tier 2 | None found | MANUAL ONLY |
| TomTom Traffic Incidents API | Not assigned | API | REQUIRES ACCESS |
| HERE Traffic API | Not assigned | API | REQUIRES ACCESS |
| Mappls (MapmyIndia) | Not assigned | Commercial API | REQUIRES ACCESS |
| Waze for Cities | Not assigned | Partner feed | NOT USABLE |

**The main finding:** no government, police or road authority in Hyderabad
publishes road closures or traffic advisories in a machine-readable form.
They publish on X, Facebook and WhatsApp, for people to read. The only
machine-readable sources of Hyderabad road-event information found are news
feeds, which report those advisories second-hand, and commercial traffic APIs.

## Tiers

REI's tier definitions: 1 government, police or road authority; 2 official
event organiser or transport operator; 3 approved commercial or partner source;
4 discovery-only.

- News publishers are none of the first three, so they are **tier 4**. Their
  reports are leads for human validation.
- Commercial providers are given **no tier**: tier 3 means an *approved*
  source, and none has been approved.

---

# A. Connected sources

All six are read by the same generic RSS connector. Terms of use have **not**
been formally reviewed for any of them; see "Licensing" at the end.

## Source: Telangana Today

- **Organization:** Telangana Today
- **Authority level:** Tier 4 — news media
- **Category:** News
- **Source URL:** https://telanganatoday.com/hyderabad
- **Machine-readable access:** https://telanganatoday.com/hyderabad/feed
- **RSS:** YES · **API:** NO · **HTML:** YES · **PDF:** NO · **Social/public notices:** not checked
- **Hyderabad relevance:** High. The publisher's Hyderabad section; every item is tagged Hyderabad.
- **Data provided:** Title, link, publication time, author, tags, summary, full article body.
- **Update frequency:** The feed declares hourly updates. It holds about 500 items, roughly two weeks.
- **Access requirements:** None.
- **Licensing/terms notes:** Not reviewed.
- **Integration status:** CONNECTED
- **Reason:** Reachable, Hyderabad-specific, and regularly reports diversions, restrictions, processions and waterlogging.

## Source: The Hindu

- **Organization:** The Hindu
- **Authority level:** Tier 4 — news media
- **Category:** News
- **Source URL:** https://www.thehindu.com/news/cities/Hyderabad/
- **Machine-readable access:** https://www.thehindu.com/news/cities/Hyderabad/feeder/default.rss
- **RSS:** YES · **API:** NO · **HTML:** YES · **PDF:** NO · **Social/public notices:** not checked
- **Hyderabad relevance:** Medium. It is the Hyderabad city feed, but 42 of 60 items were tagged Telangana and were statewide.
- **Data provided:** Title, link, publication time, one tag. Most items have no summary; none has a body.
- **Update frequency:** About 60 items covering roughly two days.
- **Access requirements:** None.
- **Licensing/terms notes:** Not reviewed.
- **Integration status:** CONNECTED
- **Reason:** Reachable and reputable. Detection rests on the headline alone, so it will find fewer events than the others.

## Source: Deccan Chronicle

- **Organization:** Deccan Chronicle
- **Authority level:** Tier 4 — news media
- **Category:** News
- **Source URL:** https://www.deccanchronicle.com/southern-states/telangana
- **Machine-readable access:** https://www.deccanchronicle.com/category/southern-states/telangana/google_feeds.xml
- **RSS:** YES · **API:** NO · **HTML:** YES · **PDF:** NO · **Social/public notices:** not checked
- **Hyderabad relevance:** Medium. A Telangana-wide feed; no usable Hyderabad-only feed exists (the `/category/hyderabad/` feed held seven items from July 2026). The city is given only in the article's opening dateline, which the scope check reads.
- **Data provided:** Title, link, publication time, author, section tags, summary, full article body.
- **Update frequency:** About 60 items covering under a day.
- **Access requirements:** None.
- **Licensing/terms notes:** Not reviewed.
- **Integration status:** CONNECTED
- **Reason:** Reachable; it reported the DLF / IIIT Junction closure in June 2026.

## Source: The Siasat Daily

- **Organization:** The Siasat Daily
- **Authority level:** Tier 4 — news media
- **Category:** News
- **Source URL:** https://www.siasat.com/news/hyderabad/
- **Machine-readable access:** https://www.siasat.com/news/hyderabad/feed/
- **RSS:** YES · **API:** NO · **HTML:** YES · **PDF:** NO · **Social/public notices:** not checked
- **Hyderabad relevance:** High. The Hyderabad section; all 40 items were tagged Hyderabad.
- **Data provided:** Title, link, publication time, author, tags, summary, full article body.
- **Update frequency:** About 40 items covering roughly 30 hours.
- **Access requirements:** None. Its robots.txt blocks a list of named AI crawlers; it does not block feed readers.
- **Licensing/terms notes:** No terms page was found at the usual addresses. Not reviewed.
- **Integration status:** CONNECTED
- **Reason:** Reachable and Hyderabad-specific. It reported the IIIT Junction diversions in June 2026.

## Source: NewsMeter

- **Organization:** NewsMeter
- **Authority level:** Tier 4 — news media
- **Category:** News
- **Source URL:** https://newsmeter.in/hyderabad
- **Machine-readable access:** https://newsmeter.in/category/hyderabad/google_feeds.xml (declared by the section page)
- **RSS:** YES · **API:** NO · **HTML:** YES · **PDF:** NO · **Social/public notices:** not checked
- **Hyderabad relevance:** High. All 60 items were tagged Hyderabad.
- **Data provided:** Title, link, publication time, author, tags, summary, full article body.
- **Update frequency:** About 60 items covering roughly ten days.
- **Access requirements:** None.
- **Licensing/terms notes:** No terms page was found at the usual addresses. Not reviewed.
- **Integration status:** CONNECTED
- **Reason:** Reachable and Hyderabad-specific, with the highest density of traffic wording of any feed checked. It reported the IIIT Junction closure in June 2026.

## Source: The Hans India

- **Organization:** The Hans India
- **Authority level:** Tier 4 — news media
- **Category:** News
- **Source URL:** https://www.thehansindia.com/news/cities/hyderabad
- **Machine-readable access:** https://www.thehansindia.com/category/news/cities/hyderabad/google_feeds.xml (declared by the section page)
- **RSS:** YES · **API:** NO · **HTML:** YES · **PDF:** NO · **Social/public notices:** not checked
- **Hyderabad relevance:** High. All 29 items were tagged Hyderabad.
- **Data provided:** Title, link, publication time, author, tags, summary, full article body.
- **Update frequency:** About 30 items covering under three hours. Polled every 15 minutes for that reason.
- **Access requirements:** None.
- **Licensing/terms notes:** No terms page was found at the usual addresses. Not reviewed. **Correction, 14 October 2026:** the terms are at https://www.thehansindia.com/pages/terms-conditions (found by the research of 8 October, `docs/cities/hyderabad-source-research.md`; read again 14 October): "HMHL grants you a limited license to access and make personal use of this site but not for commercial purposes. We permit the use of materials on this website subject to due credit is given to HMHL."
- **Integration status:** CONNECTED until 14 October 2026, when the user removed it from REI; registered without a connector since ([decision 0026](../decisions/0026-hans-india-removed.md)).
- **Reason:** Reachable and Hyderabad-specific. The very short feed window means articles published while REI is not running are lost.
- **Production (Railway), 14 October 2026:** the feed is behind Cloudflare, which answers HTTP 403 to Railway's servers. Every deployment since 12 October was refused (about 400 polls), except one on 14 October, 10:01-12:33 UTC, which got through 11 times out of 11; from an office connection the same request gets 200. Cloudflare judges the network address a request comes from, and Railway's address changes between deployments. robots.txt allows the feed, so this is the site's bot protection, not a ban on REI. It is not worked around (no browser disguise, no proxies). Since 14 October a refusal is reported as Cloudflare's (`connectors/base.py`, `refusal_detail`).

---

# B. News feeds found but not connected

## Source: The Times of India (Hyderabad)

- **Organization:** The Times of India
- **Authority level:** Tier 4 — news media
- **Category:** News
- **Source URL:** https://timesofindia.indiatimes.com/city/hyderabad
- **Machine-readable access:** https://timesofindia.indiatimes.com/rssfeeds/-2128816011.cms
- **RSS:** YES · **API:** NO · **HTML:** YES · **PDF:** NO · **Social/public notices:** not checked
- **Hyderabad relevance:** High in content, but not expressed in the feed.
- **Data provided:** Title, link, publication time. No tags, no body; 13 of 20 items had no summary.
- **Update frequency:** 20 items covering under a day.
- **Access requirements:** None.
- **Licensing/terms notes:** Could not be confirmed; the RSS page did not yield readable terms.
- **Integration status:** DISCOVERED
- **Reason:** With no tags and no body, the current rules can place an article in Hyderabad only if its headline names the city, so most articles would be dropped. Connecting it usefully needs a decision on trusting the feed's own section, and its terms need checking first.

## Source: Hyderabad Mail

- **Organization:** Hyderabad Mail
- **Authority level:** Tier 4 — news media
- **Category:** News
- **Source URL:** https://hyderabadmail.com/
- **Machine-readable access:** https://hyderabadmail.com/feed/
- **RSS:** YES · **API:** NO · **HTML:** YES · **PDF:** NO · **Social/public notices:** not checked
- **Hyderabad relevance:** High; it has reported Hyderabad traffic advisories.
- **Data provided:** Title, link, publication time, tags, summary. No body.
- **Update frequency:** 10 items covering under a day.
- **Access requirements:** None.
- **Licensing/terms notes:** Not reviewed.
- **Integration status:** DISCOVERED
- **Reason:** The feed works, but the reliability of the publication has not been assessed.

## Source: Telangana Tribune

- **Organization:** Telangana Tribune
- **Authority level:** Tier 4 — news media
- **Category:** News
- **Source URL:** https://www.telanganatribune.com/
- **Machine-readable access:** https://www.telanganatribune.com/feed/
- **RSS:** YES · **API:** NO · **HTML:** YES · **PDF:** NO · **Social/public notices:** not checked
- **Hyderabad relevance:** High.
- **Data provided:** Title, link, publication time, tags, summary. No body.
- **Update frequency:** 10 items covering about two days.
- **Access requirements:** None.
- **Licensing/terms notes:** Not reviewed.
- **Integration status:** DISCOVERED
- **Reason:** The feed works, but the reliability of the publication has not been assessed.

---

# C. Police and traffic authorities

## Source: Hyderabad Traffic Police

- **Organization:** Hyderabad City Police
- **Authority level:** Tier 1 — police
- **Category:** Traffic authority
- **Source URL:** https://www.htp.gov.in/
- **Machine-readable access:** NO PUBLIC MACHINE-READABLE SOURCE FOUND
- **RSS:** NO · **API:** NO · **HTML:** NO (no advisory listing) · **PDF:** NO · **Social/public notices:** YES (Facebook, X, Instagram, WhatsApp channel)
- **Hyderabad relevance:** Highest: the issuing authority for advisories, diversions and restrictions in Hyderabad city.
- **Data provided:** On the website: static information. Its "Traffic Updates" link goes to the Facebook page.
- **Update frequency:** Not established for the social channels.
- **Access requirements:** Reading the social posts by program would need the platforms' own APIs, which were not evaluated here.
- **Licensing/terms notes:** Not reviewed.
- **Integration status:** MANUAL ONLY
- **Reason:** Official source — manual/public notice only.

## Source: Hyderabad City Police press notes

- **Organization:** Hyderabad City Police
- **Authority level:** Tier 1 — police
- **Category:** Police
- **Source URL:** https://www.hyderabadpolice.gov.in/
- **Machine-readable access:** NO PUBLIC MACHINE-READABLE SOURCE FOUND
- **RSS:** NO · **API:** NO · **HTML:** YES (list of press notes) · **PDF:** YES · **Social/public notices:** YES (X, Facebook, WhatsApp)
- **Hyderabad relevance:** High. The press notes include traffic diversion notices.
- **Data provided:** Press notes as PDF files linked from the home page.
- **Update frequency:** The newest note listed was dated December 2025, so the listing appeared not to be kept current.
- **Access requirements:** None to read; would need a PDF connector.
- **Licensing/terms notes:** Not reviewed.
- **Integration status:** DISCOVERED
- **Reason:** Not connected: there is no feed, and a listing ten months out of date would not deliver current advisories.

## Source: Cyberabad Police

- **Organization:** Cyberabad Police Commissionerate
- **Authority level:** Tier 1 — police
- **Category:** Traffic authority
- **Source URL:** https://www.cyberabadpolice.gov.in/
- **Machine-readable access:** NO PUBLIC MACHINE-READABLE SOURCE FOUND
- **RSS:** NO · **API:** NO · **HTML:** NO (no advisory listing found) · **PDF:** NO · **Social/public notices:** YES (X, Facebook, WhatsApp)
- **Hyderabad relevance:** Highest for the IT corridor (Gachibowli, Madhapur, Kondapur); it issued the IIIT Junction and Khajaguda advisories.
- **Data provided:** On the website: organisational pages. No traffic advisories were found on the traffic wing page.
- **Update frequency:** Not established.
- **Access requirements:** As for Hyderabad Traffic Police.
- **Licensing/terms notes:** Not reviewed.
- **Integration status:** MANUAL ONLY
- **Reason:** Official source — manual/public notice only.

## Source: Cyberabad Traffic Pulse

- **Organization:** Cyberabad Police Commissionerate
- **Authority level:** Tier 1 — police
- **Category:** Traffic alert service
- **Source URL:** https://cyberabadtrafficpulse.telangana.gov.in/
- **Machine-readable access:** NO
- **RSS:** NO · **API:** NO (registration endpoints only) · **HTML:** NO · **PDF:** NO · **Social/public notices:** YES (alerts to a registered phone)
- **Hyderabad relevance:** High: congestion, accident blockages, event advisories and VIP movements in the Cyberabad area.
- **Data provided:** Alerts for routes a person selects, sent to their phone.
- **Update frequency:** "Depending on the real-time traffic events" (the service's own wording).
- **Access requirements:** Personal registration with a phone number and one-time password; the registration is protected against automated use.
- **Licensing/terms notes:** Registration requires accepting the service's terms, which were not reviewed.
- **Integration status:** MANUAL ONLY
- **Reason:** A subscription service for individuals. It publishes no data feed, and it is not an API.

## Source: Rachakonda Police

- **Organization:** Rachakonda Police Commissionerate
- **Authority level:** Tier 1 — police
- **Category:** Traffic authority
- **Source URL:** https://rachakondapolice.telangana.gov.in/
- **Machine-readable access:** Could not be checked
- **RSS / API / HTML / PDF / Social:** Could not be checked
- **Hyderabad relevance:** Covers the eastern part of the metropolitan area.
- **Data provided:** Unknown.
- **Update frequency:** Unknown.
- **Access requirements:** Unknown.
- **Licensing/terms notes:** Not reviewed.
- **Integration status:** NOT USABLE
- **Reason:** The website did not respond when checked (with and without `www`), so nothing could be verified.

---

# D. Civic and disaster authorities

## Source: Greater Hyderabad Municipal Corporation (GHMC)

- **Organization:** Greater Hyderabad Municipal Corporation
- **Authority level:** Tier 1 — government
- **Category:** Civic body
- **Source URL:** https://www.ghmc.gov.in/
- **Machine-readable access:** NO PUBLIC MACHINE-READABLE SOURCE FOUND
- **RSS:** NO · **API:** NO · **HTML:** NO (no works or closure notices found) · **PDF:** tender and circular documents only · **Social/public notices:** YES (X, Facebook)
- **Hyderabad relevance:** High in principle: road works, drainage, waterlogging.
- **Data provided:** Citizen services, tenders, circulars. The "Traffic and Transportation" page is a departmental description. No GIS or open-data resource for road works was found.
- **Update frequency:** Not applicable.
- **Access requirements:** None to read the website.
- **Licensing/terms notes:** Not reviewed.
- **Integration status:** MANUAL ONLY
- **Reason:** No road-works, closure or waterlogging notices are published in a form that can be consumed.

## Source: HYDRAA

- **Organization:** Hyderabad Disaster Response and Asset Protection Agency
- **Authority level:** Tier 1 — government
- **Category:** Disaster response
- **Source URL:** https://hydraa.telangana.gov.in/
- **Machine-readable access:** NO PUBLIC MACHINE-READABLE SOURCE FOUND
- **RSS:** NO · **API:** NO (none found) · **HTML:** a news page that showed no items without running its web application · **PDF:** boundary maps and orders · **Social/public notices:** YES (X, Facebook, Instagram, WhatsApp channel)
- **Hyderabad relevance:** High for flooding and emergency response.
- **Data provided:** Organisational information. Its rainfall and forecast links lead to TGDPS pages, not to data of its own.
- **Update frequency:** Not established.
- **Access requirements:** None to read the website.
- **Licensing/terms notes:** Not reviewed.
- **Integration status:** MANUAL ONLY
- **Reason:** The rainfall maps it links to are TGDPS web pages, not an API. Alerts go out on social channels.

## Source: TGDPS live rainfall

- **Organization:** Telangana Development Planning Society
- **Authority level:** Tier 1 — government
- **Category:** Weather / rainfall
- **Source URL:** https://tgdps.telangana.gov.in/liveghmcrain.jsp
- **Machine-readable access:** HTML table only; no API found
- **RSS:** NO · **API:** NO · **HTML:** YES · **PDF:** reports · **Social/public notices:** not checked
- **Hyderabad relevance:** High: rainfall per automatic weather station across the Hyderabad area, with district, mandal, location and circle.
- **Data provided:** Rainfall in millimetres for the current day per station. Separate pages give state-wide and hourly views.
- **Update frequency:** Through the day (the page showed the current day up to the current hour).
- **Access requirements:** None to read. The site did not respond at the `www.` address, only without it.
- **Licensing/terms notes:** Not reviewed.
- **Integration status:** DISCOVERED
- **Reason:** Not connected. It would need an HTML connector, and rainfall is context for possible waterlogging, not a road event: it must not create road events by itself.

## Source: Open Data Telangana

- **Organization:** Government of Telangana
- **Authority level:** Tier 1 — government
- **Category:** Open data portal
- **Source URL:** https://data.telangana.gov.in/
- **Machine-readable access:** Dataset downloads; no public API could be confirmed (the standard catalogue API address returned "not found")
- **RSS:** NO · **API:** not confirmed · **HTML:** web application · **PDF:** NO · **Social/public notices:** not checked
- **Hyderabad relevance:** Low for road events.
- **Data provided:** Historical datasets, such as daily weather by mandal. No road-works or road-closure dataset was found.
- **Update frequency:** Historical.
- **Access requirements:** Not established.
- **Licensing/terms notes:** Not reviewed.
- **Integration status:** DISCOVERED
- **Reason:** Historical data is not a live road-event source.

## Source: NDMA SACHET alerts (Telangana)

- **Organization:** National Disaster Management Authority
- **Authority level:** Tier 1 — government
- **Category:** Disaster and weather alerts
- **Source URL:** https://sachet.ndma.gov.in/
- **Machine-readable access:** https://sachet.ndma.gov.in/cap_public_website/rss/rss_telangana.xml
- **RSS:** YES (Common Alerting Protocol) · **API:** NO · **HTML:** YES · **PDF:** NO · **Social/public notices:** not checked
- **Hyderabad relevance:** Low to medium. Alerts are at district level.
- **Data provided:** Weather and flood warnings from IMD Hyderabad and the Central Water Commission: thunderstorms, gusty winds, river flood levels. 10 items in the Telangana feed; 99 in the all-India feed.
- **Update frequency:** As alerts are issued; the newest Telangana item was three days old.
- **Access requirements:** None.
- **Licensing/terms notes:** Not reviewed.
- **Integration status:** DISCOVERED
- **Reason:** The only working official feed found. Deliberately not connected to event creation: it describes weather, not roads. It is a candidate for a separate "context" signal shown to reviewers.

## Source: IMD Meteorological Centre Hyderabad

- **Organization:** India Meteorological Department
- **Authority level:** Tier 1 — government
- **Category:** Weather
- **Source URL:** https://mausam.imd.gov.in/hyderabad/
- **Machine-readable access:** NO PUBLIC MACHINE-READABLE SOURCE FOUND on this site
- **RSS:** NO · **API:** NO · **HTML:** YES · **PDF:** YES (forecasts, rainfall bulletins, press releases) · **Social/public notices:** YES (X, Facebook)
- **Hyderabad relevance:** Medium: district forecasts and rainfall.
- **Data provided:** Forecast and rainfall bulletins.
- **Update frequency:** Daily bulletins.
- **Access requirements:** None.
- **Licensing/terms notes:** Not reviewed.
- **Integration status:** DISCOVERED
- **Reason:** Weather context only. Its warnings already reach the NDMA SACHET feed in machine-readable form.

---

# E. Road authorities, transport operators, other

## Source: National Highways Authority of India (NHAI)

- **Organization:** National Highways Authority of India
- **Authority level:** Tier 1 — road authority
- **Category:** Road authority
- **Source URL:** https://nhai.gov.in/
- **Machine-readable access:** NO PUBLIC MACHINE-READABLE SOURCE FOUND
- **RSS:** NO · **API:** NO · **HTML:** web application · **PDF:** not checked · **Social/public notices:** not checked
- **Hyderabad relevance:** National highways through the region (for example NH-65, NH-44).
- **Data provided:** No closure or diversion notices were found.
- **Update frequency:** Not applicable.
- **Access requirements:** Not established.
- **Licensing/terms notes:** Not reviewed.
- **Integration status:** MANUAL ONLY
- **Reason:** Nothing consumable was found.

## Source: Hyderabad Metropolitan Development Authority (HMDA)

- **Organization:** Hyderabad Metropolitan Development Authority
- **Authority level:** Tier 1 — government
- **Category:** Development authority
- **Source URL:** https://www.hmda.gov.in/notices/
- **Machine-readable access:** HTML notices page; no feed found
- **RSS:** NO · **API:** NO · **HTML:** YES · **PDF:** not checked · **Social/public notices:** YES (X, Facebook)
- **Hyderabad relevance:** Possibly, for the Outer Ring Road; not established.
- **Data provided:** A notices page. Whether it carries road closures was not established.
- **Update frequency:** Not established.
- **Access requirements:** None.
- **Licensing/terms notes:** Not reviewed.
- **Integration status:** DISCOVERED
- **Reason:** Reachable, but its relevance to road events was not established.

## Source: TGSRTC

- **Organization:** Telangana State Road Transport Corporation
- **Authority level:** Tier 2 — transport operator
- **Category:** Bus operator
- **Source URL:** https://www.tgsrtc.telangana.gov.in/
- **Machine-readable access:** NO PUBLIC MACHINE-READABLE SOURCE FOUND
- **RSS:** NO · **API:** NO · **HTML:** NO (no diversion notices found) · **PDF:** NO · **Social/public notices:** YES (X, Facebook)
- **Hyderabad relevance:** Bus diversions would indicate road restrictions.
- **Data provided:** Services and bookings. Its "Open Data" page describes IT initiatives and offers no data.
- **Update frequency:** Not applicable.
- **Access requirements:** None.
- **Licensing/terms notes:** Not reviewed.
- **Integration status:** MANUAL ONLY
- **Reason:** Nothing consumable was found.

## Source: Hyderabad Metro Rail

- **Organization:** L&T Metro Rail (Hyderabad) Ltd.
- **Authority level:** Tier 2 — transport operator
- **Category:** Metro operator
- **Source URL:** https://ltmetro.com/
- **Machine-readable access:** https://ltmetro.com/feed/
- **RSS:** YES · **API:** NO · **HTML:** YES · **PDF:** NO · **Social/public notices:** not checked
- **Hyderabad relevance:** Low for road events.
- **Data provided:** Corporate news (awards, launches). 10 items; the newest was dated December 2025.
- **Update frequency:** A few items a year.
- **Access requirements:** None.
- **Licensing/terms notes:** Not reviewed.
- **Integration status:** NOT USABLE
- **Reason:** The feed works but has no road-event content.

## Source: Rajiv Gandhi International Airport

- **Organization:** GMR Hyderabad International Airport Ltd.
- **Authority level:** Tier 2 — transport operator
- **Category:** Airport
- **Source URL:** https://www.hyderabad.aero/
- **Machine-readable access:** NO PUBLIC MACHINE-READABLE SOURCE FOUND
- **RSS:** NO · **API:** NO · **HTML:** YES (media releases, passenger advisories) · **PDF:** NO · **Social/public notices:** YES (X, Facebook, WhatsApp channel)
- **Hyderabad relevance:** Airport access roads.
- **Data provided:** No airport-access or road advisories were found.
- **Update frequency:** Not established.
- **Access requirements:** None.
- **Licensing/terms notes:** Not reviewed.
- **Integration status:** MANUAL ONLY
- **Reason:** Nothing consumable was found.

## Event organisers

Not investigated source by source. Road-affecting events (marathons, festival
processions, cricket matches) are announced by many separate organisers, each
on its own website or social page, and no common feed was found. In practice
the traffic restrictions for such events are issued by the police and reported
by the news feeds above.

---

# F. Commercial real-time traffic providers

None of these is integrated. Hyderabad coverage has **not** been verified for
any of them: that needs an account and a test.

## Source: TomTom Traffic Incidents API

- **Organization:** TomTom
- **Authority level:** Not assigned (not an approved source)
- **Category:** Commercial traffic data
- **Source URL:** https://docs.tomtom.com/traffic-api/documentation/traffic-incidents/incident-details
- **Machine-readable access:** REST API returning JSON
- **RSS:** NO · **API:** YES · **HTML:** NO · **PDF:** NO · **Social/public notices:** NO
- **Hyderabad relevance:** India is listed in TomTom's coverage table for both the Traffic Incidents and Traffic Flow APIs. Coverage and quality for Hyderabad are untested.
- **Data provided:** Incidents with geometry (point or line), a category (accident, jam, lane closed, road closed, road works, flooding, rain, broken-down vehicle and others), the location name where the incident starts, road numbers, and start and end times when available. Planned incidents can be requested as well as present ones.
- **Update frequency:** Tied to TomTom's traffic model; the exact interval was not confirmed.
- **Access requirements:** An API key. The pricing page lists a free allowance of 2,500 requests a month for this API, with no credit card.
- **Licensing/terms notes:** The pricing page states no storage or redistribution terms; the legal terms were not reviewed. Whether REI may store the data and pass it to customers must be established before any integration.
- **Integration status:** REQUIRES ACCESS
- **Reason:** The most direct route to unplanned incidents with coordinates. Needs an account, a Hyderabad coverage test and a licence review.

## Source: HERE Traffic API

- **Organization:** HERE Technologies
- **Authority level:** Not assigned
- **Category:** Commercial traffic data
- **Source URL:** https://docs.here.com/traffic-api/docs
- **Machine-readable access:** REST API
- **RSS:** NO · **API:** YES · **HTML:** NO · **PDF:** NO · **Social/public notices:** NO
- **Hyderabad relevance:** HERE's documentation lists India among countries with real-time flow and incident coverage. Hyderabad was not verified.
- **Data provided:** Traffic flow and incidents. Field-level detail was not reviewed.
- **Update frequency:** Not verified.
- **Access requirements:** An API key; plan limits were not verified.
- **Licensing/terms notes:** Not reviewed. HERE is also a named REI customer target, which may matter commercially.
- **Integration status:** REQUIRES ACCESS
- **Reason:** A candidate alongside TomTom; less was verified.

## Source: Mappls (MapmyIndia)

- **Organization:** CE Info Systems Ltd.
- **Authority level:** Not assigned
- **Category:** Commercial traffic data
- **Source URL:** https://www.mappls.com/
- **Machine-readable access:** Commercial APIs; no public documentation of an incidents API was found
- **RSS:** NO · **API:** commercial · **HTML:** NO · **PDF:** NO · **Social/public notices:** NO
- **Hyderabad relevance:** Not established. It advertises road closures supplied by traffic police; the partnerships found were with Delhi and Uttar Pradesh police.
- **Data provided:** Advertised: real-time incidents, safety alerts and official planned closures.
- **Update frequency:** Advertised as near real time.
- **Access requirements:** A commercial agreement.
- **Licensing/terms notes:** Not reviewed.
- **Integration status:** REQUIRES ACCESS
- **Reason:** Potentially the best Indian coverage, but nothing could be verified without a sales conversation.

## Source: Waze for Cities

- **Organization:** Google (Waze)
- **Authority level:** Not assigned
- **Category:** Partner data exchange
- **Source URL:** https://www.waze.com/
- **Machine-readable access:** Partner feed
- **RSS:** NO · **API:** partner feed · **HTML:** NO · **PDF:** NO · **Social/public notices:** NO
- **Hyderabad relevance:** No Hyderabad agency partnership was found.
- **Data provided:** Crowd-reported incidents and closures, exchanged with partners.
- **Update frequency:** Reported as every two minutes.
- **Access requirements:** Membership is for government agencies and road operators that contribute their own real-time traffic data.
- **Licensing/terms notes:** Governed by the Waze partner terms.
- **Integration status:** NOT USABLE
- **Reason:** REI is not a government agency or road operator, so it does not qualify.

## Standards and community data

- **OpenStreetMap:** carries the road network and long-term construction tags.
  It is not a source of temporary closures or advisories, and no Hyderabad feed
  of temporary restrictions was found. Relevant later as a road network for GIS
  resolution, not as an event source.
- **WZDx (Work Zone Data Exchange):** a United States specification for
  work-zone feeds. No Indian or Hyderabad WZDx feed was found. Useful as a
  reference when REI defines its own output format.
- **DATEX II:** the European standard for traffic and travel information.
  TomTom offers its incident data in this format. No Indian public DATEX II
  feed was found.

---

# What this means for coverage

| | Planned events | Unplanned incidents |
| --- | --- | --- |
| News RSS (connected) | Yes, when a paper reports the advisory | Rain and waterlogging are reported; accidents are not detected by the current rules |
| Police social channels (not readable by program) | Yes, at the source | Not established |
| Commercial APIs | TomTom can return planned incidents; quality untested | Yes, with coordinates |

- **Authority:** the connected sources are all tier 4. The tier 1 sources exist
  but are published for people only.
- **Freshness:** news follows the police notice; the delay was not measured.
- **Evidence quality:** news gives a headline, usually a summary, and for four
  of the six feeds the full article. It rarely gives exact times and never
  coordinates.
- **History:** RSS only reaches back from hours to two weeks. An advisory
  issued before REI began polling, such as the IIIT Junction closure of June
  2026, cannot be recovered from a feed.

# Licensing

No source's terms of use have been formally reviewed, and every connected
source is marked `terms_reviewed: false`. REI stores the feed content as
internal evidence and shows the headline, a summary and a link back to the
publisher. Before any commercial use or redistribution, each publisher's terms
need to be read by someone qualified to judge them. Terms pages could not be
located at the usual addresses for The Siasat Daily, NewsMeter and The Hans
India. (Corrections: Siasat's terms were found on 14 October 2026, decision
0024; The Hans India's at `/pages/terms-conditions`, decision 0026.)
