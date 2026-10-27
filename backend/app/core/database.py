from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import REPO_ROOT

ALEMBIC_INI = REPO_ROOT / "database" / "alembic.ini"

# No parallel query in REI's PostgreSQL sessions (migrations included). Parallel
# workers share their work through /dev/shm, which production's database container
# keeps small: from 26 October 2026 NDW's runs failed there with "could not resize
# shared memory segment ... No space left on device" (decision 0042). REI's queries
# are lookups and lists by indexed columns; they do not need parallel workers.
POSTGRES_SESSION_OPTIONS = (
    "-c max_parallel_workers_per_gather=0 -c max_parallel_maintenance_workers=0"
)


def create_db_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    if url.get_backend_name() == "postgresql":
        return create_engine(
            url, pool_pre_ping=True, connect_args={"options": POSTGRES_SESSION_OPTIONS}
        )
    if url.get_backend_name() != "sqlite":
        return create_engine(url, pool_pre_ping=True)

    in_memory = url.database in (None, "", ":memory:")
    if not in_memory:
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False, "timeout": 30},
        # One shared connection keeps an in-memory database alive across sessions.
        **({"poolclass": StaticPool} if in_memory else {}),
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")
        dbapi_connection.execute("PRAGMA busy_timeout=30000")

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def run_migrations(database_url: str) -> None:
    """Bring the database schema up to date (database/migrations)."""
    config = Config(str(ALEMBIC_INI))
    # '%' is the interpolation character in Alembic's config values.
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")
