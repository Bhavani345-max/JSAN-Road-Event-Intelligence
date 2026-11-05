# 0057 — Brazil: Google News search in Portuguese

**Status:** 5 November 2026. Code local, tested, for the user to review. Works in
production only once the Serper credits are topped up (all Serper searches have
failed with "Not enough credits" since 22 October).

## Context

The user, 5 November 2026: "for brazil there is no events and no sources are
working properly, check that also and make it work".

Production had no Brazil source at all. The 4 November research
(`docs/data-sources/brazil-malaysia-sources-2026-11-04.md`) found no official feed
REI may use, and the re-check of 5 November found the same:

- Rio's COR occurrences: BigQuery only, CC BY-ND 3.0 (no adaptations).
- São Paulo: the city's CKAN disallows all robots; `capital.sp.gov.br` does not
  answer robots.txt (read as disallow); the state's terms page
  (`cms.sp.gov.br/cms/termo-uso`) answers automated clients with an empty 202.
- Federal and many state hosts refuse foreign networks.
- EBC's news agencies (Agência Brasil, Agência Gov): Agência Brasil's service page
  says "A reprodução é permitida, desde que a Agência Brasil seja citada nos
  créditos do conteúdo", but EBC's terms of use
  (`ebc.com.br/termos-de-uso-e-condicoes-gerais-do-portal-da-ebc`, clause 1(b)) say
  "O Usuário deverá utilizar o Portal apenas para finalidades de uso pessoal, sem
  intuito comercial ou lucrativo." Not connected (the precedent is Mid-day, decision 0033).
  Agência Brasília and Agência Minas: "Todos os direitos reservados".
- TomTom's live layer (decision 0054) already shows Brazil's live closures on the map
  (106 in central São Paulo, 8 in central Rio on 5 November), never stored.

Asked which route to take, the user chose **Serper search for Brazil** (5 November 2026).

## Decision

- **Brazil is a country entry with nine city entries** (`sao-paulo`, `rio-de-janeiro`,
  `brasilia`, `belo-horizonte`, `curitiba`, `porto-alegre`, `salvador`, `recife`,
  `fortaleza`), like India: one country-wide place list did not work, because a
  name used in several metros ("Boa Viagem" in Recife, Salvador and Niterói;
  "Copacabana") is then "not one spot" and locates nothing.
- **Each city is searched on Google News through Serper** as
  `google-news-serper-<city>` (decision 0037's search): one search each
  ("São Paulo interdição OR bloqueio OR desvio trânsito" …), of the past week, once
  a day, up to 100 results: 18 Serper credits a day for the nine. Asked for
  Brazilian results in Brazilian Portuguese (`gl=br`, `hl=pt-br`); the Indian
  searches stay in English. Article pages are read as for the Indian cities (the
  user's decision of 19 October 2026), except publishers whose terms forbid
  automated access or that the user removed.
- **Opt-in per entry**: `discovery.serper_search` in the city file. Only Brazil's
  cities set it; South Africa, which also has a place list and searches, is not
  searched.
- **Place lists** (`<city>_places.json`, 3,000–17,600 located names each):
  OpenStreetMap (ODbL), one Overpass download of eleven boxes over the nine metro
  areas (São Paulo and Rio in two each), split by each city's box. Names with
  accents are now kept (the builder used to drop every non-ASCII name, which
  dropped "Praça da Sé"); names in other scripts still are. A long road
  (Avenida Paulista, Marginal Tietê) stays a known name without a position, the
  rule of every place list: an event naming only it is not pinned to a point.
- **Scope**: a result is kept only when its headline, snippet or link names the
  city, its roads, its traffic agency or its state (`SP`, `RJ` … as whole words, so
  G1's `/sp/` links count); a headline naming another of the nine cities or
  Portugal, Lisbon, Angola, Mozambique or El Salvador (and not the city) is dropped.
  São Paulo's agency is matched as "CET-SP", not "CET", which "CET-Rio" contains.
- **Portuguese in REI's matching** (`services/geo_resolution/names.py`): accents
  are dropped before matching, one character for one, so positions stay those of
  the original text ("São Paulo" = "Sao Paulo", "Praça da Sé" = "praca da se");
  the press's abbreviations "Av.", "Estr.", "Rod.", "Pça.", "Vd." read as Avenida,
  Estrada, Rodovia, Praça, Viaduto. No existing place list has an accented name or
  any of these words (checked: 0 of 59,181; "marg", Hindi for road, is left alone).
- **Portuguese result dates**: "há 3 dias", "há 1 mês", "4 de nov. de 2026".
- The AI reading already reads every stored news article, whatever the keyword
  rules say, and the model reads Portuguese; its places are located with the Brazil
  place list and its dates are checked against the article's own wording.

## What the user must do

Top up Serper credits (serper.dev; the same key serves India's eight searches,
also failing). Then the nine Brazil searches run on their own once a day.

## Verified

`tests/unit/test_brazil_search.py`: the nine cities searched, the country entry and
South Africa not; each registered on the key in Portuguese, `REQUIRES_ACCESS`
without it; requests carry `gl=br`, `hl=pt-br`; São Paulo's search keeps its own
result and drops Rio's (also one headlined "Rio de Janeiro" with "CET-Rio"),
Lisbon's and an unplaced one; Portuguese dates; accents and abbreviations;
positions kept; each list locates its own places (Praça da Sé with and without
accents, Pinheiros, Tijuca, Pampulha, Boa Viagem in Recife and in Salvador);
Avenida Paulista known but not located. The searches themselves could not be
tried: Serper answers "Not enough credits".
