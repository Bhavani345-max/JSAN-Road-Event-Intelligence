"""Exactly two accounts: Admin and User (decision 0032).

Both are created only from configuration at startup (SEED_ADMIN_* and
SEED_USER_*), once, and never reset. There is no registration. The Admin
manages REI and reviews; the User signs in to view the console and changes
nothing. Every test runs on an in-memory database with test accounts.
"""

from collections import defaultdict

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.routes import auth
from app.core.config import Settings
from app.main import create_app
from app.models import AuthSession, User
from app.services.auth_service import change_account_email

ADMIN = ("admin@example.com", "admin test password 1")
USER = ("user@example.com", "user test password 22")
ORIGIN = {"Origin": "http://localhost:3000"}


def settings(**overrides) -> Settings:
    values = {
        "_env_file": None, "database_url": "sqlite://", "auto_migrate": False,
        "ingestion_scheduler_enabled": False,
        "seed_admin_email": ADMIN[0], "seed_admin_password": ADMIN[1],
        "seed_user_email": USER[0], "seed_user_password": USER[1],
    }  # fmt: skip
    return Settings(**(values | overrides))


@pytest.fixture(autouse=True)
def fresh_limits(monkeypatch):
    monkeypatch.setattr(auth, "_LOGIN_ATTEMPTS", defaultdict(auth.deque))


@pytest.fixture
def app(engine):
    application = create_app(settings(), engine=engine)
    # No source is read in these tests.
    application.state.ingestion_service.connector_factories = {}
    return application


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client


def sign_in(client, account, password=None):
    email, own_password = account
    return client.post("/api/auth/login", json={"email": email, "password": password or own_password})


def accounts(session):
    session.expire_all()
    return {user.email: user for user in session.scalars(select(User))}


# --- the two accounts -----------------------------------------------------------------


def test_startup_creates_exactly_the_admin_and_the_user(client, session):
    found = accounts(session)
    assert {email: user.role for email, user in found.items()} == {ADMIN[0]: "admin", USER[0]: "user"}
    assert all(user.is_active for user in found.values())
    # Passwords are stored only as salted hashes, each its own.
    hashes = [user.password_hash for user in found.values()]
    assert all(h.startswith("pbkdf2_sha256$") for h in hashes) and len(set(hashes)) == 2
    assert ADMIN[1] not in hashes[0] + hashes[1] and USER[1] not in hashes[0] + hashes[1]


def test_a_restart_never_resets_a_password_or_adds_an_account(engine, session, client):
    before = {email: user.password_hash for email, user in accounts(session).items()}
    changed = settings(seed_admin_password="another admin password", seed_user_password="another user password")
    with TestClient(create_app(changed, engine=engine)):
        pass
    after = {email: user.password_hash for email, user in accounts(session).items()}
    assert after == before


def test_a_changed_email_never_adds_a_third_account(engine, session, client):
    before = {email: (user.role, user.password_hash) for email, user in accounts(session).items()}
    changed = settings(seed_admin_email="second-admin@example.com", seed_user_email="second-user@example.com")
    with TestClient(create_app(changed, engine=engine)) as other:
        assert sign_in(other, ("second-admin@example.com", ADMIN[1])).status_code == 401
        assert sign_in(other, ("second-user@example.com", USER[1])).status_code == 401
        assert sign_in(other, ADMIN).status_code == 200
    after = {email: (user.role, user.password_hash) for email, user in accounts(session).items()}
    assert after == before


@pytest.mark.parametrize(
    "overrides",
    [
        {"seed_user_email": ADMIN[0]},  # the same email as the admin
        {"seed_user_password": "short"},  # below the minimum length
        {"seed_user_password": None},  # only half configured
    ],
)
def test_a_user_account_is_not_created_from_unsafe_configuration(engine, session, overrides):
    with TestClient(create_app(settings(**overrides), engine=engine)) as client:
        assert client.get("/api/health").status_code == 200  # the API still starts
    assert {email: user.role for email, user in accounts(session).items()} == {ADMIN[0]: "admin"}


def test_a_password_needs_at_least_eight_characters(engine, session):
    # Seven characters: the User is not created; the API still starts.
    with TestClient(create_app(settings(seed_user_password="Abcd@03"), engine=engine)):
        pass
    assert USER[0] not in accounts(session)
    # Eight characters: created, and it signs in.
    with TestClient(create_app(settings(seed_user_password="Abcd@034"), engine=engine)) as client:
        assert sign_in(client, (USER[0], "Abcd@034")).json()["role"] == "user"


def test_there_is_no_registration(client):
    for path in ("/api/auth/register", "/api/auth/signup", "/api/users", "/api/auth/users"):
        assert client.post(path, json={"email": "new@example.com", "password": "a new password 1"}).status_code in (
            401, 404, 405,
        ), path  # fmt: skip
    assert sign_in(client, ("new@example.com", "a new password 1")).status_code == 401
    assert sign_in(client, ADMIN).status_code == 200
    paths = client.get("/api/openapi.json").json()["paths"]
    assert not [path for path in paths if "register" in path or "signup" in path or path.startswith("/api/users")]


# --- signing in -----------------------------------------------------------------------


def test_admin_and_user_both_sign_in_with_their_own_password(client):
    assert sign_in(client, ADMIN).json()["role"] == "admin"
    assert sign_in(client, USER).json()["role"] == "user"
    # Each password opens its own account only.
    assert sign_in(client, (ADMIN[0], USER[1])).status_code == 401
    assert sign_in(client, (USER[0], ADMIN[1])).status_code == 401


def test_invalid_credentials_are_refused_alike(client):
    wrong = sign_in(client, ADMIN, password="not the admin password")
    unknown = sign_in(client, ("nobody@example.com", "whatever password"))
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_eight_failures_lock_that_account_only(client):
    for _ in range(8):
        assert sign_in(client, USER, password="wrong password").status_code == 401
    # The ninth try, even with the right password, waits out the window.
    assert sign_in(client, USER).status_code == 429
    # The other account is not affected.
    assert sign_in(client, ADMIN).status_code == 200


def test_eight_failures_on_the_admin_do_not_lock_out_the_user(client):
    for _ in range(8):
        assert sign_in(client, ADMIN, password="wrong password").status_code == 401
    assert sign_in(client, ADMIN).status_code == 429
    assert sign_in(client, USER).status_code == 200


# --- what each account may do -----------------------------------------------------------

READ_PATHS = (
    "/api/auth/me", "/api/cities", "/api/sources", "/api/events/summary",
    "/api/events?view=validation", "/api/merge-candidates", "/api/docs",
)  # fmt: skip
# Review decisions and other changes; the event and candidate ids do not exist,
# so an allowed request gets 404/422 and changes nothing.
REVIEW_CHANGES = (
    ("/api/events/EVT-NOSUCHEVENT/status", {"status": "REJECTED", "reason": "test reason"}),
    ("/api/events/EVT-NOSUCHEVENT/severity", {"severity": "LOW", "reason": "test reason"}),
    ("/api/events/EVT-NOSUCHEVENT/extend", {"until": "2030-01-01", "reason": "test reason"}),
    ("/api/merge-candidates/999999/reject", {"reason": "test reason"}),
)


def test_without_signing_in_nothing_but_health_and_sign_in_is_open(client):
    assert client.get("/api/health").status_code == 200
    for path in READ_PATHS:
        assert client.get(path).status_code == 401, path
    for path, body in REVIEW_CHANGES:
        assert client.post(path, json=body, headers=ORIGIN).status_code == 401, path
    assert client.post("/api/ingestion/run", headers=ORIGIN).status_code == 401


@pytest.mark.parametrize("account", [ADMIN, USER], ids=["admin", "user"])
def test_both_accounts_can_use_the_console(client, account):
    assert sign_in(client, account).status_code == 200
    for path in READ_PATHS:
        assert client.get(path).status_code == 200, path


def test_the_user_cannot_change_anything_or_reach_admin_routes(client):
    assert sign_in(client, USER).status_code == 200
    for path, body in REVIEW_CHANGES:
        assert client.post(path, json=body, headers=ORIGIN).status_code == 403, path
    assert client.post("/api/events", json={"title": "x", "basis": "y"}, headers=ORIGIN).status_code == 403
    assert client.post("/api/ingestion/run", headers=ORIGIN).status_code == 403
    assert client.post("/api/ingestion/run", params={"source_id": "telangana-today"}, headers=ORIGIN).status_code == 403


def test_the_admin_reviews_and_runs_sources(client):
    assert sign_in(client, ADMIN).status_code == 200
    for path, body in REVIEW_CHANGES:
        assert client.post(path, json=body, headers=ORIGIN).status_code in (404, 422), path
    # No connector is configured in this test: nothing is fetched.
    assert client.post("/api/ingestion/run", headers=ORIGIN).status_code == 200
    assert client.post("/api/ingestion/run", params={"source_id": "no-such-source"}, headers=ORIGIN).status_code == 404


# --- changing the admin's sign-in email -------------------------------------------------

NEW_ADMIN_EMAIL = "new-admin@example.com"


def snapshot(session):
    """What must survive an email change, per account id."""
    return {
        user.user_id: (user.email, user.password_hash, user.role, user.is_active, user.display_name, user.created_at)
        for user in accounts(session).values()
    }


def test_changing_the_admin_email_keeps_the_account_and_its_password(client, session):
    assert sign_in(client, ADMIN).status_code == 200  # an open admin session
    user_client = TestClient(client.app)
    assert sign_in(user_client, USER).status_code == 200  # and an open user session
    before = snapshot(session)

    change = change_account_email(session, ADMIN[0], NEW_ADMIN_EMAIL, role="admin")
    session.commit()

    after = snapshot(session)
    admin_id = change.user_id
    assert after[admin_id] == (NEW_ADMIN_EMAIL, *before[admin_id][1:])  # same id, hash, role, status
    assert {k: v for k, v in after.items() if k != admin_id} == {k: v for k, v in before.items() if k != admin_id}
    assert len(after) == 2
    # The admin's open sessions ended; the user's did not.
    assert change.sessions_ended == 1
    assert client.get("/api/auth/me").status_code == 401
    assert user_client.get("/api/auth/me").json()["email"] == USER[0]
    # The same password now opens the account with the new email only.
    assert sign_in(client, ADMIN).status_code == 401
    signed_in = sign_in(client, (NEW_ADMIN_EMAIL, ADMIN[1]))
    assert signed_in.status_code == 200 and signed_in.json()["role"] == "admin"
    assert client.post("/api/ingestion/run", headers=ORIGIN).status_code == 200  # still an admin


def test_after_the_change_a_restart_with_either_seed_email_adds_nothing(engine, session, client):
    change_account_email(session, ADMIN[0], NEW_ADMIN_EMAIL)
    session.commit()
    before = snapshot(session)
    for seed_email in (NEW_ADMIN_EMAIL, ADMIN[0]):
        with TestClient(create_app(settings(seed_admin_email=seed_email), engine=engine)):
            pass
        assert snapshot(session) == before


@pytest.mark.parametrize(
    "old, new, reason",
    [
        (ADMIN[0], USER[0], "already used"),  # taken by the user
        (ADMIN[0], " User@Example.COM ", "already used"),  # the same, in another case
        ("nobody@example.com", NEW_ADMIN_EMAIL, "No account"),
        (USER[0], NEW_ADMIN_EMAIL, "is a 'user' account, not 'admin'"),  # not the admin
        (ADMIN[0], "not-an-email", "Not an email"),
        (ADMIN[0], ADMIN[0].upper(), "current email"),
    ],
)
def test_an_email_change_that_is_not_safe_changes_nothing(client, session, old, new, reason):
    assert sign_in(client, ADMIN).status_code == 200
    before = snapshot(session)
    with pytest.raises(ValueError, match=reason):
        change_account_email(session, old, new, role="admin")
    session.rollback()
    assert snapshot(session) == before
    assert client.get("/api/auth/me").status_code == 200  # the session is still open


def test_sessions_can_be_kept(client, session):
    assert sign_in(client, ADMIN).status_code == 200
    change = change_account_email(session, ADMIN[0], NEW_ADMIN_EMAIL, end_sessions=False)
    session.commit()
    assert change.sessions_ended == 0
    assert client.get("/api/auth/me").json()["email"] == NEW_ADMIN_EMAIL
    assert session.scalar(select(AuthSession).where(AuthSession.user_id == change.user_id)) is not None
