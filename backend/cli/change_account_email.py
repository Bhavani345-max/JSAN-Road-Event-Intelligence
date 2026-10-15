"""Give an existing account a new sign-in email (its password, role and history stay):
    python backend/cli/change_account_email.py OLD NEW --role admin            # check only: nothing is saved
    python backend/cli/change_account_email.py OLD NEW --role admin --apply    # save the change
    --role ROLE        the role the account must have; anything else is refused
    --keep-sessions    keep the account's open sessions (by default they end,
                       so it signs in again with the new email)
    --railway-proxy    connect through Railway's TCP proxy, from the POSTGRES_* and
                       RAILWAY_TCP_PROXY_* variables `railway run -s PostGIS` provides

Everything runs in one transaction. Before saving, every account is compared
with how it was: only the changed account's email and last-update time may
differ, so its password hash, id, role and status, and every other account,
are checked to be exactly as they were. No hash, token or password is printed.
"""

import argparse
import hashlib
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BACKEND_DIR)]

from sqlalchemy import URL, func, select  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import create_db_engine, create_session_factory  # noqa: E402
from app.models import AuthSession, User  # noqa: E402
from app.services.auth_service import change_account_email  # noqa: E402


def _railway_proxy_url() -> URL:
    env = os.environ
    return URL.create(
        "postgresql+psycopg",
        username=env["POSTGRES_USER"],
        password=env["POSTGRES_PASSWORD"],
        host=env["RAILWAY_TCP_PROXY_DOMAIN"],
        port=int(env["RAILWAY_TCP_PROXY_PORT"]),
        database=env["POSTGRES_DB"],
    )


def _accounts(session) -> dict[str, tuple]:
    """Every account by id, read from the database itself (plain columns, not the
    session's loaded objects): what must not change. The password hash is compared
    as its full SHA-256 digest; only the first 12 characters are ever printed."""
    rows = session.execute(select(
        User.user_id, User.email, User.role, User.is_active, User.display_name, User.created_at,
        User.password_hash, User.updated_at,
    ))  # fmt: skip
    return {
        user_id: (email, role, active, name, created, hashlib.sha256(password_hash.encode()).hexdigest(), updated)
        for user_id, email, role, active, name, created, password_hash, updated in rows
    }


def _show(title: str, accounts: dict[str, tuple], sessions: dict[str, int]) -> None:
    print(title)
    for user_id, (email, role, active, _, _, fingerprint, _) in sorted(accounts.items(), key=lambda a: a[1][4]):
        print(f"  {email} | role={role} | active={active} | hash fingerprint={fingerprint[:12]}"
              f" | open sessions={sessions.get(user_id, 0)}")


def _sessions(session) -> dict[str, int]:
    return dict(session.execute(select(AuthSession.user_id, func.count()).group_by(AuthSession.user_id)).all())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("old_email")
    parser.add_argument("new_email")
    parser.add_argument("--role", required=True, help="the role the account must have, e.g. admin")
    parser.add_argument("--apply", action="store_true", help="save the change (default: check only)")
    parser.add_argument("--keep-sessions", action="store_true", help="keep the account's open sessions")
    parser.add_argument("--railway-proxy", action="store_true", help="connect through Railway's TCP proxy")
    args = parser.parse_args()

    url = _railway_proxy_url() if args.railway_proxy else get_settings().database_url
    engine = create_db_engine(url)
    print("Database:", engine.url.render_as_string(hide_password=True))
    with create_session_factory(engine)() as session:
        before, sessions_before = _accounts(session), _sessions(session)
        _show("Before:", before, sessions_before)
        try:
            change = change_account_email(
                session, args.old_email, args.new_email, role=args.role, end_sessions=not args.keep_sessions
            )
        except ValueError as error:
            session.rollback()
            print(f"Not changed: {error}")
            return 2
        after, sessions_after = _accounts(session), _sessions(session)
        # Only the changed account's email and last-update time may differ, and
        # only its sessions may have ended.
        expected = {
            user_id: (change.new_email, *values[1:6], after[user_id][6]) if user_id == change.user_id else values
            for user_id, values in before.items()
        }
        others = {user_id: n for user_id, n in sessions_before.items() if user_id != change.user_id}
        if after != expected or {k: v for k, v in sessions_after.items() if k != change.user_id} != others:
            session.rollback()
            print("Not changed: the check after the change found other differences; nothing was saved.")
            return 3
        _show("After:", after, sessions_after)
        print(f"{change.old_email} -> {change.new_email}; sessions ended: {change.sessions_ended}")
        if args.apply:
            session.commit()
            print("Saved.")
        else:
            session.rollback()
            print("Check only: nothing was saved. Add --apply to save.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
