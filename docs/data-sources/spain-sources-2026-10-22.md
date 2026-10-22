# Spain: new road-event sources, 22 October 2026

**Status:** research only. No code was changed, nothing was connected,
committed or deployed, and no email or form was sent. This is a reading of
published terms, not legal advice.

Research base:
- [spain-connectors-2026-10-21.md](spain-connectors-2026-10-21.md) (the four
  built connectors).
- The Spain parts of
  [europe-official-road-sources-2026-10-16.md](europe-official-road-sources-2026-10-16.md).

Those sources are not repeated here: `dgt-spain-incidents` (held),
`barcelona-public-space-works`, `madrid-informo-incidents` and
`euskadi-traffic-incidences`.

## Result in short

- **Two new PERMITTED sources were verified live:**
  - **Servei Català de Trànsit (SCT) incidents GML**, at
    `www.gencat.cat/transit/opendata/incidenciesGML.xml`. It covers Catalonia,
    which DGT's feed leaves out: 198 points, mostly roadworks. Reuse is allowed
    by the Generalitat's open reuse notice, with credit. **It gives no end
    times**, so under the 15 October display rule every record would be
    *unconfirmed* and hidden.
  - **Málaga traffic cuts (*cortes de tráfico*)**, a GeoJSON file: 110 points,
    with start and end on 101 to 103 of them. The dataset is marked
    "CC BY 4.0", but its licence link points to CC BY-SA 4.0.
- **DGT clarification: nothing has changed.**
  - The NAP incidents dataset still says "Creative Commons Attribution" with no
    version.
  - Its "Condition for use" still points to DGT's general legal notice
    (*aviso legal*). That notice was not changed (it is still dated 10 February
    2022) and still forbids unauthorised commercial reuse.
  - No NAP-wide licence or terms page exists. The NAP "About" page has no
    terms.
  - New finding: other DGT datasets on the same NAP state "Contract or
    licence: **CC BY 4.0**" explicitly, so DGT can declare a versioned licence
    when it wants to. The incidents dataset does not.
  - Keep `dgt-spain-incidents` **held** and ask nap@dgt.es.
- **ASK_PERMISSION:**
  - **Incidents DT-GV**: the Basque Traffic Directorate's DATEX II feed on the
    NAP. It has 162 records, ends on 100 and coordinates on 108. Its NAP page
    says "No licence – No contract".
  - DGT incidents (unchanged).
  - SCT's DATEX II on the NAP (unchanged). The gencat.cat feed above replaces
    it.
- **Licence permits reuse, but the data can't be fetched politely:**
  - **Navarra** road status: CC BY 4.0, but the host is unreachable from the
    research network.
  - **Castilla y León** road incidents: CC BY 4.0, but robots.txt disallows
    the portal's API and downloads, and the source host refused the
    connection.
  - **Valencia city** public-road occupation: CC BY 4.0, but the geoportal
    reset the connection.
  - **Madrid Calle 30** planned works: CC BY 4.0, but the download path is
    disallowed by robots.txt.
  - **DGT 3.0** sports-event segments and connected cones: CC BY 4.0, but they
    need certificates from DGT 3.0.
- **No road-event dataset was found** for:
  - Andalucía, Comunitat Valenciana, Galicia and Valladolid.
  - Palma, Las Palmas, Murcia, Córdoba and Gijón (search only, or a JavaScript
    catalogue).
- **Unreachable from the research network** (timeouts, connection resets or
  DNS failures, likely network filtering):
  - Regions: Comunidad de Madrid, Aragón, Cantabria, Canarias, Baleares,
    Castilla-La Mancha, Región de Murcia.
  - Cities: Zaragoza, Sevilla, Vitoria-Gasteiz.
  - **Re-test these from REI's production network before ruling them out.**

## Summary table

"Items" are counted at fetch time on 22 October 2026, between 10:48 and
11:21 UTC.

| Source | Type | URL | HTTP | Items | Dates? | Geometry? | robots.txt | Licence | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SCT incidents, Catalonia | GML (WFS 1.0 FeatureCollection) | `www.gencat.cat/transit/opendata/incidenciesGML.xml` | 200, 181 KB | 198 (works 190, queues 8) | one timestamp (`data`); **no end** | WGS 84 point on all 198 | allowed | Generalitat reuse notice: Llicència oberta d'ús d'informació – Catalunya / CC0 equivalent, with attribution | **PERMITTED** (start only) |
| SCT incidents RSS, Catalonia | RSS 2.0 | `www.gencat.cat/transit/opendata/incidenciesRSS.xml` | 200, 70 KB | 218 | publication time only | none | allowed | as above | PERMITTED (no geometry; GML preferred) |
| Málaga traffic cuts | GeoJSON (also CSV, GML, KML, SHP) | `datosabiertos.malaga.eu/recursos/transporte/trafico/da_cortesTrafico-4326.geojson` | 200, 78 KB | 110 | start 103, end 101 | point on all 110 | allowed (Crawl-delay 10) | "CC BY 4.0" (the link points to CC BY-SA 4.0) | **PERMITTED** |
| Incidents DT-GV (Basque Traffic Directorate) | DATEX II 1.0 | `nap.dgt.es/datex2/dt-gv/SituationPublication/all/content.xml` | 200, 833 KB | 154 situations / 162 records | start 162, end 100 | lat/lon on 108; ALERT-C only on 54 | allowed | NAP: "No licence – No contract", condition "-" | ASK_PERMISSION |
| DGT incidents DATEX II 3.7 (re-check) | DATEX II 3.7 | `nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v37.xml` | not fetched (page only) | — | — | — | allowed | "Creative Commons Attribution" (no version); condition: DGT aviso legal | ASK_PERMISSION (held) |
| DGT 3.0 sports-event segments (use case 10) | MQTT / REST (DGT 3.0) | `ssl://production.cmobility30.es:8883`, `pre.cmobility30.es/use-case-10` | not fetched (needs certificates) | — | — | lines / points | — | NAP: "Contract or licence: CC BY 4.0" | NEEDS_KEY |
| DGT 3.0 connected cones (use case 12) | REST (DGT 3.0) | `pre.cmobility30.es/use-case-12` | not fetched | — | — | points | — | not read | NEEDS_KEY |
| Navarra road status | CKAN datastore (CSV, JSON, XML) | `datosabiertos.navarra.es/dataset/f7cafe87-…/resource/9323f68f-…/download/incidenciasdecarreteras.csv` | TCP timeout | — | — | — | unreachable | CC BY 4.0 (datos.gob.es record) | UNREACHABLE (licence OK) |
| Castilla y León road incidents | JSON / XML / CSV | `servicios.jcyl.es/InviPublica/OpenData?formato=json` (redirect target) | connection closed, twice | — | — | — | origin: unreachable; ODS mirror: `/api/` and downloads disallowed | CC BY 4.0 | RESTRICTED for now (robots) |
| Valencia city public-road occupation | ArcGIS REST GeoJSON | `geoportal.valencia.es/server/rest/services/OPENDATA/Trafico/MapServer/209/query?where=1=1&outFields=*&f=geojson` | connection reset, twice | — | `fecha_inicio`, `fecha_fin` (data model) | yes (layer) | unreachable | CC BY 4.0 | UNREACHABLE (licence OK) |
| Madrid Calle 30 planned works | XML | `datos.madrid.es/egob/catalogo/212422-7905615-trafico-calle30-planificados.xml`, which redirects to `/dataset/…/resource/…/download/…` | 302 to a disallowed path | — | — | — | **download path disallowed** | CC BY 4.0 | RESTRICTED (robots) |
| Tenerife road incidents (Cabildo) | JSON / CSV per year | `datos.tenerife.es/ckan/…/incidencias-en-carreteras-2026.json` | 200, 2.4 MB | 10,503 (1 Jan to 5 Oct 2026) | start only | none (road and section names) | allowed | "Creative Commons Attribution" (`cc-by`) | NOT USEFUL (monthly history) |
| Lorca "other traffic incidents" | JSON | `datos.lorca.es/catalogo/otras-incidencias-trafico/otras-incidencias-trafico.json` | 200, 2 bytes | 0 | fields exist | lat/lon fields | none (404) | "Las recogidas en el Aviso Legal" (not read) | NOT USEFUL (empty) |
| A Coruña open data | CKAN | `datos.coruna.gal` | — | — | — | — | `Disallow: /` | — | RESTRICTED (robots) |
| Salamanca traffic-cuts map | CKAN | `opendata.aytosalamanca.es/…/mapa-cortes-trafico` | robots.txt 503 | — | — | — | treated as full disallow | — | not fetched |
| Bilbao works affecting traffic | GeoJSON | `www.bilbao.eus/aytoonline/srvDatasetObra?formato=geojson` | 403 (robots too) | — | — | — | 403 | not read | BLOCKED (covered by Euskadi API sourceId 5) |
| Barcelona traffic-incident notices (*frase*) | TXT | `opendata-ajuntament.barcelona.cat` package `425f3411-…` | read timeout, twice | — | — | — | 403 (no rules) | CC BY 4.0 (datos.gob.es record) | not verified |
| Zaragoza street incidents | JSON | `www.zaragoza.es/sede/servicio/incidencia/via-publica.json` | TCP timeout | — | — | — | unreachable | not read | UNREACHABLE |
| Commercial: TomTom, HERE (listed on the NAP) | — | `nap.dgt.es/en/organization/tomtom`, `/here` | — | — | — | — | — | NAP facet "Other (Not Open)" | not open |

## DGT clarification (nap.dgt.es, 10 requests, at least 10 s apart)

### What the incidents dataset says now

Page: <https://nap.dgt.es/en/dataset/incidencias-dgt-datex2-v3-7>,
"Last Updated June 10, 2026".

- "License: Creative Commons Attribution". The link goes to
  `http://www.opendefinition.org/licenses/cc-by`, with no version.
- "Contract or licence: Licence and Free of charge".
- "Condition for use: https://www.dgt.es/contenido/aviso-legal/".
- Link to resource:
  `https://nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v37.xml`.

This is the same as on 16 and 21 October.

### DGT's legal notice, re-read

Page: <https://www.dgt.es/contenido/aviso-legal/>. HTTP 200; the page still
says "Fecha actualización: 10 febrero 2022". The wording is unchanged:

> Los derechos de propiedad intelectual de este portal de Internet, su diseño
> gráfico y los códigos que contiene, son titularidad de la Dirección General
> de Tráfico, a no ser que se indique otra diferente. La reproducción,
> distribución, comercialización o transformación no autorizadas de dichas
> obras, a no ser que sea para uso personal y privado, constituye una
> infracción de los derechos de propiedad intelectual…

> La ubicación no autorizada de la información contenida en este portal, así
> como los perjuicios ocasionados en los derechos de propiedad intelectual e
> industrial de la Dirección General de Tráfico, podrán dar lugar al ejercicio
> de las acciones legales correspondientes…

In English: unauthorised reproduction, distribution, commercialisation or
transformation is an infringement unless it is for personal and private use.
Unauthorised placing of the portal's information elsewhere may lead to legal
action.

### No NAP-wide terms page

- The NAP menu has only Datasets, Organizations and About.
- `/en/about` describes the NAP under Delegated Regulation 886/2013. It has no
  licence or terms text.

### New: DGT declares CC BY 4.0 explicitly on some datasets

Page: <https://nap.dgt.es/en/dataset/segmentos-correspondientes-a-pruebas-deportivas>
("Linestring corresponding to sport events", publisher "DGT 3.0").

- "Contract or licence: **CC BY 4.0**".
- "Condition for use: https://creativecommons.org/licenses/by/4.0/deed.es".

So DGT can, and sometimes does, state a versioned licence without pointing to
the aviso legal. The incidents dataset does neither.

### Reading

- Unchanged from 21 October: the dataset carries an unversioned CC BY label,
  and its own condition for use points to a notice that forbids unauthorised
  commercial reuse.
- **Keep `dgt-spain-incidents` held.**
- Suggested question for nap@dgt.es (not sent):
  - Is the licence of *Incidencias DGT DATEX2 v3.7* CC BY 4.0?
  - Does that licence allow commercial reuse, overriding the aviso legal's
    restriction?
  - What attribution wording does DGT want?

### Other road-event datasets on the NAP

From `/en/organization/dgt` (19 datasets) and the searches `?q=incidencias`
(13 found) and `?q=obras` (6 found):

| NAP dataset | Owner | Licence statement on the NAP | Notes |
| --- | --- | --- | --- |
| Incidents DGT DATEX2 v3.7 | DGT | "Licence and Free of charge"; condition: aviso legal; CKAN label "Creative Commons Attribution" | held (above) |
| Linestring corresponding to sport events | DGT 3.0 | **"CC BY 4.0"**, condition: CC BY 4.0 deed | Update every 15 s. Access per the GitHub wiki: MQTT `ssl://production.cmobility30.es:8883` and REST `https://pre.cmobility30.es/use-case-10`, with tables `out_usecase10_cones` and `out_usecase10_v2`. Errors include `401 "User not found or valid"`. Certificates come from soporte@cmobility30.es. **NEEDS_KEY** |
| Location of cones for sporting events | DGT 3.0 | page not fetched (request cap) | same use case 10 |
| Connected cones (roadworks) | DGT 3.0 | page not fetched | Use case 12 wiki: "La funcionalidad de publicación requiere de certificados de acceso … soporte@cmobility30.es". **NEEDS_KEY** |
| Dynamic sending of slow vehicle positions | DGT 3.0 | not read | slow special vehicles (V-2 signal); not a road event |
| Traffic Incidents (SRTI) in LOD DATEX II | DGT | not read | RDF; not fetched |
| Incidents DT-GV | Trafiko Zuzendaritza / Dirección de Tráfico (Basque Government) | **"No licence – No contract"**, condition "-" (sidebar label "Creative Commons Attribution") | source 3 below |
| Incidents SCT | Servei Català de Trànsit | "No licence – No contract" (16 Oct) | replaced by the gencat.cat feed (source 1) |
| Calle 30 incidents; Calle 30 scheduled roadworks | Madrid Calle 30 control centre | "Licence and Free of charge"; condition "Link" (datos.madrid.es, CC BY 4.0) | source 7 below |
| Madrid incidents in public roads (XML, KML) | Ayuntamiento de Madrid | — | already built (`madrid-informo-incidents`) |
| SPFRIA / *tefiva* | Dirección General de Carreteras (MITMA) | not read | animal-collision sections; static, not events |
| TomTom Traffic, TomTom SRTI API, HERE Traffic | commercial | "Other (Not Open)" (2 in the licence facet) | commercial; skipped |

- **Licence facet** of the `incidencias` search: "Creative Commons At…" 10,
  "Other (Not Open)" 2, "License not specified" 1.
- **Organisations on the NAP:** DGT, SCT, DT-GV, Ayuntamiento de Madrid,
  112 Comunitat Valenciana, 112 Galicia, Diputación de Valencia, Diputación
  Foral de Gipuzkoa, DG Carreteras del MITMA, TomTom and HERE.
  - The 112 organisations and the two Diputaciones had no dataset matching
    "incidencias" or "obras". Their pages were not opened because of the
    request cap.

## Per-source notes

### 1. Servei Català de Trànsit incidents, Catalonia (PERMITTED, start only)

Authority: Generalitat de Catalunya, Departament d'Interior i Seguretat
Pública, Servei Català de Trànsit. Catalonia is not covered by DGT's feed.

**Endpoints**
- `GET https://www.gencat.cat/transit/opendata/incidenciesGML.xml`: HTTP 200,
  180,905 bytes, `application/xml`, UTF-8. `Last-Modified` was 10:57:04 GMT,
  about 10 minutes before the fetch.
- `GET https://www.gencat.cat/transit/opendata/incidenciesRSS.xml`: HTTP 200,
  70 KB, 218 items. The RSS has no coordinates.
- **robots.txt (www.gencat.cat):** disallows only `/mediamb/pn/espais`,
  `/eadop/…`, `/vtls`, `/cgi-bin`, `/diari/`, `/diari_c/` and one PDF.
  `/transit/opendata/` is allowed. No Crawl-delay.

**Catalogue entry**
- Socrata entry `uyam-bs37`, "Incidències viàries en temps real a Catalunya",
  read through `analisi.transparenciacatalunya.cat/api/views/uyam-bs37.json`
  (`/api/` is allowed there; Crawl-delay 1).
- It lists both URLs as access points: "Freqüència d'actualització: Contínua".
- It says `"license": "See Terms of Use"`, attribution "Departament d'Interior
  i Seguretat Pública".
- Its attribution link is
  `administraciodigital.gencat.cat/ca/dades/dades-obertes/informacio-practica/llicencies/`.
  That host's robots.txt is `User-agent: * / Disallow: /`, so the page was not
  read.

**Licence: the Generalitat's legal notice**

Page: <https://tramits.gencat.cat/ca/ajuda/avis_legal/>, read live; robots.txt
allows it.

> La Generalitat de Catalunya permet la reutilització dels continguts i de les
> dades per a tot el món i sense cap mena de limitació temporal ni restricció,
> en els termes establerts per la Llicència oberta d'ús d'informació –
> Catalunya o per l'equivalent instrument legal CC0 de Creative Commons, …
> (citació de la font, no alteració ni desnaturalització de la informació i
> especificació de la data d'última actualització), i sempre que no es
> contradigui amb la llicència o avís que pugui tenir una obra i que és la que
> preval.

The same page adds:
- "Amb el concepte reutilització … ens referim a l'ús que en poden fer
  persones, empreses i organitzacions per crear nous productes i/o serveis".
- Required credit: "Generalitat de Catalunya. Departament de [nom
  departament]. [organisme autònom, empresa pública]".
- Logos and marks may not be used.

**Reading:** worldwide reuse without restriction, CC0-equivalent, explicitly
including companies building products. Conditions:
- cite the source;
- do not alter or distort the information;
- state the date of last update.

The dataset's "See Terms of Use" sends readers to these Generalitat terms; no
specific licence or notice that would take precedence was found.

- **Verdict:** PERMITTED.
- **Credit:** "Generalitat de Catalunya. Departament d'Interior i Seguretat
  Pública. Servei Català de Trànsit", plus the time the data was fetched.
- **Caveat:** the licence page the dataset links to is robots-blocked and was
  not read.

**Format (GML)**
- `wfs:FeatureCollection`. Each feature is a `cite:mct2_v_afectacions_data`
  with a `gml:Point` in EPSG:4326, written `lon,lat`.
- Fields, all filled on all 198:
  - `identificador`: unique, 198 distinct.
  - `tipus` and `subtipus`.
  - `carretera`, `pk_inici`, `pk_fi`.
  - `causa`, `descripcio`, `descripcio_tipus`.
  - `data`: RFC 1123, GMT.
  - `nivell`, `sentit`, `font` (always "SCT").
  - `cap_a` (towards) is filled on 75.
- **No end time and no geometry beyond the point.**

**Live (10:58 UTC)**
- **Counts:** 198 features, 198 distinct ids.
- **Types:** `descripcio_tipus` Obres 190, Retenció 8.
- **Descriptions:** "Calçada restringida" 178, "Calçada tallada" 9,
  "Calçada restringida. Desviaments" 2, "Calçada tallada. Desviaments" 1,
  queue texts 8.
- **Causes:** maintenance 50, road markings 18, general works 16, gardening 15,
  cleaning 13, alignment 10, pavement 8, bridges 8, slope stabilisation 8,
  fibre 8, and others including landslide 3, breakdown 3 and carriageway
  collapse 1.
- **Direction:** both 152, increasing 31, decreasing 15.
- **`data` range:** 2024-02-08 to 2026-10-22; 193 in 2026, 120 in October
  2026. Long works keep their original date.
- **Extent:** 41.08 to 42.68 °N, 0.65 to 3.18 °E.
- The RSS has 218 items. About 20 have no GML point. The NAP DATEX II copy
  had 230 records with a point on 198 on 16 October.

**Suggested REI mapping (from codes and fixed phrases only)**
- `descripcio` "Calçada tallada" (with Obres): planned closure.
- "Calçada restringida": lane restriction.
- "Desviaments": keep the word; do not draw a diversion.
- `descripcio_tipus` Retenció (queues): not taken, as with DGT's
  AbnormalTraffic.
- `causa` is kept as words.
- `data` is the only time. Treat it as the stated start/notice time, never as
  an end.

**Expected volume:** about 200 records live, nearly all works, plus a few
queues.

**REI caveat:** no record has an end time, so under the 15 October rule all
are *unconfirmed* and hidden. This is the same situation as Euskadi
`sourceId 1`. The records would still be stored as evidence.

### 2. Málaga traffic cuts (*cortes de tráfico*) (PERMITTED)

Authority: Ayuntamiento de Málaga (author "Responsable de movilidad").

**Endpoint and access**
- `GET https://datosabiertos.malaga.eu/recursos/transporte/trafico/da_cortesTrafico-4326.geojson`:
  HTTP 200, 78,479 bytes, `application/geo+json`.
- `Last-Modified: Thu, 22 Oct 2026 02:52:24 GMT`, so it is rebuilt daily.
- The same layer exists as CSV, GML, KML and SHP, in EPSG:4326 and 25830.
- Map preview: `callejero.malaga.eu/?gplayers=corte-trafico`.
- **robots.txt:** `Disallow: /dataset/rate/`, `/revision/`,
  `/dataset/*/history`, `/api/`; `Crawl-delay: 10`. `/recursos/` and
  `/dataset/<name>` pages are allowed.
- **TLS:** the certificate is issued by FNMT-RCM. The first attempt failed
  verification on this machine; later attempts passed. REI's httpx uses the
  certifi bundle, which verified the chain in a test.

**Licence**

Page: <https://datosabiertos.malaga.eu/dataset/cortes-de-trafico>.
- The licence block reads "Creative Commons Atribución/Reconocimiento 4.0
  Licencia Pública Internacional — CC BY 4.0".
- But the link target is `http://creativecommons.org/licenses/by-sa/4.0/`, and
  the page's schema.org metadata says
  `"schema:license": "http://creativecommons.org/licenses/by-sa/4.0/"`.
- Both licences allow commercial use. BY-SA also requires adapted material to
  be shared alike.
- **Verdict:** PERMITTED. Credit "Ayuntamiento de Málaga".
- **Caveat:** treat the data as CC BY-SA 4.0 until Málaga confirms which
  licence it means. Málaga's general aviso legal was not read.

**Format**
- A FeatureCollection of Points. Properties:
  - `ID` (integer) and `NOMBRE` (for example `AFECTACION_0000576_313322`).
  - `DESCRIPCION`, `DIRECCION`, `TITULARIDAD` (always MUNICIPAL).
  - `DESDE` and `HASTA` as `dd/mm/yyyy H:MM`, local time.
  - `TIPOCORTE`, `TIPOAFECTACION`, `NOTAS` (on 50).
  - Empty tourism fields (`URL`, `PRECIOS`, `TARJETAJOVEN` and others).
- **Coordinates have a bogus third value**, for example
  `[-4.3995, 36.7238, 4065143.43]`, which looks like the EPSG:25830 northing.
  Drop it.

**Live (10:59 UTC)**
- **Counts:** 110 features, all points.
- **Times:** start parsed on 103 and end on 101. The 7 records without dates
  also have a blank type.
- **Status:** 103 current, 7 upcoming, 0 ended.
- **Date ranges:** starts 2025-05-29 to 2026-12-04; ends 2026-10-23 to
  2028-11-12.
- **`TIPOCORTE`:** Obras 101, Izado (crane lift) 2, blank 7.
- **`TIPOAFECTACION`:** Ocupación de calzada 60, Corte 34, Ocupación de
  estacionamiento 9, blank 7.

**Suggested REI mapping**
- `TIPOAFECTACION` Corte: planned closure.
- Ocupación de calzada: lane restriction.
- Ocupación de estacionamiento (parking only): not taken, or no type.
- `TIPOCORTE` Izado: keep the word.
- `DESCRIPCION` is the summary only. It is never parsed for times or extents.
- **Identity:** `NOMBRE` (or `ID`).

**Expected volume:** about 100 to 110 live. A new `malaga` city entry is
needed (bbox about 36.65, −4.56, 36.80, −4.33).

### 3. Incidents DT-GV, Basque Country (ASK_PERMISSION)

Owner: Trafiko Zuzendaritza / Dirección de Tráfico, Gobierno Vasco
(etkzkud@trafikoa.eus, 94 400 98 91). Published through the NAP.

**Endpoint**
- `GET https://nap.dgt.es/datex2/dt-gv/SituationPublication/all/content.xml`:
  HTTP 200, 833,281 bytes, `Cache-Control: max-age=60`.
- DATEX II 1.0 (`http://datex2.eu/schema/1_0/1_0`). The NAP says it updates
  every 9 minutes.
- `/datex2/` is allowed by the NAP's robots.txt.

**Licence**

Page: <https://nap.dgt.es/en/dataset/incidencias-dt-gv>, "Last Updated
September 25, 2026".
- "Contract or licence: No licence – No contract".
- "Condition for use: -".
- The CKAN sidebar label still says "Creative Commons Attribution".
- With no stated licence and contradictory labels, the verdict is
  ASK_PERMISSION.

**Live (publicationTime 2026-10-22T12:45:19+02:00)**
- **Counts:** 154 situations, 162 records.
- **Record types:**
  - MaintenanceWorks 95 (`roadMaintenanceType` roadworks).
  - ConstructionWorks 53.
  - Accident 5.
  - Activities 5 (`publicEventType` athleticsMeeting 4, bicycleRace 1).
  - VehicleObstruction 4.
- **Times:** start on all 162 and end on 100. 130 current, 29 upcoming, 3
  ended but still listed.
- **Date ranges:** starts 2024-11-07 to 2027-06-10; ends 2026-10-22 to
  2027-09-30.
- **Location:** lat/lon on 108 records (TPEG linear or point); 54 carry only
  ALERT-C location codes.

**Why it matters**
- REI's Euskadi API (`sourceId 1`) gives region-wide incidences with no ends.
- DT-GV gives planned roadworks and sporting events with ends and coordinates.
- Worth asking etkzkud@trafikoa.eus (and nap@dgt.es) for the licence.
- The Open Data Euskadi CC BY 4.0 terms may already cover it if the
  Directorate confirms the feed is the same data.

**Suggested mapping if permitted:** works become road works; Activities with a
publicEventType become an event; Accident becomes an accident;
VehicleObstruction becomes a road hazard.

### 4. Navarra road status (licence OK, host unreachable)

Owner: Gobierno de Navarra, Centro de Control de Conservación de Carreteras.
The datos.gob.es record (title search for "carreteras", modified
16 Oct 2026) lists the distributions:
- `https://datosabiertos.navarra.es/dataset/f7cafe87-6a49-452e-b846-336c12d6a279/resource/9323f68f-9c8f-47e1-884c-d6985b957606/download/incidenciasdecarreteras.csv`
- `datastore/dump/9323f68f-…?format=json|xml|tsv|ods|xlsx`
- An XSD, `incidenciasdecarreteras.xsd`.
- Each carries
  `license = http://publications.europa.eu/resource/authority/licence/CC_BY_4_0`.

**What happened:** `datosabiertos.navarra.es` did not accept a TCP connection
on port 443 (timeout). Its robots.txt and data were not read.

**What is known:** search summaries describe a 15-minute update of weather,
road and works incidents. Fields, counts and geometry were **not verified**.

**Next step:** re-test from REI's production network. This is a likely
PERMITTED source.

### 5. Castilla y León road incidents (CC BY 4.0, access blocked)

Owner: Junta de Castilla y León, regional road network.

**Access**
- `datosabiertos.jcyl.es/web/jcyl/risp/es/transporte/incidencias_carreteras/1284212099243.json`
  answers 302 to `https://servicios.jcyl.es/InviPublica/OpenData?formato=json`.
- `servicios.jcyl.es` closed the connection on its robots.txt twice. Under
  RFC 9309 an unreachable robots.txt means full disallow, so the feed was not
  requested.
- The Opendatasoft mirror,
  `analisis.datosabiertos.jcyl.es/explore/dataset/incidencias-en-la-red-de-carreteras-titularidad-de-la-junta-de-castilla-y-leon/`,
  says "Frecuencia de actualización: Cada 10 mint." and
  `"license_url": "https://creativecommons.org/licenses/by/4.0/deed"`.
- That host's robots.txt disallows `/api/`, `/explore/download` and
  `/explore/dataset/*/download`. So every machine route to the data is
  disallowed.

**Verdict:** RESTRICTED for now, by robots and not by the licence.

**Next step:** ask the Junta for a permitted machine endpoint, or re-test
`servicios.jcyl.es/robots.txt` from another network.

### 6. Valencia city public-road occupation (CC BY 4.0, geoportal unreachable)

**Dataset page:**
<https://opendata.vlci.valencia.es/dataset/ocupacio-via-publica-ocupacion-via-publica>.
- "Licencia: Atribución 4.0 Internacional (CC BY 4.0)".
- "Información geográfica referente a la ocupación de la vía pública por
  festejos, incidencias u obras".
- **Data model:** `id_incidencia`, `desc_incidencia`, `tipo_incidencia`,
  `desc_calle`, `tipo_afectacion`, `fecha_inicio`, `fecha_fin`,
  `numero_policia_origen`.
- **Resources:** ArcGIS layer 209 of
  `geoportal.valencia.es/server/rest/services/OPENDATA/Trafico/MapServer`, in
  GeoJSON, JSON, KMZ, PBF and WFS, plus a ZIP.
- **robots.txt (opendata.vlci.valencia.es):** `/api/` disallowed,
  Crawl-delay 10.

**What happened:** `geoportal.valencia.es` reset the connection on its
robots.txt twice. Nothing was read.

**Next step:** re-test from production. This is a likely PERMITTED source with
start and end dates, covering festivities, incidents and works.

**Also seen** in the "tráfico" search (44 datasets), none of them events:
- `talls-transit-falles` (Fallas closures), which search snippets date to
  December 2019.
- `estat-transit-temps-real` (traffic state).
- Cameras, loops, ORA parking and similar.

### 7. Madrid Calle 30 planned works (CC BY 4.0, robots-blocked)

**Dataset page:** <https://datos.madrid.es/dataset/212422-0-trafico-calle30-planificados>.
- "Licencia: Creative Commons Attribution 4.0 International (CC BY 4.0)".
- Updated every 5 minutes.

**Access**
- The NAP access URL
  `http://datos.madrid.es/egob/catalogo/212422-7905615-trafico-calle30-planificados.xml`
  answers 302 to
  `/dataset/212422-0-trafico-calle30-planificados/resource/212422-0-trafico-calle30-planificados/download/…`.
- datos.madrid.es's robots.txt disallows `/dataset/*/resource/*/download/*`
  (and `/*?`, with `Crawl-delay: 10`).
- The redirect was not followed.

**Verdict:** RESTRICTED (robots).

**Notes:**
- Calle 30 incidents (the NAP's `trafico-calle-30-incidencias`) were not
  checked. They probably use the same download path.
- Ask datos.madrid.es (or madridcalle30@mc30.es) for a permitted machine path,
  as REI already uses for Informo on `informo.madrid.es`.

### 8. Others checked

- **Tenerife road incidents** (Cabildo de Tenerife, `datos.tenerife.es`).
  - `package_show`: `license_id "cc-by"`, "Creative Commons Attribution".
    robots.txt `Allow: /`.
  - Yearly JSON and CSV files, updated monthly. The 2026 file
    (`Last-Modified` 1 Oct 2026) holds 10,503 incidents from 1 January to
    5 October.
  - Fields: road, section, communication type, start time, type and subtype.
    Types include Tráfico 4,907, Accidentes 1,395, Tareas Mantenimiento 1,301
    and Obras 607.
  - No coordinates and no end. A historical log, **not useful** for live
    events.
  - The live service is `cic.tenerife.es` (not fetched).
- **Lorca** "Otras incidencias de tráfico".
  - Daily, last updated 22/10/2026, with fields for street, start, end and
    lat/lon.
  - It returned `[]`.
  - Conditions "Las recogidas en el Aviso Legal" (not read).
- **Andalucía** (Junta CKAN, `/api/` allowed): "carreteras" found 4 datasets,
  only maps and tariffs (all CC BY 4.0); "tráfico" found 0.
- **Comunitat Valenciana** (`dadesobertes.gva.es`, `/api/` disallowed, HTML
  search used): "carreteras" found 18 and "incidencias" found 18. Only traffic
  counts, noise maps, snow plans, contracts and an accessibility study.
- **Galicia** (`abertos.xunta.gal`): no road-event dataset found. The guessed
  catalogue URL returned 404, and searches found none.
- **Valladolid** (`valladolid.es` open-data files): the transport sector has
  bike stations, ORA parking and EV chargers only.
- **Gijón:** `datos.gijon.es` redirects to `www.gijon.es/es/datos`, a
  JavaScript app backed by `api.gijon.es`. No traffic-cut dataset was found
  by search; the API was not explored.
- **Bilbao** "Obras con afección al tráfico"
  (`www.bilbao.eus/aytoonline/srvDatasetObra?formato=geojson`): HTTP 403 on
  robots.txt and data. Bilbao's works are already in the Euskadi API
  (`sourceId 5`).
- **Vitoria-Gasteiz** "Incidencias de tráfico"
  (`www.vitoria-gasteiz.org/j16-02w/capaAction.do?…c=704`): TCP timeout.
  datos.gob.es says it was last modified in 2020. Covered by the Euskadi API
  (`sourceId 6`).
- **Donostia:** covered by the Euskadi API (`sourceId 7`). Its "Zonas de
  obras" cartography was last modified in 2020 (not fetched).
- **Diputació de Barcelona:** its local-road incident notices are passed to
  SCT, which publishes them (Diputació transparency page, via search). No
  separate open feed was found.
- **Palma, Las Palmas, Murcia (city), Córdoba, Sevilla:** web searches found
  no traffic-cut or works dataset. Sevilla's host timed out. The others'
  portals were not fetched.

## Recommended to connect

Ranked by value to REI.

1. **Málaga traffic cuts** (PERMITTED).
   - About 110 live points, with start and end on over 90%. Rebuilt daily.
   - Can be shown at once under the display rules.
   - Needs a `malaga` city entry and a decision to treat the data as CC BY-SA
     4.0 until Málaga confirms.
2. **SCT incidents GML, Catalonia** (PERMITTED, start only).
   - About 200 points on the Catalan road network, the only official Catalan
     source REI can use.
   - All records lack an end, so they would be stored but hidden as
     unconfirmed.
   - Connect it if REI wants Catalonia evidence now; it becomes visible only if
     the display rule changes for start-only official feeds.
   - Credit "Generalitat de Catalunya. Departament d'Interior i Seguretat
     Pública. Servei Català de Trànsit" with the fetch date.

**Worth pursuing, not connectable today:**

3. **Navarra road status** (CC BY 4.0): re-test from production.
4. **Valencia city public-road occupation** (CC BY 4.0): re-test from
   production.
5. **Incidents DT-GV** (ask etkzkud@trafikoa.eus / nap@dgt.es). It would add
   planned works and sporting events with ends to the Basque coverage.
6. **DGT incidents** (ask nap@dgt.es for the licence version and commercial
   reuse).
7. **Castilla y León incidents** (ask the Junta for a permitted endpoint).
8. **Madrid Calle 30 planned works and incidents** (ask datos.madrid.es for a
   permitted path).
9. **DGT 3.0 sports events and connected cones** (CC BY 4.0). Certificates
   from soporte@cmobility30.es would be needed. That is a registration, which
   REI's rules leave to the user.

## Requests made

- **User-Agent:** `JSAN-REI/1.0 (road event intelligence; source research)`.
- **robots.txt first** on every host.
  - Rules were read under RFC 9309: longest match wins, and `*` and `$` are
    supported.
  - A 4xx means no rules. A 5xx or an unreachable robots.txt means full
    disallow.
  - Redirects are followed (added after the first `administraciodigital`
    attempt).
- **Pace:** sequential, at least 2.5 s between requests to one host, and
  Crawl-delay honoured: nap.dgt.es, datos.madrid.es, datosabiertos.malaga.eu,
  opendata.vlci.valencia.es and dadesobertes.gva.es at 10 s,
  analisi.transparenciacatalunya.cat at 1 s (so 2.5 s).
- **At most 10 requests a host;** only nap.dgt.es reached 10.
- **Totals:** 93 HTTP requests were sent between 10:48 and 11:21 UTC. Another
  21 were blocked by robots.txt or unreachable robots files and never sent.
- **What was not done:** no login, key, registration, CAPTCHA, proxy or
  browser disguise. No email or form was sent.

| Host | Sent | Statuses |
| --- | --- | --- |
| nap.dgt.es | 10 | all 200 (robots, 7 dataset/search/organisation pages, DT-GV feed); 10–18 s apart |
| datos.gob.es | 8 | 200 ×7, 503 ×1 (one dataset HTML page); the `tráfico` title search body was truncated at 1.2 MB |
| opendata.vlci.valencia.es | 5 | 200 ×5 |
| www.valladolid.es | 4 | 200 ×4 |
| datosabiertos.malaga.eu | 4 | TLS failure ×1, then 200 ×3 |
| www.gencat.cat | 3 | 200 ×3 |
| tramits.gencat.cat | 3 | robots 302, then 200 ×2 |
| administraciodigital.gencat.cat | 3 | robots 302 ×2, robots 200 (`Disallow: /`); no page fetched |
| analisi.transparenciacatalunya.cat | 3 | 200 ×3 |
| www.juntadeandalucia.es | 3 | 200 ×3 |
| dadesobertes.gva.es | 3 | 200 ×3 |
| datos.tenerife.es | 3 | 200 ×3 |
| datos.madrid.es | 3 | 200, 302 (not followed: disallowed target), 200 |
| datos.lorca.es | 3 | robots 404, 200 ×2 |
| github.com | 3 | 200 ×3 (robots, two DGT 3.0 wiki pages) |
| opendata-ajuntament.barcelona.cat | 3 | robots 403, read timeout ×2 |
| analisis.datosabiertos.jcyl.es | 2 | 200 ×2 |
| datosabiertos.jcyl.es | 2 | 200, 302 |
| www.dgt.es | 2 | 200 ×2 |
| www.gijon.es / datos.gijon.es | 2 / 2 | 200 ×2 / 404, 200 |
| abertos.xunta.gal | 2 | 200, 404 |
| www.bilbao.eus | 2 | 403 ×2 |
| servicios.jcyl.es, geoportal.valencia.es, catalegdades.caib.cat | 2 each | connection closed or reset, twice each (robots only) |
| datos.coruna.gal | 1 | robots 200 (`Disallow: /`) |
| opendata.aytosalamanca.es | 1 | robots 503 |
| www.zaragoza.es, datosabiertos.navarra.es, datos.comunidad.madrid, datos.canarias.es, datosabiertos.castillalamancha.es | 1 each | TCP timeout (robots) |
| opendata.aragon.es, datos.cantabria.es | 1 each | DNS failure |

**Other network checks (no HTTP request sent):**
- TCP connect probes to port 443 of about 20 candidate hosts, to tell
  timeouts from refusals.
- One TLS handshake with datosabiertos.malaga.eu to read its certificate
  issuer.
- One DNS query to 8.8.8.8, which timed out.

**Discovery:**
- Web searches (search engine only).
- The datos.gob.es `apidata` catalogue: title searches for "cortes de
  tráfico", "incidencias", "obras", "tráfico" and "carreteras".

**Access-rule notes**
- **nap.dgt.es:** robots.txt has `Disallow: /dataset`. The `/en/dataset/…`,
  `/en/dataset?q=…` and `/en/organization/dgt` pages were read under the same
  literal reading as on 16 and 21 October: the rule covers paths that *begin*
  with `/dataset`. It may be meant to cover the English pages too.
- **opendata-ajuntament.barcelona.cat:** robots.txt 403 was treated as no
  rules, as before.
- **Retries:** at most one retry per unreachable host, and none after a
  second failure.

**Files**
- Request log: `C:\Users\JSANCO~1\AppData\Local\Temp\claude\C--Users-Jsan-Consulting-Desktop-JSAN-Road-Event-Intelligence\1f1e58d5-c7a5-480c-a06f-4cc65e0fa21f\scratchpad\es-research\log.tsv`.
- Samples (outside the repo) are in the same `es-research` folder:
  - `sct_incidenciesGML.xml` and `sct_incidenciesRSS.xml`
  - `malaga_cortes_4326.geojson`
  - `dtgv_content.xml`
  - `tfe_incidencias_2026.json`
  - the licence and dataset pages
  - robots files under `robots\`

## Not verified

- Navarra's fields, counts and update rate. The host was unreachable.
- Valencia city occupation counts and geometry. The geoportal was
  unreachable.
- Castilla y León feed contents.
- Calle 30 incident and works contents.
- Barcelona's *frase* feed: the API timed out today.
- The Generalitat licence page linked from the SCT dataset (robots-blocked),
  and the full text of the Llicència oberta d'ús d'informació – Catalunya.
- Which licence Málaga means (CC BY 4.0 or CC BY-SA 4.0), and Málaga's aviso
  legal.
- Licences of the NAP datasets "Location of cones for sporting events",
  "Connected cones" and "SRTI LOD". Their pages were not opened because of the
  request cap.
- Whether SCT's `data` is the start of the restriction or the time of its last
  update.
- Every host listed as unreachable. The failures look like network filtering
  of the research connection, not refusals by terms.
