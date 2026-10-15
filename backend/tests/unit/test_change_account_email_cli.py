"""The command that gives an account a new sign-in email (cli/change_account_email.py).

Run on a throwaway SQLite file with two test accounts: check-only saves
nothing, --apply saves only the email, a wrong role is refused, and the check
after the change rolls everything back if anything else changed.
"""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.database import create_db_engine, create_session_factory
from app.models import AuthSession, User
from app.models.base import Base
from app.services.auth_service import ADMIN_ROLE, USER_ROLE, create_session, seed_account

CLI = Path(__file__).resolve().parents[2] / "cli" / "change_account_email.py"
OLD, NEW, USER = "admin@example.com", "new-admin@example.com", "user@example.com"


@pytest.fixture
def cli(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'accounts.db'}"
    engine = create_db_engine(url)
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory() as session:
        admin, _ = seed_account(session, OLD, "admin test password", role=ADMIN_ROLE)
        user, _ = seed_account(session, USER, "user test password", role=USER_ROLE)
        for account in (admin, admin, user):  # two open admin sessions, one user session
            create_session(session, account, 12)
        session.commit()
    spec = importlib.util.spec_from_file_location("change_account_email_cli", CLI)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "get_settings", lambda: SimpleNamespace(database_url=url))

    def run(*args: str) -> int:
        monkeypatch.setattr(sys, "argv", ["change_account_email.py", *args])
        return module.main()

    def accounts() -> dict[str, tuple]:
        with factory() as session:
            return {u.user_id: (u.email, u.role, u.is_active, u.password_hash, u.created_at)
                    for u in session.scalars(select(User))}  # fmt: skip

    def sessions() -> dict[str, list[tuple]]:
        with factory() as session:
            found: dict[str, list[tuple]] = {}
            for row in session.scalars(select(AuthSession).order_by(AuthSession.token_hash)):
                found.setdefault(row.user_id, []).append((row.token_hash, row.created_at, row.expires_at))
            return found

    yield SimpleNamespace(run=run, accounts=accounts, sessions=sessions, module=module)
    engine.dispose()


def test_check_only_saves_nothing(cli):
    before, sessions = cli.accounts(), cli.sessions()
    assert cli.run(OLD, NEW, "--role", "admin") == 0
    assert cli.accounts() == before and cli.sessions() == sessions


def test_apply_ends_only_the_changed_accounts_sessions(cli):
    user_id = next(uid for uid, values in cli.accounts().items() if values[0] == USER)
    before = cli.sessions()
    assert cli.run(OLD, NEW, "--role", "admin", "--apply") == 0
    assert cli.sessions() == {user_id: before[user_id]}  # the user's, row for row


def test_apply_changes_only_the_email(cli):
    before = cli.accounts()
    assert cli.run(OLD, NEW, "--role", "admin", "--apply") == 0
    after = cli.accounts()
    for user_id, values in before.items():
        expected = (NEW, *values[1:]) if values[0] == OLD else values
        assert after[user_id] == expected
    # And back again: the rollback is the same command, reversed.
    assert cli.run(NEW, OLD, "--role", "admin", "--apply") == 0
    assert cli.accounts() == before


def test_a_wrong_role_or_a_taken_email_is_refused(cli, capsys):
    before = cli.accounts()
    assert cli.run(USER, NEW, "--role", "admin", "--apply") == 2
    assert cli.run(OLD, USER, "--role", "admin", "--apply") == 2
    assert cli.accounts() == before
    assert "is a 'user' account, not 'admin'" in capsys.readouterr().out


def test_any_other_difference_rolls_everything_back(cli, monkeypatch, capsys):
    real_change = cli.module.change_account_email

    def change_and_more(session, *args, **kwargs):
        change = real_change(session, *args, **kwargs)
        session.scalar(select(User).where(User.email == USER)).role = "admin"  # a change that must not happen
        session.flush()
        return change

    monkeypatch.setattr(cli.module, "change_account_email", change_and_more)
    before = cli.accounts()
    assert cli.run(OLD, NEW, "--role", "admin", "--apply") == 3
    assert cli.accounts() == before
    assert "nothing was saved" in capsys.readouterr().out


def test_ending_another_accounts_sessions_rolls_everything_back(cli, monkeypatch):
    real_change = cli.module.change_account_email

    def change_and_end_the_users_sessions(session, *args, **kwargs):
        change = real_change(session, *args, **kwargs)
        user_id = session.scalar(select(User.user_id).where(User.email == USER))
        session.query(AuthSession).filter(AuthSession.user_id == user_id).delete()
        session.flush()
        return change

    monkeypatch.setattr(cli.module, "change_account_email", change_and_end_the_users_sessions)
    before, sessions = cli.accounts(), cli.sessions()
    assert cli.run(OLD, NEW, "--role", "admin", "--apply") == 3
    assert cli.accounts() == before and cli.sessions() == sessions
