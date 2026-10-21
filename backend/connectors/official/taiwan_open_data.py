"""What the Taiwanese city works feeds share (21 October 2026).

Taipei, New Taipei and Taichung publish their road works and traffic
maintenance plans on Taiwan's government open-data platform under the Open
Government Data License, version 1.0 (政府資料開放授權條款－第1版,
https://data.gov.tw/license), which allows use "for any purpose, including
but not limited to making all kinds of Derivative Works either as products
or services" provided the attribution in its Exhibit is given (read 21
October 2026; docs/data-sources/taiwan-connectors-2026-10-21.md).

The three feeds write dates in the Republic of China (民國) calendar or in
ISO form, give local times (Asia/Taipei) or none, and name the people in
charge of each site with their mobile numbers. Those people's names and
numbers are not REI's to keep: each connector drops them before a record is
stored, and keeps the organisations' names.
"""

import re
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from packages.source_models import CommercialUse, CostCategory, SourceClass, TermsStatus

from .feature_feed import clean

TAIPEI_TIME = ZoneInfo("Asia/Taipei")
LICENCE = "Open Government Data License, version 1.0 (政府資料開放授權條款－第1版), https://data.gov.tw/license"
LICENCE_URL = "https://data.gov.tw/license"
# The open-data platform's terms, common to the three feeds' definitions.
COMMON_TERMS = dict(
    source_class=SourceClass.GOVERNMENT_OPEN_DATA,
    cost_category=CostCategory.FREE_PUBLIC,
    terms_status=TermsStatus.PERMITS_TESTING,
    licence=LICENCE,
    commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
    language="zh",
)
# The Republic of China calendar counts years from 1912: 民國 115 is 2026.
ROC_YEAR_OFFSET = 1911


def attribution(provider: str, dataset: str, year: int = 2026) -> str:
    """The attribution the licence's Exhibit asks for, in its own words."""
    return (
        f"{provider} {year} {dataset}。此開放資料依政府資料開放授權條款 (Open Government Data License) "
        f"進行公眾釋出，使用者於遵守本條款各項規定之前提下，得利用之。政府資料開放授權條款：{LICENCE_URL}"
    )


_ROC_SLASHED = re.compile(r"^(\d{2,3})/(\d{1,2})/(\d{1,2})$")
_ROC_DIGITS = re.compile(r"^(\d{2,3})(\d{2})(\d{2})$")


def roc_date(value: Any) -> date | None:
    """A date written in the ROC calendar: "115/10/21", "99/08/17" or "1151021"."""
    text = clean(value)
    match = _ROC_SLASHED.match(text) or _ROC_DIGITS.match(text)
    if not match:
        return None
    year, month, day = (int(part) for part in match.groups())
    try:
        return date(year + ROC_YEAR_OFFSET, month, day)
    except ValueError:
        return None


def at_hour(day: date, hour: int) -> datetime:
    """`day` at a stated hour, Taipei time; 24 is the end of the day (REI: 23:59:59)."""
    if hour == 24:
        return datetime.combine(day, time(23, 59, 59), tzinfo=TAIPEI_TIME)
    return datetime.combine(day, time(hour), tzinfo=TAIPEI_TIME)


# Words that end or mark an organisation's name in Chinese: a company, a
# works contractor, a public body, a school, a temple. A name with none of
# them (two to four characters, "彭秀枝") is a person's and is not kept.
_ORGANISATION = re.compile(
    # Anywhere in the name.
    r"有限公司|股份|公司|財團法人|社團法人|祭祀公業|政府|公所|委員會|協會|基金會|教會|企業|實業|事業|工業|"
    r"工程|營造|建設|廣告|科技|管理處|營業處|服務所|國民之家|商場|廣場|百貨|尚未發包"
    # At its end.
    r"|(局|處|署|院|所|部|隊|中心|學校|大學|中學|小學|國小|國中|高中|幼兒園|醫院|診所|學會|工會|商會|農會|"
    r"漁會|總會|宮|廟|寺|銀行|商行|車行|工程行|企業行|傢俱行|家具行|五金行|材料行|水電行|電器行|合作社|社|"
    r"店|廠|館|鋼構|工坊|工作室|園藝|水電|電機|電氣|機電|包工業)$"
)
_TRAILING_NOTE = re.compile(r"\s*[（(][^（()）]*[）)]$")


def organisation(value: Any) -> str | None:
    """The name, when it is an organisation's; None for a person's name or nothing."""
    name = clean(value)
    if not name:
        return None
    return name if _ORGANISATION.search(_TRAILING_NOTE.sub("", name)) else None


def without(item: dict[str, Any], fields: frozenset[str]) -> dict[str, Any]:
    """The record without the named fields (the people in charge and their numbers)."""
    return {key: value for key, value in item.items() if key not in fields}
