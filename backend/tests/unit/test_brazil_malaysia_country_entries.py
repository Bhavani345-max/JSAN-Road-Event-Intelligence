"""Brazil and Malaysia: country entries with no source yet (4 November 2026).

Researched live on 4 November 2026 (docs/data-sources/brazil-malaysia-sources-2026-11-04.md):
no official feed of either country is both keyless and licensed for REI's
commercial reuse with current events, locations and start times, so neither
entry lists a source. Each covers its whole territory and its own time zone
and language.
"""

import pytest

from packages.cities import cities_within, get_city, load_cities

# Well-known places that must fall inside each country's area (latitude, longitude).
INSIDE = {
    "brazil": {
        "São Paulo": (-23.55, -46.63),
        "Rio de Janeiro": (-22.91, -43.17),
        "Manaus": (-3.12, -60.02),
        "Chuí": (-33.69, -53.46),
        "Cruzeiro do Sul (Acre)": (-7.63, -72.67),
        "Fernando de Noronha": (-3.85, -32.42),
    },
    "malaysia": {
        "Kuala Lumpur": (3.14, 101.69),
        "George Town": (5.41, 100.33),
        "Johor Bahru": (1.46, 103.76),
        "Kuching": (1.55, 110.36),
        "Kota Kinabalu": (5.98, 116.07),
        "Tawau": (4.24, 117.89),
    },
}
OUTSIDE = {
    "brazil": {"Buenos Aires": (-34.60, -58.38), "Lima": (-12.05, -77.04)},
    "malaysia": {"Medan": (3.59, 98.67), "Manila": (14.60, 120.98)},
}


@pytest.mark.parametrize(
    "city_id, country, timezone, language",
    [("brazil", "BR", "America/Sao_Paulo", "pt"), ("malaysia", "MY", "Asia/Kuala_Lumpur", "ms")],
)
def test_each_is_the_single_country_entry_of_its_country(city_id, country, timezone, language):
    entry = get_city(city_id)
    assert (entry.level, entry.country, entry.timezone, entry.language) == ("country", country, timezone, language)
    assert [c.id for c in load_cities().values() if c.level == "country" and c.country == country] == [city_id]
    assert cities_within(entry) == ()
    assert entry.official_sources == () and entry.gis_sources == ()


@pytest.mark.parametrize("city_id", ["brazil", "malaysia"])
def test_the_area_covers_the_country_and_not_its_neighbours(city_id):
    entry = get_city(city_id)
    for place, (latitude, longitude) in INSIDE[city_id].items():
        assert entry.covers(latitude, longitude), place
    for place, (latitude, longitude) in OUTSIDE[city_id].items():
        assert not entry.covers(latitude, longitude), place
    longitude, latitude = entry.map.center
    assert entry.covers(latitude, longitude)


def test_scope_terms_name_the_country_in_english_and_the_local_language():
    assert get_city("brazil").scope_terms == ("Brazil", "Brasil")
    assert get_city("malaysia").scope_terms == ("Malaysia",)
