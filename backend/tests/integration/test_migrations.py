from sqlalchemy import inspect

from app.core.database import create_db_engine, run_migrations
from app.models import Base


def test_migrations_create_the_same_schema_as_the_models(tmp_path):
    url = f"sqlite:///{(tmp_path / 'migrated.db').as_posix()}"
    run_migrations(url)
    # Running again must be a no-op.
    run_migrations(url)

    engine = create_db_engine(url)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names()) - {"alembic_version"}
    assert tables == {
        "sources", "source_artifacts", "events", "event_versions",
        # Added by migration 0004 (6 October 2026).
        "source_artifact_revisions",
        # Added by migration 0005 (6 October 2026).
        "event_merge_candidates",
        # Added by migration 0006 (6 October 2026).
        "junction_references",
        # Added by migration 0007 (14 October 2026): reviewer sign-in.
        "users", "auth_sessions",
    }  # fmt: skip

    for table in Base.metadata.sorted_tables:
        migrated = {column["name"]: column for column in inspector.get_columns(table.name)}
        assert set(migrated) == {column.name for column in table.columns}, table.name
        for column in table.columns:
            if not column.primary_key:
                assert migrated[column.name]["nullable"] == column.nullable, (
                    f"{table.name}.{column.name}"
                )

    unique = {
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("source_artifacts")
    }
    assert ("source_id", "external_id") in unique
    engine.dispose()
