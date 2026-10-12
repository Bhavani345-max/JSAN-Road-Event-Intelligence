from sqlalchemy.orm import Session

from app.repositories.sources import SourceRepository
from connectors.registry import RegisteredSource


def sync_reference_data(session: Session, sources: tuple[RegisteredSource, ...]) -> None:
    """Startup data: bring the sources table in line with the source registry.

    No events are ever seeded. Every event in the database comes from a
    connected source and its stored evidence.
    """
    SourceRepository(session).sync_registry(source.definition for source in sources)
    session.commit()
