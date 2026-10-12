# API connectors

`serper_news.py` — Google News search through the Serper API: finds Hyderabad
road articles from any publisher and reads each one from its own page. See
`docs/data-sources/google-news-search.md`.

Planned: the TomTom Traffic Incidents API for real-time, unplanned incidents.

A connector here implements the `SourceConnector` protocol
(`connectors/base.py`), returns `RawSourceRecord`s and is listed in
`connectors/registry.py`. API keys are read from environment variables
(see `.env.example`), never written in code.
