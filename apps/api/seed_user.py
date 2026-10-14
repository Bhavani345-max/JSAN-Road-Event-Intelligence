"""Create the first local reviewer from SEED_ADMIN_EMAIL/PASSWORD in .env."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.config import get_settings
from app.core.database import create_db_engine, create_session_factory, run_migrations
from app.services.auth_service import seed_admin_user


def main() -> int:
    settings = get_settings()
    if not settings.seed_admin_email or not settings.seed_admin_password:
        print("Set SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD in .env first.")
        return 2
    run_migrations(settings.database_url)
    factory = create_session_factory(create_db_engine(settings.database_url))
    with factory() as session:
        try:
            user, created = seed_admin_user(
                session, settings.seed_admin_email, settings.seed_admin_password
            )
            session.commit()
        except ValueError as error:
            session.rollback()
            print(str(error))
            return 2
    print(f"Bootstrap account {'created' if created else 'already exists'}: {user.email}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
