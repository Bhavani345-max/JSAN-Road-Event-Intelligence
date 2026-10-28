"""Sign-in limit, admin password reset and recovery codes (decision 0044).

The user's rules of 28 October 2026: warn from the third failed attempt, lock
the account for 30 minutes at the fifth; the administrator resets the User's
password (a temporary one, replaced at the next sign-in); the administrator
keeps single-use recovery codes for a forgotten password of their own; an
emergency reset on the server when the codes are gone too. Every test runs on
an in-memory database with test accounts.
"""

import logging
from collections import defaultdict

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.routes import auth
from app.core.config import Settings
from app.main import create_app
from app.models import AuthSession, RecoveryCode, SecurityEvent, User
from app.services.auth_service import SECURITY_EVENT_KINDS, normalize_recovery_code
from cli.reset_password import reset_on_server

ADMIN = ("admin@example.com", "admin test password 1")
USER = ("user@example.com", "user test password 22")
ORIGIN = {"Origin": "http://localhost:3000"}
NEW = "a brand new password"


class Clock:
    """Stands in for the limiter's monotonic clock."""

    def __init__(self):
        self.now = 1_000_000.0

    def __call__(self):
        return self.now

    def minutes(self, minutes):
        self.now += minutes * 60


@pytest.fixture(autouse=True)
def fresh_limits(monkeypatch):
    monkeypatch.setattr(auth, "_LOGIN_ATTEMPTS", defaultdict(auth.deque))


@pytest.fixture
def clock(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(auth, "monotonic", clock)
    return clock


@pytest.fixture
def app(engine):
    settings = Settings(
        _env_file=None, database_url="sqlite://", auto_migrate=False,
        ingestion_scheduler_enabled=False,
        seed_admin_email=ADMIN[0], seed_admin_password=ADMIN[1],
        seed_user_email=USER[0], seed_user_password=USER[1],
    )  # fmt: skip
    application = create_app(settings, engine=engine)
    application.state.ingestion_service.connector_factories = {}
    with TestClient(application):
        yield application


def client(app):
    return TestClient(app)


def sign_in(app_or_client, account, password=None):
    browser = app_or_client if isinstance(app_or_client, TestClient) else client(app_or_client)
    email, own = account
    response = browser.post("/api/auth/login", json={"email": email, "password": password or own})
    return browser, response


def signed_in(app, account, password=None):
    browser, response = sign_in(app, account, password)
    assert response.status_code == 200, response.json()
    return browser


def user_id(session, email):
    session.expire_all()
    return session.scalar(select(User.user_id).where(User.email == email))


def events(session):
    session.expire_all()
    return [(event.kind, event.account_id, event.actor_id) for event in session.scalars(select(SecurityEvent).order_by(SecurityEvent.occurred_at))]


def reset(admin_browser, account_id, admin_password=ADMIN[1]):
    return admin_browser.post(
        f"/api/auth/accounts/{account_id}/temporary-password", json={"current_password": admin_password}, headers=ORIGIN
    )


def new_codes(admin_browser, admin_password=ADMIN[1]):
    return admin_browser.post("/api/auth/recovery-codes", json={"current_password": admin_password}, headers=ORIGIN)


def recover(app, email, code, new_password=NEW):
    return client(app).post("/api/auth/recover", json={"email": email, "recovery_code": code, "new_password": new_password})


# --- the sign-in limit ------------------------------------------------------------------


@pytest.mark.parametrize("email", [USER[0], "nobody@example.com"], ids=["account", "made-up email"])
def test_warned_from_the_third_failure_and_locked_at_the_fifth(app, email):
    answers = [sign_in(app, (email, "wrong password"))[1] for _ in range(5)]
    assert [answer.status_code for answer in answers] == [401, 401, 401, 401, 429]
    details = [answer.json()["detail"] for answer in answers]
    assert details[0] == details[1] == "The email or password is incorrect."
    assert details[2] == "The email or password is incorrect. 2 attempts left before this account is locked for 30 minutes."
    assert details[3] == "The email or password is incorrect. 1 attempt left before this account is locked for 30 minutes."
    assert details[4].endswith("Too many failed attempts: this account is locked for 30 minutes.")


def test_the_answers_are_the_same_for_an_account_and_a_made_up_email(app):
    for _ in range(5):
        real = sign_in(app, (USER[0], "wrong password"))[1]
        made_up = sign_in(app, ("nobody@example.com", "wrong password"))[1]
        assert (real.status_code, real.json()) == (made_up.status_code, made_up.json())


def test_the_lock_lasts_30_minutes_from_the_fifth_failure_even_with_the_right_password(app, clock):
    for gap in (0, 10, 10, 5, 4):  # five failures within 29 minutes
        clock.minutes(gap)
        sign_in(app, (USER[0], "wrong password"))
    clock.minutes(29)
    _, still = sign_in(app, USER)
    assert still.status_code == 429 and still.json()["detail"].endswith("try again in 1 minute.")
    clock.minutes(1)
    assert sign_in(app, USER)[1].status_code == 200


def test_failures_older_than_30_minutes_are_forgotten(app, clock):
    for _ in range(4):
        assert sign_in(app, (USER[0], "wrong password"))[1].status_code == 401
    clock.minutes(31)
    _, first_again = sign_in(app, (USER[0], "wrong password"))
    assert first_again.json()["detail"] == "The email or password is incorrect."  # counting starts over


def test_a_success_clears_the_count(app):
    for _ in range(4):
        sign_in(app, (USER[0], "wrong password"))
    assert sign_in(app, USER)[1].status_code == 200
    assert sign_in(app, (USER[0], "wrong password"))[1].json()["detail"] == "The email or password is incorrect."


def test_a_lock_is_recorded_for_an_account_only(app, session):
    for email in (USER[0], "nobody@example.com"):
        for _ in range(5):
            sign_in(app, (email, "wrong password"))
    assert events(session) == [("sign_in_locked", user_id(session, USER[0]), None)]


# --- the administrator resets the User's password ------------------------------------------


def test_only_an_administrator_resets_a_password(app, session):
    target = user_id(session, USER[0])
    assert reset(client(app), target).status_code == 401
    assert reset(signed_in(app, USER), target).status_code == 403
    assert client(app).get("/api/admin/users").status_code == 401
    assert signed_in(app, USER).get("/api/admin/users").status_code == 403
    admin = signed_in(app, ADMIN)
    wrong = reset(admin, target, admin_password="not my password")
    assert wrong.status_code == 400 and wrong.json()["detail"] == "The current password is incorrect."
    assert reset(admin, user_id(session, ADMIN[0])).status_code == 400  # never the administrator's own
    assert reset(admin, "no-such-account").status_code == 404
    assert client(app).post(
        f"/api/auth/accounts/{target}/temporary-password", json={"current_password": ADMIN[1]},
        headers={"Origin": "https://evil.example"}, cookies=admin.cookies,
    ).status_code == 403  # fmt: skip
    # Nothing changed: the User still signs in with their own password.
    assert sign_in(app, USER)[1].json()["must_change_password"] is False


def test_the_administrator_lists_the_accounts(app):
    listed = signed_in(app, ADMIN).get("/api/admin/users").json()
    assert sorted((account["email"], account["role"], account["status"]) for account in listed) == [
        (ADMIN[0], "admin", "active"), (USER[0], "user", "active"),
    ]  # fmt: skip


def test_a_temporary_password_must_be_replaced_before_anything_else(app, session, caplog):
    caplog.set_level(logging.DEBUG)
    user_browser = signed_in(app, USER)
    response = reset(signed_in(app, ADMIN), user_id(session, USER[0]))
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    temporary = response.json()["temporary_password"]
    assert normalize_recovery_code(temporary) is not None and len(temporary) == 19  # xxxx-xxxx-xxxx-xxxx
    assert response.json()["account"]["must_change_password"] is True
    # The User was signed out everywhere, and the old password no longer works.
    assert user_browser.get("/api/auth/me").status_code == 401
    assert sign_in(app, USER)[1].status_code == 401
    # Signed in with the temporary password: nothing but choosing a new one.
    browser, signed = sign_in(app, USER, temporary)
    assert signed.status_code == 200 and signed.json()["must_change_password"] is True
    assert browser.get("/api/auth/me").json()["must_change_password"] is True
    for path in ("/api/events", "/api/sources", "/api/cities"):
        assert browser.get(path).status_code == 403, path
    assert browser.post("/api/auth/profile", json={"display_name": "x"}, headers=ORIGIN).status_code == 403
    assert browser.post("/api/auth/password", json={"current_password": temporary, "new_password": NEW}, headers=ORIGIN).json() == {"ok": True}
    assert browser.get("/api/auth/me").json()["must_change_password"] is False
    assert browser.get("/api/events").status_code == 200
    assert sign_in(app, USER, NEW)[1].status_code == 200
    admin_id, target = user_id(session, ADMIN[0]), user_id(session, USER[0])
    assert events(session)[-2:] == [("temporary_password_set", target, admin_id), ("password_changed", target, target)]
    # The temporary password is in no record and no log line.
    assert temporary not in caplog.text
    assert all(temporary not in str(row.detail) for row in session.scalars(select(SecurityEvent)))


def test_a_reset_lifts_the_users_lock(app, session):
    for _ in range(5):
        sign_in(app, (USER[0], "wrong password"))
    assert sign_in(app, USER)[1].status_code == 429
    temporary = reset(signed_in(app, ADMIN), user_id(session, USER[0])).json()["temporary_password"]
    assert sign_in(app, USER, temporary)[1].status_code == 200


def test_wrong_administrator_passwords_count_towards_the_administrators_limit(app, session):
    admin = signed_in(app, ADMIN)
    target = user_id(session, USER[0])
    assert [reset(admin, target, "guess").status_code for _ in range(5)] == [400, 400, 400, 400, 429]
    assert reset(admin, target).status_code == 429
    assert sign_in(app, ADMIN)[1].status_code == 429


# --- the administrator's recovery codes --------------------------------------------------


def test_only_an_administrator_has_recovery_codes(app):
    assert client(app).get("/api/auth/recovery-codes").status_code == 401
    assert new_codes(client(app)).status_code == 401
    user = signed_in(app, USER)
    assert user.get("/api/auth/recovery-codes").status_code == 403
    assert new_codes(user, USER[1]).status_code == 403
    admin = signed_in(app, ADMIN)
    assert admin.get("/api/auth/recovery-codes").json() == {"remaining": 0, "total": 0, "created_at": None}
    assert new_codes(admin, "not my password").status_code == 400


def test_codes_are_shown_once_and_stored_only_as_digests(app, session, caplog):
    caplog.set_level(logging.DEBUG)
    admin = signed_in(app, ADMIN)
    response = new_codes(admin)
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    codes = response.json()["codes"]
    assert len(codes) == len(set(codes)) == 10
    assert all(normalize_recovery_code(code) for code in codes)
    status = admin.get("/api/auth/recovery-codes").json()
    assert (status["remaining"], status["total"]) == (10, 10) and "codes" not in status
    stored = " ".join(row.code_hash for row in session.scalars(select(RecoveryCode)))
    for code in codes:
        assert code not in stored and normalize_recovery_code(code) not in stored
        assert code not in caplog.text
    assert ("recovery_codes_created", user_id(session, ADMIN[0]), user_id(session, ADMIN[0])) in events(session)


def test_new_codes_cancel_the_earlier_ones(app):
    admin = signed_in(app, ADMIN)
    old = new_codes(admin).json()["codes"]
    new = new_codes(admin).json()["codes"]
    assert recover(app, ADMIN[0], old[0]).status_code == 400
    assert recover(app, ADMIN[0], new[0]).status_code == 200


def test_a_recovery_code_sets_a_new_password_once(app, session):
    admin = signed_in(app, ADMIN)
    code = new_codes(admin).json()["codes"][3]
    # Typed in capitals with spaces: still the code.
    response = recover(app, " Admin@Example.com ", code.upper().replace("-", " "))
    assert response.status_code == 200 and response.json() == {"ok": True, "codes_left": 9}
    assert admin.get("/api/auth/me").status_code == 401  # every session ended
    assert sign_in(app, ADMIN)[1].status_code == 401
    assert sign_in(app, ADMIN, NEW)[1].status_code == 200
    # Used up: the same code again is refused like any wrong one.
    again = recover(app, ADMIN[0], code, "another new password")
    assert again.status_code == 400 and again.json()["detail"] == "The email or recovery code is not valid."
    assert sign_in(app, ADMIN, NEW)[1].status_code == 200
    admin_id = user_id(session, ADMIN[0])
    assert ("recovered_with_code", admin_id, admin_id) in events(session)
    assert session.scalar(select(AuthSession).where(AuthSession.user_id == admin_id)) is not None  # the new sign-in


def test_a_refused_new_password_does_not_use_the_code_up(app):
    admin = signed_in(app, ADMIN)
    code = new_codes(admin).json()["codes"][0]
    short = recover(app, ADMIN[0], code, "short")
    assert short.status_code == 400 and "at least 8 characters" in short.json()["detail"]
    assert admin.get("/api/auth/recovery-codes").json()["remaining"] == 10
    assert recover(app, ADMIN[0], code).status_code == 200


@pytest.mark.parametrize(
    "email, code",
    [
        (ADMIN[0], "aaaa-bbbb-cccc-dddd"),  # a code of the right form, not the account's
        (ADMIN[0], "not a code"),
        ("nobody@example.com", "VALID"),  # replaced by a real code below
        (USER[0], "VALID"),  # another account's code
    ],
    ids=["wrong code", "malformed", "made-up email", "another account"],
)
def test_every_wrong_recovery_gets_the_same_answer(app, email, code):
    valid = new_codes(signed_in(app, ADMIN)).json()["codes"][0]
    response = recover(app, email, valid if code == "VALID" else code)
    assert response.status_code == 400
    assert response.json() == {"detail": "The email or recovery code is not valid."}


def test_recovery_attempts_are_limited_and_a_lock_spares_the_codes(app):
    admin = signed_in(app, ADMIN)
    valid = new_codes(admin).json()["codes"][0]
    statuses = [recover(app, ADMIN[0], "aaaa-bbbb-cccc-dddd").status_code for _ in range(5)]
    assert statuses == [400, 400, 400, 400, 429]
    locked = recover(app, ADMIN[0], valid)
    assert locked.status_code == 429  # even the right code waits
    assert admin.get("/api/auth/recovery-codes").json()["remaining"] == 10


def test_the_view_only_user_cannot_use_recovery(app, session):
    """The User has no codes: the administrator resets their password instead."""
    assert recover(app, USER[0], "aaaa-bbbb-cccc-dddd").json() == {"detail": "The email or recovery code is not valid."}


# --- the emergency reset on the server ----------------------------------------------------


def test_the_emergency_reset_sets_a_temporary_password_and_ends_the_codes(app, session):
    admin = signed_in(app, ADMIN)
    codes = new_codes(admin).json()["codes"]
    temporary, ended = reset_on_server(app.state.session_factory, ADMIN[0])
    assert ended == 10
    assert admin.get("/api/auth/me").status_code == 401
    assert recover(app, ADMIN[0], codes[1]).status_code == 400  # the lost codes no longer work
    browser, signed = sign_in(app, ADMIN, temporary)
    assert signed.json()["must_change_password"] is True
    assert browser.get("/api/events").status_code == 403
    admin_id = user_id(session, ADMIN[0])
    assert events(session)[-2:] == [
        ("recovery_codes_revoked", admin_id, None),
        ("temporary_password_set_on_server", admin_id, None),
    ]
    with pytest.raises(LookupError):
        reset_on_server(app.state.session_factory, "nobody@example.com")


def test_existing_sign_in_and_roles_are_unchanged(app):
    admin = signed_in(app, ADMIN)
    user = signed_in(app, USER)
    assert admin.get("/api/auth/me").json()["must_change_password"] is False
    assert admin.post("/api/ingestion/run", headers=ORIGIN).status_code == 200
    assert user.get("/api/events").status_code == 200
    assert user.post("/api/ingestion/run", headers=ORIGIN).status_code == 403


def test_every_security_event_kind_fits_its_column():
    limit = SecurityEvent.__table__.columns["kind"].type.length
    assert all(len(kind) <= limit for kind in SECURITY_EVENT_KINDS)
