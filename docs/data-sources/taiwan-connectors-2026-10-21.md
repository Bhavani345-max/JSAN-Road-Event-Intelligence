# Taiwan connectors: Taipei, New Taipei, Taichung (21 October 2026)

Three official works feeds, connected (run by hand until scheduled), from the
candidates in [Asia, Middle East and Africa sources](asia-mea-official-road-sources-2026-10-16.md).
Not yet in the registry: the snippet at the end adds them. Nothing was written
to any database; no commit was made.

| Source id | City | Feed | Read live | Kept | Located | Start | End |
|---|---|---|---|---|---|---|---|
| `taipei-todaywork` | Taipei | 臺北市今日施工資訊 (works reported today) | 869 | 850 | 850 | 850 | 850 |
| `new-taipei-road-excavation` | New Taipei | 新北市政府道路挖掘資訊 (excavation permits) | 2,140 | 579 | 579 | 579 | 579 |
| `taichung-traffic-maintenance-plans` | Taichung | 臺中市交通維持計畫資料集 (traffic maintenance plans) | 516 | 480 | 480 | 480 | 480 |

Live dry run 21 October 2026, 11:23 UTC (19:23 Taipei), one `fetch()` each.
"Read" = records the connector took from the file (after the exclusions
below); "Kept" = in effect now or starting within the run window; every kept
record lies inside its city's area.

## Licence (re-read live, 21 October 2026)

All three are licence code 1 on the national catalogue: the dataset pages
https://data.gov.tw/dataset/145614, https://data.gov.tw/dataset/122989 and
https://data.gov.tw/dataset/84900 each state 授權方式 "政府資料開放授權條款-第1版"
and 計費方式 "免費" (fetched 11:01 UTC). Providers stated there: 臺北市政府工務局,
新北市政府工務局, 臺中市政府交通局.

From https://data.gov.tw/license (fetched 11:00 UTC), Open Government Data
License, version 1.0:

> 2.1. The Data Providing Organization grants User a perpetual, worldwide,
> non-exclusive, irrevocable, royalty-free copyright license to reproduce,
> distribute, publicly transmit, publicly broadcast, publicly recite, publicly
> present, publicly perform, compile, adapt to the Open Data provided for any
> purpose, including but not limited to making all kinds of Derivative Works
> either as products or services.

> 3.2. When User makes use of the Open Data and its Derivative Work, he/she
> must make an explicit notice of statement as attribution requested in the
> Exhibit below by the Data Providing Organization. If User fails to comply
> with the attribution requirement, the rights granted under this License
> shall be deemed to have been void ab initio.

Chinese text, 二、(一): "各機關所提供之開放資料，授權使用者不限目的、時間及地域、非專屬、不可撤回、免授權金進行利用".
Exhibit (附件：顯名聲明): "提供機關／單位 [年份] [開放資料釋出名稱與版本號] 此開放資料依政府資料開放授權條款
(Open Government Data License) 進行公眾釋出，使用者於遵守本條款各項規定之前提下，得利用之。政府資料開放授權條款：
https://data.gov.tw/license". Each source's `attribution` is this statement
with its provider, 2026 and the dataset's name. Section 4.2: compatible with
CC BY 4.0. Section 5: a provider may stop supplying data that may infringe
privacy. Verdict: commercial use permitted with attribution
(`PERMITTED_WITH_ATTRIBUTION`, `PERMITS_TESTING`, not a legal review).

## robots.txt (21 October 2026)

- `tpnco.blob.core.windows.net`: HTTP 400 XML error (Azure Blob, no rules).
- `data.ntpc.gov.tw`: HTTP 200 WAF page "Request Rejected" (no rules); the CSV itself was served.
- `newdatacenter.taichung.gov.tw`: HTTP 200, the site's JavaScript app page (no rules).
- `data.gov.tw`: HTTP 500 (no rules).

As in the 16 October research, treated as "no rules". Requests: 3 to each
data host (robots.txt, one sample, one dry run), 8 to data.gov.tw (robots,
licence page, 3 catalogue API entries, 3 dataset pages), 3 s apart, User-Agent
`JSAN-REI/1.0 (road event intelligence; RSS reader)` (Settings.http_user_agent).
`datacenter.taichung.gov.tw` (the Taichung API documentation) did not resolve
in DNS; nothing was received from it.

## How each feed is read

**Taipei** (`connectors/official/taipei_works.py`, GeoJSON in TWD97 / TM2,
refreshed every 10 minutes, polled hourly). One record per site
(`Ac_no`-`sno`). Geometry: the works area (`Positions`, MultiPolygon for road
maintenance, MultiLineString for excavation) converted to WGS 84; its point is
the site's location. Approved dates `Cb_Da`/`Ce_Da` (ROC calendar) as whole
days in Asia/Taipei; the hours text `Co_Ti` is kept in the stated period, not
read as a time. All report kinds (`AppMode` 0 施工通報, 3 銑鋪通報, 4 搶修通報,
5 道路維護通報, 6 人手孔施工通報, B 建案公設復舊, from the catalogue's notes)
are ROAD_WORKS. `IsBlock` 是 and `PlanB` (建議改道) are kept as the location's
closure words ("影響通行（建議改道）"); no closure type is claimed.
Not taken: sites whose only works item is 人行道維護 (pavement maintenance)
and that do not affect traffic (`IsBlock` 否; 246 on 21 October), following
the Tokushima rule that a pavement restriction is not road traffic; and the
feed's own test entries (address "全市APP測試", approval 99015156, 25 entries
drawn from Taipei to Taichung). Sites past their approved end (some state a
reason for overrunning in `DType`) are not kept: no end is extended.

**New Taipei** (`connectors/official/new_taipei_excavation.py`, CSV with
TWD97 points, daily, polled four times a day). One record per permit
(`caseid`), a point each, ROAD_WORKS (a permit does not say whether traffic is
closed). Dates `casestartdate_yyymmddroc`/`caseenddate_yyymmddroc` as whole
days; only when `workperiod` is a single continuous stretch with stated hours
on the same days ("連續性施工，115年07月01日09時起116年07月27日16時止，共392日")
are those hours used. `workperiod` is kept in the stated period.

**Taichung** (`connectors/official/taichung_traffic_plans.py`, JSON with
WGS 84 points in text, daily, polled four times a day). The feed lists a plan
worked on several days once a day; rows of one plan at one site with the same
hours on following (or overlapping) days are read as one period, from the
start hour on the first day to the end hour on the last (`StartTime`/`EndTime`,
24 = end of day; 0 to 24 = whole days). Exact duplicate rows count once.
One point is a Point; several points are read as the line the plan draws, in
the order listed, or as an area when the last point repeats the first (15 on
21 October). Rows without a point (312 of 1,137) are not taken. No event type
is given: the `Type` codes (1, 2, 3, 4, 6) are not explained in the catalogue
and the API documentation host could not be reached. Record id:
`<Id>:<site hash>:<last day>`.

**Personal data.** Dropped before storing: Taipei `Tc_Ma`, `Tc_Ma3` (masked
names) and `Tc_Tl`, `Tc_Tl3` (mobile numbers); New Taipei `construction_man`,
`supervise_man` and all eight phone fields, `supervise`/`constructionunit`
when they name a person rather than an organisation, `remark` when it holds a
phone number or contact person; Taichung `Contact`, `Telephone`, and `Company`
when it is an individual's name (about 90 names on 21 October). Organisation
names are kept. The test fixtures carry placeholders (王小明, 0900000000) in
place of the real values.

**Coordinates.** `connectors/official/twd97.py` converts TWD97 / TM2 zone 121
(EPSG:3826: GRS 80, central meridian 121° E, scale 0.9999, false easting
250,000 m) to longitude and latitude with Krüger's series (Karney 2011), pure
Python. `tests/unit/test_twd97.py` checks it against published points, all
within 1 cm: control points N001 七星山, N364 劍潭山, N324 紅淡山 (control-point
list on https://wiki.osgeo.org/wiki/Taiwan_datums/Test_points), 頂山 S567
TWD97[2010] (Ministry of National Defense paper 「座標系統轉換與格式換算之研究」,
pp. 60-63) and PROJ's example on https://wiki.osgeo.org/wiki/Taiwan_datums.

## Cities

`taiwan.json` (country entry, TW, Asia/Taipei, zh) and, within it,
`taipei.json`, `new-taipei.json`, `taichung.json`, each listing its source in
`official_sources`. Scope terms in English and Chinese (臺北/台北, 新北, 臺中/台中).

## Registry snippet (not applied)

In `backend/connectors/registry.py`, with the other official imports:

```python
from .official.taipei_works import TaipeiTodayWorksConnector, taipei_source
from .official.new_taipei_excavation import NewTaipeiRoadExcavationConnector, new_taipei_source
from .official.taichung_traffic_plans import TaichungTrafficPlansConnector, taichung_source
```

and in `_official_sources`, inside the `feature_feeds` tuple:

```python
            # Taiwan: Taipei, New Taipei and Taichung (21 October 2026).
            (taipei_source, TaipeiTodayWorksConnector),
            (new_taipei_source, NewTaipeiRoadExcavationConnector),
            (taichung_source, TaichungTrafficPlansConnector),
```

## Not built

- **Taiwan TDX** (national road and freeway news): needs a registered key.
- **Police Broadcasting Service live reports** (data.gov.tw 15221): host
  unreachable on 16 October; not retried.
- **New Taipei 10-minute works feed** (data.gov.tw 177913): not examined.
- **Taichung `Type` meanings**: not published in what could be read; an
  event type for Taichung needs them (ask 臺中市政府交通局, or read
  https://datacenter.taichung.gov.tw/swagger/yaml/387290000H from a network
  where it resolves).
