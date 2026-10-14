# HTML connectors

`article.py` reads **one news article of a connected source** from the
structured data (schema.org NewsArticle) its page carries, for articles the
feed no longer has. Used by `python backend/cli/backfill.py <source_id> <url>`.

Not implemented yet: sources that publish only as web pages, such as notices
on an authority's website. Same contract as every connector: implement
`SourceConnector` (`connectors/base.py`) and return `RawSourceRecord`s.
