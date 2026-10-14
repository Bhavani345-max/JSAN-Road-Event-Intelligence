"""Migration 0002 removes demo data from a database that already contains it."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.core.config import BACKEND_DIR, REPO_ROOT
from app.core.database import ALEMBIC_INI, create_db_engine

NOW = "2026-10-02 08:00:00"


def migrate(url: str, revision: str) -> None:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, revision)


def test_upgrade_deletes_demo_events_and_keeps_real_ones(tmp_path):
    url = f"sqlite:///{(tmp_path / 'old.db').as_posix()}"
    migrate(url, "0001")

    engine = create_db_engine(url)
    with engine.begin() as connection:
        for source_id, name, kind in (
            ("rei-demo", "REI demo data set", "MANUAL"),
            ("telangana-today", "Telangana Today", "RSS"),
        ):
            connection.execute(
                text(
                    "INSERT INTO sources (source_id, source_name, source_type, active, created_at, updated_at) "
                    "VALUES (:id, :name, :kind, 1, :now, :now)"
                ),
                {"id": source_id, "name": name, "kind": kind, "now": NOW},
            )
        for event_id, source_id, is_demo in (
            ("DEMO-HYD-001", "rei-demo", 1),
            ("DEMO-HYD-002", "rei-demo", 1),
            ("EVT-REAL00000001", "telangana-today", 0),
        ):
            connection.execute(
                text(
                    "INSERT INTO events (event_id, source_id, title, status, is_demo, version, created_at, updated_at) "
                    "VALUES (:id, :source, 'x', 'VALIDATION_REQUIRED', :demo, 1, :now, :now)"
                ),
                {"id": event_id, "source": source_id, "demo": is_demo, "now": NOW},
            )
            connection.execute(
                text(
                    "INSERT INTO event_versions (event_id, version, status, snapshot, changed_by, created_at) "
                    "VALUES (:id, 1, 'VALIDATION_REQUIRED', '{}', 'test', :now)"
                ),
                {"id": event_id, "now": NOW},
            )
    engine.dispose()

    migrate(url, "head")

    engine = create_db_engine(url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT event_id FROM events")).scalars().all() == [
            "EVT-REAL00000001"
        ]
        assert connection.execute(text("SELECT event_id FROM event_versions")).scalars().all() == [
            "EVT-REAL00000001"
        ]
        assert connection.execute(text("SELECT source_id FROM sources")).scalars().all() == [
            "telangana-today"
        ]
    columns = {column["name"] for column in inspect(engine).get_columns("events")}
    assert "is_demo" not in columns
    source_columns = {column["name"] for column in inspect(engine).get_columns("sources")}
    assert {"source_tier", "organization", "endpoint", "integration_status", "notes"} <= source_columns
    assert "tier" not in source_columns
    engine.dispose()


def test_the_application_no_longer_ships_demo_seed_data():
    assert not (REPO_ROOT / "database" / "seeds").exists()
    for path in (BACKEND_DIR / "app").rglob("*.py"):
        code = Path(path).read_text(encoding="utf-8")
        assert "demo" not in code.lower(), f"{path} still refers to demo data"
    # The located events that remain are test fixtures, under tests/ only.
    assert (BACKEND_DIR / "tests" / "fixtures" / "located_events.json").exists()
