"""Emergency password reset on the server (decision 0044, docs/operations/emergency-account-recovery.md).

    python backend/cli/reset_password.py admin@example.com

For when an administrator has forgotten the password AND has no recovery code
left. Only someone with access to the server (Railway project) can run it. It
gives the account a new random temporary password, printed once here, ends all
the account's sessions and its remaining recovery codes, and records the reset
(never the password). The account must choose its own password at its next
sign-in and should then create new recovery codes.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import create_db_engine, create_session_factory  # noqa: E402
from app.models import User  # noqa: E402
from app.services.auth_service import (  # noqa: E402
    normalize_email,
    revoke_recovery_codes,
    set_temporary_password,
)


def reset_on_server(session_factory: sessionmaker[Session], email: str) -> tuple[str, int]:
    """The account's new temporary password and how many recovery codes were ended.
    Raises LookupError when no account has the email."""
    with session_factory() as session, session.begin():
        user = session.scalar(select(User).where(User.email == normalize_email(email)).with_for_update())
        if user is None:
            raise LookupError(f"No account has the email {normalize_email(email)}.")
        ended = revoke_recovery_codes(session, user)
        temporary = set_temporary_password(session, user, actor=None)
    return temporary, ended


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    email = normalize_email(sys.argv[1])
    settings = get_settings()
    print(f"Database: {'PostgreSQL' if settings.database_url.startswith('postgresql') else 'SQLite (local)'}")
    print(f"Account:  {email}")
    print("This sets a temporary password, signs the account out everywhere and ends its recovery codes.")
    if input('Type "RESET" to continue: ').strip() != "RESET":
        print("Cancelled. Nothing was changed.")
        return 1
    try:
        temporary, ended = reset_on_server(create_session_factory(create_db_engine(settings.database_url)), email)
    except LookupError as error:
        print(f"ERROR: {error}")
        return 2
    print()
    print(f"Temporary password (shown only now): {temporary}")
    print(f"Recovery codes ended: {ended}")
    print("Give it to the account holder in person or by phone, never by email or chat.")
    print("They must choose a new password when they sign in, then create new recovery codes.")
    print("If the account was locked after failed sign-ins, the lock ends within 30 minutes")
    print("(or at once when the API restarts).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
