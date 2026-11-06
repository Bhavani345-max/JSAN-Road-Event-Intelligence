# Second search of the zero-event countries (6 November 2026)

The user asked to "try these countries for more sources and make it works":
South Africa (2 events to review), Brazil, Ireland, Latvia, Malaysia and Poland
(0 each). Three research agents searched in parallel on 6 November 2026,
14:27–14:48 UTC, under REI's rules: only sources whose licence explicitly
permits commercial reuse; robots.txt read first and obeyed; at least 3 s between
requests to a host; no logins, sign-ups, keys, proxies or faked headers; every
claim backed by a fetch. They skipped what the searches of 4 and 5 November had
already settled (`baltics-poland-ireland-sources-2026-11-04.md`,
`brazil-malaysia-sources-2026-11-04.md`,
`zero-event-countries-sources-2026-11-05.md`). About 80 hosts were checked.

**Result: nothing new can be connected without permission, a registration or
paid credits.** The notable finds are recorded in
`backend/connectors/discovered_2026_11_06.py`, inactive and without a connector.

## Before the search

Poland's two open sources, GDDKiA's `utrdane.xml` (CC0) and Warsaw's
"Utrudnienia w ruchu drogowym" (CC BY 4.0), were tried again on 6 November
2026: `www.archiwum.gddkia.gov.pl`, `www.gddkia.gov.pl` and `dane.um.warszawa.pl`
time out (connect) both from REI's machine in India and from REI's server on
Railway, while `api.dane.gov.pl` answers from both. These hosts appear to accept
connections only from networks nearer to them.

## Finds

| Country | Source | Data on 6 Nov 2026 | Licence | Verdict |
| --- | --- | --- | --- | --- |
| Poland | Białystok road disruptions (ArcGIS, `pl-bialystok-road-disruptions`) | 13 lines, 10 in force, start and end dates, edited that day | none stated anywhere | Needs permission: ask Urząd Miejski w Białymstoku |
| Ireland | Galway County severe-weather road closures (ArcGIS, `ie-galway-county-severe-weather-closures`) | 3 storm closures, all reopened; no start or end | disclaimer and "(c) Galway County Council"; the council's other 77 hub datasets are CC BY 4.0 | Needs permission: ask the council to publish it on its hub |
| Ireland | Kilkenny County Council road notices (`ie-kilkenny-road-notices`) | HTML list, about 4 closures, dates without a year, no coordinates | PSI re-use with rights reserved on text and maps | Not usable |
| Latvia | Riga ĀMD street repairs (data.gov.lv, `lv-riga-amd-street-repairs`) | 404 street lines, no start or end dates | CC BY 4.0 | Not usable: no dates |
| Brazil | ARTESP works programme (`br-artesp-programacao-de-obras`) | only templates, schemas and examples so far | Creative Commons Atribuição | Watch: connectable once real files appear |
| Brazil | Mato Grosso SINFRA road works (`br-mt-sinfra-road-works`) | 830 lines with contract dates, March 2026 snapshot | none | Not usable |

## Also checked, not recorded separately

- **Poland:** dane.gov.pl (utrudnienia, remonty, objazdy, "pasa drogowego",
  "roboty drogowe", "zarząd dróg" and more): nothing hosted on the portal itself;
  Bytom, Gliwice and Gierałtowice files are on `otwartedane.metropoliagzm.pl`,
  which timed out, and date from 2021 to January 2025. A Warsaw layer of possible
  disruptions for September–October 2026 was a one-off without a licence;
  geoportal.gov.pl timed out.
- **Latvia:** data.gov.lv (satiksme, ierobežojumi, remontdarbi, būvdarbi,
  slēgšana and all 78 Riga City datasets). LVC's works map now draws from the
  national access point's internal tiles (an account is needed for its API, as
  before); LVC's own GIS and open-data pages return 404. Riga Water's dispatch
  events are water cuts without traffic restrictions; Liepāja's layer holds test
  content; Jēkabpils lists permanent weight limits.
- **Brazil:** dados.gov.br needs a key; Belo Horizonte's portal answers 403
  "Acesso Bloqueado"; Recife, Distrito Federal, Rio Grande do Sul, DER-PR and the
  Fortaleza and São Paulo state portals did not answer or did not resolve from
  REI's network; DNIT's blockade layers now need a token; Rio's works layer stopped
  in 2013; Salvador's mobility folder is empty; GeoSampa and the national INDE
  GeoServer hold no current events; PRF and ARTESP files are history.
- **Ireland:** data.gov.ie and Smart Dublin forbid automated API queries in
  robots.txt (the national data catalogue was searched instead); Fingal publishes
  monthly counts and an undated programme; data.tii.ie answers 403; Westmeath's
  entry is blank; Cork County's alerts are not open data.
- **Malaysia:** data.gov.my (368 datasets) has no road events; LLM's new
  `TMC/bencana` layer holds 3 test points from 2021; JKR's hosts timed out;
  councils publish press items and PDFs only.
- **South Africa:** City of Cape Town's catalogue (266 datasets) has no closures
  and its terms are silent on reuse; eThekwini's closures download failed its
  certificate check and is dated April 2023 elsewhere; the Johannesburg Roads
  Agency feed's certificate has expired; Western Cape is unchanged (permission).

Two slips by the agent for Ireland, Malaysia and South Africa: gov.ie's robots.txt
answered with a block page that was read as "no rules", and one page request
followed (also blocked); one request to a third-party mirror went out without a
robots check (refused at connection).

## What would unlock these countries

1. **Permission e-mails:** Białystok (new) and Galway County Council (new), plus
   those listed on 5 November (Meath, Cork City, Limerick, TII, Kraków, Łódź,
   Szczecin, Gdynia, COR Rio, DNIT, NADMA, LLM, Western Cape).
2. **Free registration:** Latvia's national access point (e-mail only, CC0), the
   one route to Latvian state-road events; Poland's KPD (organisation form and a
   client certificate).
3. **Credits:** the Serper news searches cover India and Brazil (paused since
   6 November 2026 for lack of credits).
4. **Network:** the Polish government hosts above, and several Brazilian state
   portals, did not answer from India or from Railway; they may answer a server
   hosted nearer to them. Not tried.
