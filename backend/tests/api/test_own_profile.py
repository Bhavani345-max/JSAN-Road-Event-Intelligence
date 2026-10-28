"""Each account changes its own name, sign-in email and password (decision 0043).

Both accounts may, the view-only User too: it is their own account, not REI's
data. A new email or password needs the current password; wrong ones count
towards the account's sign-in limit. The browser making the change stays
signed in; the account's other sessions end. No route reaches another account.
"""

from collections import defaultdict

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.routes import auth
from app.core.config import Settings
from app.main import create_app
from app.models import User

ADMIN = ("admin@example.com", "admin test password 1")
USER = ("user@example.com", "user test password 22")
ORIGIN = {"Origin": "http://localhost:3000"}


@pytest.fixture(autouse=True)
def fresh_limits(monkeypatch):
    monkeypatch.setattr(auth, "_LOGIN_ATTEMPTS", defaultdict(auth.deque))


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
    return application


def signed_in(app, account):
    client = TestClient(app)
    email, password = account
    assert client.post("/api/auth/login", json={"email": email, "password": password}).status_code == 200
    return client


def accounts(session):
    session.expire_all()
    return {
        user.user_id: (user.email, user.display_name, user.password_hash, user.role)
        for user in session.scalars(select(User))
    }


def profile(client, **body):
    return client.post("/api/auth/profile", json=body, headers=ORIGIN)


def password(client, current, new):
    return client.post("/api/auth/password", json={"current_password": current, "new_password": new}, headers=ORIGIN)


@pytest.mark.parametrize("account", [ADMIN, USER], ids=["admin", "user"])
def test_each_account_renames_itself(app, account):
    with TestClient(app):
        client = signed_in(app, account)
        response = profile(client, display_name="  Pavan   Kumar ")
        assert response.status_code == 200
        assert response.json()["display_name"] == "Pavan Kumar"
        assert response.json()["email"] == account[0]
        assert client.get("/api/auth/me").json()["display_name"] == "Pavan Kumar"


def test_a_name_cannot_be_blank_or_too_long(app, session):
    with TestClient(app):
        client = signed_in(app, ADMIN)
        before = accounts(session)
        assert profile(client, display_name="   ").status_code == 422
        assert profile(client, display_name="x" * 121).status_code == 422
        assert accounts(session) == before


def test_a_new_email_needs_the_current_password(app, session):
    with TestClient(app):
        client = signed_in(app, ADMIN)
        before = accounts(session)
        assert profile(client, email="new-admin@example.com").status_code == 400
        wrong = profile(client, email="new-admin@example.com", current_password="not it at all")
        assert wrong.status_code == 400 and wrong.json()["detail"] == "The current password is incorrect."
        assert accounts(session) == before
        # The same email (in another case) is no change and needs no password.
        assert profile(client, email=" Admin@Example.com ", display_name="Admin").status_code == 200


def test_a_new_email_keeps_this_session_and_ends_the_others(app, session):
    with TestClient(app):
        client = signed_in(app, ADMIN)
        other_browser = signed_in(app, ADMIN)
        user_browser = signed_in(app, USER)
        response = profile(client, email="New-Admin@Example.com", current_password=ADMIN[1])
        assert response.status_code == 200
        assert response.json() == {**response.json(), "email": "new-admin@example.com", "role": "admin"}
        assert client.get("/api/auth/me").json()["email"] == "new-admin@example.com"
        assert other_browser.get("/api/auth/me").status_code == 401
        assert user_browser.get("/api/auth/me").json()["email"] == USER[0]
        fresh = TestClient(app)
        assert fresh.post("/api/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]}).status_code == 401
        assert fresh.post("/api/auth/login", json={"email": "new-admin@example.com", "password": ADMIN[1]}).status_code == 200
        assert len(accounts(session)) == 2


@pytest.mark.parametrize("email", [USER[0], " USER@example.com", "not-an-email"])
def test_an_email_that_is_taken_or_not_one_changes_nothing(app, session, email):
    with TestClient(app):
        client = signed_in(app, ADMIN)
        before = accounts(session)
        response = profile(client, email=email, display_name="Changed too", current_password=ADMIN[1])
        assert response.status_code == 400
        assert accounts(session) == before
        assert client.get("/api/auth/me").status_code == 200


@pytest.mark.parametrize("account", [ADMIN, USER], ids=["admin", "user"])
def test_each_account_changes_its_own_password(app, session, account):
    with TestClient(app):
        client = signed_in(app, account)
        other_browser = signed_in(app, account)
        assert password(client, account[1], "a brand new password").json() == {"ok": True}
        assert client.get("/api/auth/me").status_code == 200  # this browser stays signed in
        assert other_browser.get("/api/auth/me").status_code == 401
        fresh = TestClient(app)
        assert fresh.post("/api/auth/login", json={"email": account[0], "password": account[1]}).status_code == 401
        assert fresh.post("/api/auth/login", json={"email": account[0], "password": "a brand new password"}).status_code == 200


def test_a_wrong_current_password_or_a_short_new_one_changes_nothing(app, session):
    with TestClient(app):
        client = signed_in(app, ADMIN)
        before = accounts(session)
        wrong = password(client, "not the password", "a brand new password")
        assert wrong.status_code == 400 and wrong.json()["detail"] == "The current password is incorrect."
        short = password(client, ADMIN[1], "short")
        assert short.status_code == 400 and "at least 8 characters" in short.json()["detail"]
        assert accounts(session) == before


def test_wrong_current_passwords_count_towards_the_sign_in_limit(app):
    with TestClient(app):
        client = signed_in(app, ADMIN)
        for _ in range(4):
            assert password(client, "guess", "a brand new password").status_code == 400
        assert password(client, "guess", "a brand new password").status_code == 429  # the fifth locks
        assert password(client, ADMIN[1], "a brand new password").status_code == 429
        assert profile(client, email="x@example.com", current_password=ADMIN[1]).status_code == 429
        fresh = TestClient(app)
        assert fresh.post("/api/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]}).status_code == 429
        # The other account is not affected.
        assert fresh.post("/api/auth/login", json={"email": USER[0], "password": USER[1]}).status_code == 200


def test_a_profile_change_never_reaches_the_role_or_another_account(app, session):
    with TestClient(app):
        client = signed_in(app, USER)
        before = accounts(session)
        response = profile(client, role="admin", user_id="someone-else", display_name="Viewer")
        assert response.status_code == 200 and response.json()["role"] == "user"
        after = accounts(session)
        user_id = next(key for key, values in before.items() if values[0] == USER[0])
        assert after[user_id] == (USER[0], "Viewer", before[user_id][2], "user")
        assert {k: v for k, v in after.items() if k != user_id} == {k: v for k, v in before.items() if k != user_id}
        # Still view-only for REI's data.
        assert client.post("/api/ingestion/run", headers=ORIGIN).status_code == 403


def test_without_a_session_or_from_another_website_nothing_changes(app, session):
    with TestClient(app):
        before = accounts(session)
        anonymous = TestClient(app)
        assert profile(anonymous, display_name="x").status_code == 401
        assert password(anonymous, ADMIN[1], "a brand new password").status_code == 401
        client = signed_in(app, ADMIN)
        elsewhere = {"Origin": "https://evil.example"}
        assert client.post("/api/auth/profile", json={"display_name": "x"}, headers=elsewhere).status_code == 403
        assert client.post(
            "/api/auth/password",
            json={"current_password": ADMIN[1], "new_password": "a brand new password"},
            headers=elsewhere,
        ).status_code == 403
        assert accounts(session) == before
