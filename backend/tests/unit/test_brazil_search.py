"""Brazil: Google News search in Portuguese for nine cities, each located with its
own place list (decision 0057).

No network: Serper and the publishers' pages are driven through httpx.MockTransport.
"""

import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from connectors.api.serper_news import (
    SerperNewsConnector,
    parse_result_date,
    search_language,
    searched_cities,
    serper_news_source,
    source_id_for,
)
from connectors.registry import registered_sources
from packages.cities import get_city
from packages.source_models import IntegrationStatus
from services.geo_resolution import resolver_for
from services.geo_resolution.names import name_tokens, normalise_name

BRAZIL_CITIES = (
    "sao-paulo", "rio-de-janeiro", "brasilia", "belo-horizonte", "curitiba",
    "porto-alegre", "salvador", "recife", "fortaleza",
)
SAO_PAULO = get_city("sao-paulo")
NOW = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)


def test_brazils_cities_are_searched_by_the_users_choice_and_south_africa_is_not():
    searched = {city.id for city in searched_cities()}
    assert set(BRAZIL_CITIES) <= searched
    # The country entry has no search or place list of its own: its cities have them.
    brazil = get_city("brazil")
    assert brazil.level == "country" and not brazil.gazetteer and "brazil" not in searched
    # South Africa has a place list and searches too, but nobody chose to spend credits on it.
    assert "south-africa" not in searched
    for city_id in BRAZIL_CITIES:
        city = get_city(city_id)
        assert (city.country, city.level, city.language) == ("BR", "city", "pt")
        assert city.gazetteer == f"{city_id}_places.json" and city.discovery.serper_search
        longitude, latitude = city.map.center
        assert brazil.covers(latitude, longitude)
        # Free-plan Serper refuses quoted phrases mixed with operators: none is used.
        assert len(city.discovery.queries) == 1 and '"' not in city.discovery.queries[0]
        assert city.name in city.discovery.queries[0]


def test_each_brazil_search_is_registered_on_the_key_in_portuguese():
    with_key = {s.definition.source_id: s for s in registered_sources("k")}
    without = {s.definition.source_id: s for s in registered_sources()}
    for city_id in BRAZIL_CITIES:
        source = with_key[source_id_for(city_id)]
        assert source.definition.source_id == f"google-news-serper-{city_id}"
        assert source.definition.integration_status is IntegrationStatus.CONNECTED
        assert source.definition.country == "BR" and source.definition.city == city_id
        assert source.definition.language == "pt"
        assert isinstance(source.create_connector("ua"), SerperNewsConnector)
        assert without[source_id_for(city_id)].definition.integration_status is IntegrationStatus.REQUIRES_ACCESS
    # The Indian cities' searches stay in English.
    assert with_key[source_id_for("delhi")].definition.language == "en"
    assert search_language(SAO_PAULO) == "pt-br" and search_language(get_city("delhi")) == "en"


RESULTS = [
    {"title": "CET anuncia interdição na Avenida Paulista para evento no domingo",
     "link": "https://g1.globo.com/sp/sao-paulo/noticia/2026/11/04/interdicao-paulista.ghtml",
     "snippet": "Trânsito será bloqueado entre a Rua da Consolação e a Praça Oswaldo Cruz.",
     "date": "há 1 dia", "source": "g1"},
    {"title": "Obras interditam faixa da Linha Amarela até sexta-feira",
     "link": "https://odia.ig.com.br/rio-de-janeiro/2026/11/linha-amarela.html",
     "snippet": "Interdição no sentido Barra.", "date": "há 5 horas", "source": "O Dia"},
    # Another Brazilian city's headline: left out of São Paulo's search.
    {"title": "Rio de Janeiro: CET-Rio interdita pistas do Aterro no domingo",
     "link": "https://g1.globo.com/rj/rio-de-janeiro/noticia/2026/11/04/aterro.ghtml",
     "snippet": "Esquema especial de trânsito em SP e no Rio.", "date": "há 1 dia", "source": "g1"},
    # Another country's headline: left out.
    {"title": "Lisboa: obras cortam trânsito na Avenida da Liberdade",
     "link": "https://www.publico.pt/2026/11/04/lisboa/obras", "snippet": "Câmara de Lisboa.",
     "date": "há 1 dia", "source": "Público"},
    # Nothing naming a Brazilian place: left out.
    {"title": "Interdição de estrada após temporal", "link": "https://news.example.com/estrada",
     "snippet": "Chuva forte.", "date": "há 2 dias", "source": "Example"},
]  # fmt: skip


def brazil_search():
    calls = {"bodies": []}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "google.serper.dev":
            calls["bodies"].append(json.loads(request.content))
            return httpx.Response(200, json={"news": RESULTS})
        return httpx.Response(200, text="<html><body>No structured data.</body></html>")

    source = serper_news_source(connected=True, city_id="sao-paulo")
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return SerperNewsConnector.for_city(source, SAO_PAULO, "test-key", "ua", client=client), calls


def test_the_sao_paulo_search_asks_google_in_brazilian_portuguese_and_keeps_its_own_results():
    connector, calls = brazil_search()
    records = connector.fetch()
    assert [body["q"] for body in calls["bodies"]] == list(SAO_PAULO.discovery.queries)
    assert {(body["gl"], body["hl"]) for body in calls["bodies"]} == {("br", "pt-br")}
    # Rio's articles (one naming no São Paulo place, one headlined Rio de Janeiro),
    # Lisbon's and an unplaced one are left out.
    assert [record.url for record in records] == [RESULTS[0]["link"]]
    assert {record.source_id for record in records} == {"google-news-serper-sao-paulo"}


@pytest.mark.parametrize(
    "text, expected",
    [
        ("há 3 dias", NOW - timedelta(days=3)),
        ("há 1 hora", NOW - timedelta(hours=1)),
        ("Há 2 semanas", NOW - timedelta(weeks=2)),
        ("há 1 mês", NOW - timedelta(days=30)),
        ("há 45 minutos", NOW - timedelta(minutes=45)),
        ("4 de nov. de 2026", datetime(2026, 11, 4, tzinfo=timezone.utc)),
        ("12 de março de 2026", datetime(2026, 3, 12, tzinfo=timezone.utc)),
        ("31 de fev. de 2026", None),
    ],
)
def test_portuguese_result_dates_are_read(text, expected):
    assert parse_result_date(text, now=NOW) == expected


def test_accents_and_portuguese_abbreviations_meet_the_maps_wording():
    assert normalise_name("São Paulo") == normalise_name("Sao Paulo") == "sao paulo"
    assert normalise_name("Av. Paulista") == normalise_name("Avenida Paulista") == "avenida paulista"
    assert normalise_name("Pça. da Sé") == normalise_name("Praça da Sé") == "praca da se"
    assert normalise_name("Rod. Anhanguera") == "rodovia anhanguera"
    # Positions stay those of the original text.
    text = "Interdição na Praça da Sé"
    assert [(token, text[start:start + len(token)]) for token, start in name_tokens(text)][-3:] == [
        ("praca", "Praça"), ("da", "da"), ("se", "Sé"),
    ]
    # Names without accents are read as before.
    assert normalise_name("Khajaguda Jn") == "khajaguda junction"
    assert normalise_name("Rajpath Marg") == "rajpath marg"


@pytest.mark.parametrize(
    "city_id, name, near",
    [
        ("sao-paulo", "Praça da Sé", (-23.55, -46.63)),
        ("sao-paulo", "Praca da Se", (-23.55, -46.63)),
        ("sao-paulo", "Pinheiros", (-23.56, -46.69)),
        ("rio-de-janeiro", "Tijuca", (-22.92, -43.23)),
        ("belo-horizonte", "Pampulha", (-19.86, -43.97)),
        # One name, two cities: each city's list has its own.
        ("recife", "Boa Viagem", (-8.12, -34.90)),
        ("salvador", "Boa Viagem", (-12.93, -38.51)),
    ],
)
def test_each_citys_place_list_locates_its_places_from_openstreetmap(city_id, name, near):
    match = resolver_for(get_city(city_id)).lookup(name, found_in=f"interdição em {name}")
    assert match is not None and match.has_position
    assert abs(match.latitude - near[0]) < 0.03 and abs(match.longitude - near[1]) < 0.03


def test_a_long_avenue_is_known_but_not_pinned_to_one_spot():
    # Avenida Paulista runs about 2.8 km: an article naming only it is not located
    # at a point of REI's choosing (the rule every place list follows).
    match = resolver_for(SAO_PAULO).lookup("Av. Paulista", found_in="interdição na Av. Paulista")
    assert match is not None and match.name == "Avenida Paulista" and not match.has_position
