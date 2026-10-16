from collections import Counter
from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Event, Source, SourceArtifact
from app.schemas.source import SourceOut
from packages.common.time import utc_now
from packages.source_models import SourceDefinition


class SourceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Source]:
        return list(self.session.scalars(select(Source).order_by(Source.source_name)))

    def get(self, source_id: str) -> Source | None:
        return self.session.get(Source, source_id)

    def to_out(self, source: Source, event_counts: Counter | None = None) -> SourceOut:
        """The source's API form. `event_counts`: its row of
        EventRepository.tally(by="source"); counted here when not given."""
        from app.repositories.events import EventRepository
        from app.services.source_status import describe

        if event_counts is None:
            event_counts = EventRepository(self.session).tally(by="source").get(source.source_id)
        out = SourceOut.model_validate(source)
        out.artifact_count = self._count(SourceArtifact, source.source_id)
        out.event_count = self._count(Event, source.source_id)
        for name, value in describe(source, event_counts).items():
            setattr(out, name, value)
        return out

    def _count(self, model: type[SourceArtifact] | type[Event], source_id: str) -> int:
        return (
            self.session.scalar(
                select(func.count()).select_from(model).where(model.source_id == source_id)
            )
            or 0
        )

    def sync_registry(self, definitions: Iterable[SourceDefinition]) -> None:
        """Make the sources table match the code registry.

        The registry owns what a source *is*; the table adds polling state.
        """
        now = utc_now()
        for definition in definitions:
            values = definition.model_dump(mode="json")
            source = self.get(definition.source_id)
            if source is None:
                self.session.add(Source(**values, created_at=now, updated_at=now))
                continue
            changed = False
            for name, value in values.items():
                if getattr(source, name) != value:
                    setattr(source, name, value)
                    changed = True
            if changed:
                source.updated_at = now
