
"""Update the email and password of an existing REI account."""

import getpass
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import create_db_engine, create_session_factory
from app.models import User
from app.services.auth_service import (
    ADMIN_ROLE,
    USER_ROLE,
    change_account_email,
    hash_password,
    normalize_email,
)
from packages.common.time import utc_now


def main() -> int:
    settings = get_settings()
    database_url = settings.database_url

    if not database_url:
        print("ERROR: DATABASE_URL is not configured.")
        return 2

    old_email = normalize_email(input("Current account email: "))
    new_email = normalize_email(input("New account email: "))
    role = input("Account role (admin/user): ").strip().lower()

    if role not in (ADMIN_ROLE, USER_ROLE):
        print("ERROR: Role must be admin or user.")
        return 2

    password = getpass.getpass("New password (hidden): ")
    confirmation = getpass.getpass("Confirm new password (hidden): ")

    if password != confirmation:
        print("ERROR: Passwords do not match.")
        return 2

    try:
        password_hash = hash_password(password)
    except ValueError as error:
        print(f"ERROR: {error}")
        return 2
    finally:
        password = ""
        confirmation = ""

    print("\nReview the requested change:")
    print(f"Existing email: {old_email}")
    print(f"New email:      {new_email}")
    print(f"Expected role:  {role}")
    print("Existing sessions will be revoked.")

    if input('Type "UPDATE" to confirm: ').strip() != "UPDATE":
        print("Cancelled.")
        return 1

    engine = create_db_engine(database_url)
    factory = create_session_factory(engine)

    try:
        with factory() as session:
            with session.begin():
                account = session.scalar(
                    select(User)
                    .where(User.email == old_email)
                    .with_for_update()
                )

                if account is None:
                    raise ValueError("Existing account was not found.")

                if account.role != role:
                    raise ValueError(
                        f"Role mismatch: existing account has role "
                        f"{account.role!r}."
                    )

                if not account.is_active:
                    raise ValueError("Account is inactive.")

                change_account_email(
                    session,
                    old_email,
                    new_email,
                    role=role,
                    end_sessions=True,
                )

                account = session.scalar(
                    select(User)
                    .where(User.email == new_email)
                    .with_for_update()
                )

                if account is None:
                    raise ValueError("Account lookup failed after email change.")

                account.password_hash = password_hash
                account.updated_at = utc_now()

        print("\nCredentials updated successfully.")
        print("Account role preserved.")
        print("Existing sessions revoked.")
        return 0

    except ValueError as error:
        print(f"ERROR: {error}")
        return 2

    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
