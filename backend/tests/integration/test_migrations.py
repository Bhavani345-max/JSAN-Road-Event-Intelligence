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
        # Added by migration 0009 (28 October 2026): account recovery.
        "recovery_codes", "security_events",
        # Added by migration 0010 (28 October 2026): registration and reset links.
        "email_tokens",
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


def test_upgrading_keeps_every_existing_account_and_its_access(tmp_path):
    """Migrations 0009 and 0010 (decisions 0044, 0045) only add: an account and its
    open session from before are untouched, and the account is active."""
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text

    from app.core.database import ALEMBIC_INI

    url = f"sqlite:///{(tmp_path / 'upgraded.db').as_posix()}"
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "0008")
    engine = create_db_engine(url)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO users (user_id, email, display_name, password_hash, role, is_active, created_at, updated_at) "
            "VALUES ('u1', 'admin@example.com', 'Admin', 'pbkdf2_sha256$1$a$b', 'admin', 1, '2026-10-01', '2026-10-01'), "
            "('u2', 'user@example.com', 'User', 'pbkdf2_sha256$1$c$d', 'user', 1, '2026-10-01', '2026-10-01')"
        ))  # fmt: skip
        connection.execute(text(
            "INSERT INTO auth_sessions (token_hash, user_id, created_at, expires_at) VALUES ('h1', 'u1', '2026-10-01', '2099-01-01')"
        ))
    engine.dispose()

    run_migrations(url)

    engine = create_db_engine(url)
    with engine.connect() as connection:
        users = connection.execute(text(
            "SELECT user_id, email, password_hash, role, is_active, status, must_change_password, email_verified_at "
            "FROM users ORDER BY user_id"
        )).all()  # fmt: skip
        sessions = connection.execute(text("SELECT token_hash, user_id FROM auth_sessions")).all()
    engine.dispose()
    assert [tuple(row) for row in users] == [
        ("u1", "admin@example.com", "pbkdf2_sha256$1$a$b", "admin", 1, "active", 0, None),
        ("u2", "user@example.com", "pbkdf2_sha256$1$c$d", "user", 1, "active", 0, None),
    ]
    assert [tuple(row) for row in sessions] == [("h1", "u1")]
    # And back: going down to 0008 keeps them too (no table is rebuilt either way).
    command.downgrade(config, "0008")
    engine = create_db_engine(url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM users")).scalar() == 2
        assert connection.execute(text("SELECT token_hash FROM auth_sessions")).scalar() == "h1"
    engine.dispose()
