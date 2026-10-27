"""How REI opens its database (decision 0042)."""

from app.core import database


def test_postgresql_sessions_run_without_parallel_workers(monkeypatch):
    # Production's PostgreSQL failed parallel plans for lack of shared memory
    # (/dev/shm) on 26-27 October 2026; every REI session, migrations included,
    # now plans without parallel workers.
    made = {}
    monkeypatch.setattr(database, "create_engine", lambda url, **options: made.update(options))
    database.create_db_engine("postgresql+psycopg://rei:secret@db.internal:5432/rei")
    assert made["connect_args"] == {
        "options": "-c max_parallel_workers_per_gather=0 -c max_parallel_maintenance_workers=0"
    }
    assert made["pool_pre_ping"] is True


def test_sqlite_is_opened_as_before():
    engine = database.create_db_engine("sqlite://")
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
