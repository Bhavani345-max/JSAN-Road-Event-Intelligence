"""Estonia, Latvia, Poland and Ireland as country entries (4 November 2026).

No source in these four countries passed every check on 4 November 2026
(docs/data-sources/baltics-poland-ireland-sources-2026-11-04.md): each entry is
configured with no official source of its own. No test reaches any service.
"""

import pytest

from connectors.registry import registered_sources
from packages.cities import area_of, get_city, load_cities

# id: (country, timezone, language, a point inside, a point outside)
ENTRIES = {
    "estonia": ("EE", "Europe/Tallinn", "et", (59.437, 24.7536), (56.9496, 24.1052)),  # Tallinn; not Riga
    "latvia": ("LV", "Europe/Riga", "lv", (56.9496, 24.1052), (54.6872, 25.2797)),  # Riga; not Vilnius
    "poland": ("PL", "Europe/Warsaw", "pl", (52.2297, 21.0122), (52.52, 13.405)),  # Warsaw; not Berlin
    "ireland": ("IE", "Europe/Dublin", "en", (53.3498, -6.2603), (51.5072, -0.1276)),  # Dublin; not London
}


@pytest.mark.parametrize("city_id", ENTRIES)
def test_each_is_a_country_entry_with_its_zone_and_language(city_id):
    country, zone, language, inside, outside = ENTRIES[city_id]
    entry = get_city(city_id)
    assert (entry.level, entry.country, entry.timezone, entry.language) == ("country", country, zone, language)
    assert entry.covers(*inside) and not entry.covers(*outside)
    longitude, latitude = entry.map.center
    assert entry.covers(latitude, longitude)
    # English and local names place an article in the country.
    assert entry.name in entry.scope_terms and len(entry.scope_terms) >= 2


@pytest.mark.parametrize("city_id", ENTRIES)
def test_none_has_an_official_source_yet(city_id):
    entry = get_city(city_id)
    assert entry.official_sources == () and entry.gis_sources == ()
    assert area_of(entry)[0] == entry


def test_each_country_has_exactly_one_entry_and_ireland_is_not_the_united_kingdom():
    countries = [city.country for city in load_cities().values() if city.level == "country"]
    assert all(countries.count(code) == 1 for code in ("EE", "LV", "PL", "IE", "GB"))
    ireland = get_city("ireland")
    assert ireland.area_name == "Republic of Ireland"
    assert ireland.covers(51.8985, -8.4756)  # Cork
    # Dublin is in the shared list of other cities' news; for Ireland it is in scope.
    assert "Dublin" in ireland.scope_terms


def test_each_gets_the_news_row_every_entry_gets_and_nothing_is_polled():
    by_city = {}
    for source in registered_sources():
        by_city.setdefault(source.definition.city, []).append(source.definition)
    for city_id in ENTRIES:
        definitions = by_city[city_id]
        assert f"google-news-rss-{city_id}" in {d.source_id for d in definitions}
        # Listed, never fetched: the news row is off by default, and anything else
        # recorded for these countries (needing a key or permission) is not connected.
        assert not any(d.active for d in definitions)
