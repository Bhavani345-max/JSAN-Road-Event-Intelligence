"""Create the local accounts from .env: the admin (SEED_ADMIN_EMAIL/PASSWORD) and,
if set, the read-only User (SEED_USER_EMAIL/PASSWORD). Existing accounts are
left as they are; no password is ever reset or printed."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.core.database import create_db_engine, create_session_factory, run_migrations
from app.services.auth_service import USER_ROLE, normalize_email, seed_account, seed_admin_user


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
    if user.email != normalize_email(settings.seed_admin_email):
        print(f"Admin account not created: {user.email} is already the admin account.")
    else:
        print(f"Bootstrap account {'created' if created else 'already exists'}: {user.email}")
    if settings.seed_user_email and settings.seed_user_password:
        if normalize_email(settings.seed_user_email) == normalize_email(settings.seed_admin_email):
            print("SEED_USER_EMAIL must differ from SEED_ADMIN_EMAIL; User account not created.")
            return 2
        with factory() as session:
            try:
                account, made = seed_account(
                    session, settings.seed_user_email, settings.seed_user_password, role=USER_ROLE
                )
                session.commit()
            except ValueError as error:
                session.rollback()
                print(str(error))
                return 2
        if account.email != normalize_email(settings.seed_user_email):
            print(f"User account not created: {account.email} is already the User account.")
        else:
            print(f"User account {'created' if made else 'already exists'}: {account.email} ({account.role})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
