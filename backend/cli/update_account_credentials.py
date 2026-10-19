
"""Safely update an existing REI production account's email and password."""

import getpass
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import (
    create_db_engine,
    create_session_factory,
)
from app.models import User
from app.services.auth_service import (
    ADMIN_ROLE,
    USER_ROLE,
    change_account_email,
    hash_password,
    normalize_email,
)


def main() -> int:
    settings = get_settings()

    if not settings.database_url:
        print("Database URL is not configured.")
        return 2

    print("REI account credential update")
    print("This operation changes an EXISTING account.")
    print("Use only the intended Railway production database.")
    print()

    old_email = input("Current login email: ").strip()
    new_email = input("New login email: ").strip()
    role = input("Account role (admin/user): ").strip().lower()

    if role not in (ADMIN_ROLE, USER_ROLE):
        print("Invalid role. Enter admin or user.")
        return 2

    if not old_email or not new_email:
        print("Both email addresses are required.")
        return 2

    if normalize_email(old_email) == normalize_email(new_email):
        print("The new email must differ from the current email.")
        return 2

    password = getpass.getpass("New password (hidden): ")
    confirm = getpass.getpass("Confirm new password (hidden): ")

    if password != confirm:
        print("Passwords do not match.")
        return 2

    try:
        new_password_hash = hash_password(password)
    except ValueError as error:
        print(str(error))
        return 2

    # Do not print the password, password hash, or database URL.
    password = ""
    confirm = ""

    print()
    print(f"Account: {normalize_email(old_email)}")
    print(f"New email: {normalize_email(new_email)}")
    print(f"Role to preserve: {role}")

    confirmation = input(
        "Type UPDATE to confirm the account change: "
    ).strip()

    if confirmation != "UPDATE":
        print("Cancelled. No changes made.")
        return 1

    engine = create_db_engine(settings.database_url)
    factory = create_session_factory(engine)

    try:
        with factory() as session:
            try:
                with session.begin():
                    account = session.scalar(
                        select(User)
                        .where(
                            User.email == normalize_email(old_email)
                        )
                        .with_for_update()
                    )

                    if account is None:
                        raise ValueError(
                            "No account exists with the current email."
                        )

                    if account.role != role:
                        raise ValueError(
                            f"Account role is {account.role!r}, "
                            f"not {role!r}. No changes made."
                        )

                    if not account.is_active:
                        raise ValueError(
                            "The account is inactive. No changes made."
                        )

                    # Change email and revoke existing sessions.
                    change_account_email(
                        session,
                        old_email,
                        new_email,
                        role=role,
                        end_sessions=True,
                    )

                    # Re-fetch the same account and set its password hash.
                    account = session.scalar(
                        select(User)
                        .where(
                            User.email == normalize_email(new_email)
                        )
                        .with_for_update()
                    )

                    if account is None:
                        raise ValueError(
                            "Account lookup failed. Changes rolled back."
                        )

                    account.password_hash = new_password_hash

                    from packages.common.time import utc_now

                    account.updated_at = utc_now()

            except ValueError as error:
                print(f"Update failed: {error}")
                return 2

        print("Account credentials updated successfully.")
        print("The existing account role was preserved.")
        print("Existing sessions were revoked.")
        print("Sign in using the new email and password.")
        return 0

    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
