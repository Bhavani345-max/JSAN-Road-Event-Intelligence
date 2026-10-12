from typing import Protocol

from packages.source_models import RawSourceRecord, SourceDefinition


class ConnectorError(Exception):
    """The source could not be fetched or its response could not be read."""


class SourceConnector(Protocol):
    """What the ingestion service needs from any connector, whatever its type."""

    source: SourceDefinition

    def fetch(self) -> list[RawSourceRecord]:
        """Fetch the source's current items. Raises ConnectorError on failure."""
        ...
