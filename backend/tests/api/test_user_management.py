"""Accounts made by administrators, no self-registration (decision 0046).

The user's brief of 28 October 2026: registration off; an administrator creates
accounts (name, email, Admin or User), changes roles, deactivates and activates
them, and resets passwords; a temporary password is shown once and replaced at
the next sign-in; nothing needs an email service. Every test runs on an
in-memory database with test accounts and no email configuration at all.
"""

import logging
from collections import defaultdict

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.routes import auth
from app.core.config import Settings
from app.main import create_app
from app.models import SecurityEvent, User

ADMIN = ("admin@example.com", "admin test password 1")
USER = ("user@example.com", "user test password 22")
ORIGIN = {"Origin": "http://localhost:3000"}
NEW_PASSWORD = "my own new password 9"


@pytest.fixture(autouse=True)
def fresh_limits(monkeypatch):
    monkeypatch.setattr(auth, "_LOGIN_ATTEMPTS", defaultdict(auth.deque))
    monkeypatch.setattr(auth, "_REQUESTS", defaultdict(auth.deque))


def settings(**overrides) -> Settings:
    values = {
        "_env_file": None, "database_url": "sqlite://", "auto_migrate": False,
        "ingestion_scheduler_enabled": False,
        "seed_admin_email": ADMIN[0], "seed_admin_password": ADMIN[1],
        "seed_user_email": USER[0], "seed_user_password": USER[1],
    }  # fmt: skip
    return Settings(**(values | overrides))


@pytest.fixture
def app(engine):
    application = create_app(settings(), engine=engine)
    application.state.ingestion_service.connector_factories = {}
    with TestClient(application):
        yield application


def sign_in(app, email, password):
    browser = TestClient(app)
    return browser, browser.post("/api/auth/login", json={"email": email, "password": password})


def signed_in(app, account):
    browser, response = sign_in(app, *account)
    assert response.status_code == 200, response.json()
    return browser


def create(browser, name="Asha Rao", email="asha.rao@example.com", role="user", password=ADMIN[1]):
    return browser.post(
        "/api/admin/users",
        json={"display_name": name, "email": email, "role": role, "current_password": password},
        headers=ORIGIN,
    )


def accounts(session):
    session.expire_all()
    return {user.email: user for user in session.scalars(select(User))}


def kinds(session, email):
    session.expire_all()
    user_id = session.scalar(select(User.user_id).where(User.email == email))
    return [e.kind for e in session.scalars(select(SecurityEvent).where(SecurityEvent.account_id == user_id).order_by(SecurityEvent.occurred_at))]


# --- 1. no public registration, no email needed ---------------------------------------------


def test_registration_is_off_even_with_email_configured(engine):
    """Off unless REGISTRATION_ENABLED is set, whatever else is configured."""
    configured = settings(
        email_provider="resend", email_api_key="k", email_from="REI <rei@example.com>",
        app_base_url="https://rei.example", allowed_email_domains="example.com",
    )  # fmt: skip
    application = create_app(configured, engine=engine)
    application.state.ingestion_service.connector_factories = {}
    with TestClient(application) as browser:
        assert browser.get("/api/auth/options").json()["registration_open"] is False
        body = {"full_name": "A B", "email": "a.b@example.com", "password": "long enough phrase 7"}
        assert browser.post("/api/auth/register", json=body).status_code == 404
        assert browser.post("/api/auth/verify-email", json={"token": "x"}).status_code == 404


def test_everything_works_without_any_email_setting(app, session):
    assert app.state.email_sender is None
    assert TestClient(app).get("/api/auth/options").json() == {
        "registration_open": False, "email_reset": False, "allowed_domains": [],
    }  # fmt: skip
    # Email reset links say plainly they are unavailable; nothing pretends to send.
    forgot = TestClient(app).post("/api/auth/forgot", json={"email": USER[0]})
    assert forgot.status_code == 503 and "not available" in forgot.json()["detail"]
    # Creating an account and resetting a password need no email.
    admin = signed_in(app, ADMIN)
    assert create(admin).status_code == 201
    target = accounts(session)[USER[0]].user_id
    reset = admin.post(f"/api/auth/accounts/{target}/temporary-password", json={"current_password": ADMIN[1]}, headers=ORIGIN)
    assert reset.status_code == 200


# --- 2, 3. the administrator creates accounts and gives roles --------------------------------


def test_an_administrator_creates_a_view_only_user(app, session, caplog):
    caplog.set_level(logging.DEBUG)
    response = create(signed_in(app, ADMIN), name="  Asha   Rao ", email=" Asha.Rao@Example.com ")
    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    temporary = body["temporary_password"]
    assert (body["account"]["display_name"], body["account"]["email"], body["account"]["role"], body["account"]["status"]) == (
        "Asha Rao", "asha.rao@example.com", "user", "active",
    )  # fmt: skip
    assert body["account"]["must_change_password"] is True and body["account"]["decided_by"] == "Admin"
    stored = accounts(session)["asha.rao@example.com"]
    assert temporary not in stored.password_hash and stored.password_hash.startswith("pbkdf2_sha256$")
    # The first sign-in: the temporary password, then nothing but choosing one's own.
    browser, signed = sign_in(app, "asha.rao@example.com", temporary)
    assert signed.status_code == 200 and signed.json()["must_change_password"] is True
    assert browser.get("/api/events").status_code == 403
    assert browser.post("/api/auth/password", json={"current_password": temporary, "new_password": NEW_PASSWORD}, headers=ORIGIN).json() == {"ok": True}
    # Now view-only: reads, changes nothing, no administration.
    assert browser.get("/api/events").status_code == 200
    assert browser.post("/api/ingestion/run", headers=ORIGIN).status_code == 403
    assert browser.get("/api/admin/users").status_code == 403
    assert kinds(session, "asha.rao@example.com")[:2] == ["account_created", "temporary_password_set"]
    assert temporary not in caplog.text
    assert all(temporary not in str(event.detail) for event in session.scalars(select(SecurityEvent)))


def test_an_administrator_creates_another_administrator(app):
    temporary = create(signed_in(app, ADMIN), name="Ravi Admin", email="ravi@example.com", role="admin").json()["temporary_password"]
    browser, _ = sign_in(app, "ravi@example.com", temporary)
    browser.post("/api/auth/password", json={"current_password": temporary, "new_password": NEW_PASSWORD}, headers=ORIGIN)
    assert browser.get("/api/admin/users").status_code == 200
    assert browser.post("/api/ingestion/run", headers=ORIGIN).status_code == 200


@pytest.mark.parametrize("email", [USER[0], "USER@Example.COM", " user@example.com "])
def test_an_email_already_used_cannot_get_a_second_account(app, session, email):
    before = accounts(session)
    response = create(signed_in(app, ADMIN), email=email)
    assert response.status_code == 409 and response.json()["detail"] == "An account with this email already exists."
    assert accounts(session).keys() == before.keys()


@pytest.mark.parametrize(
    "changes",
    [{"role": "reviewer"}, {"role": "superuser"}, {"name": "   "}, {"email": "not-an-email"}, {"name": "x" * 121}],
)
def test_a_new_account_needs_a_name_an_email_and_admin_or_user(app, session, changes):
    before = accounts(session)
    assert create(signed_in(app, ADMIN), **changes).status_code == 422
    assert accounts(session).keys() == before.keys()


def test_creating_needs_the_administrators_own_password(app, session):
    admin = signed_in(app, ADMIN)
    wrong = create(admin, password="not my password")
    assert wrong.status_code == 400 and wrong.json()["detail"] == "The current password is incorrect."
    assert "asha.rao@example.com" not in accounts(session)


# --- 4. nobody else creates accounts, changes roles or reaches administration ----------------


def test_only_an_administrator_manages_accounts(app, session):
    target = accounts(session)[ADMIN[0]].user_id
    anonymous, user = TestClient(app), signed_in(app, USER)
    for browser, status in ((anonymous, 401), (user, 403)):
        assert create(browser, password=USER[1]).status_code == status
        assert browser.post(f"/api/admin/users/{target}/role", json={"role": "user", "current_password": USER[1]}, headers=ORIGIN).status_code == status
        assert browser.post(f"/api/admin/users/{target}/suspend", headers=ORIGIN).status_code == status
        assert browser.post(f"/api/auth/accounts/{target}/temporary-password", json={"current_password": USER[1]}, headers=ORIGIN).status_code == status
        assert browser.get("/api/admin/users").status_code == status
        assert browser.get(f"/api/admin/users/{target}/history").status_code == status
    # Signed in as an administrator, but from another website: refused.
    admin = signed_in(app, ADMIN)
    foreign = admin.post("/api/admin/users", json={"display_name": "X", "email": "x@example.com", "role": "admin", "current_password": ADMIN[1]}, headers={"Origin": "https://evil.example"})
    assert foreign.status_code == 403
    assert set(accounts(session)) == {ADMIN[0], USER[0]}
    assert accounts(session)[ADMIN[0]].role == "admin"


def role(browser, account_id, new_role, password=ADMIN[1]):
    return browser.post(f"/api/admin/users/{account_id}/role", json={"role": new_role, "current_password": password}, headers=ORIGIN)


def test_an_administrator_changes_another_accounts_role(app, session):
    admin = signed_in(app, ADMIN)
    user_browser = signed_in(app, USER)
    target = accounts(session)[USER[0]].user_id
    promoted = role(admin, target, "admin")
    assert promoted.status_code == 200 and promoted.json()["role"] == "admin"
    assert user_browser.get("/api/admin/users").status_code == 200  # at once, same session
    demoted = role(admin, target, "user")
    assert demoted.status_code == 200 and demoted.json()["role"] == "user"
    assert user_browser.get("/api/admin/users").status_code == 403
    assert kinds(session, USER[0])[-2:] == ["role_changed", "role_changed"]
    assert role(admin, target, "user").status_code == 409  # already
    assert role(admin, target, "admin", password="wrong").status_code == 400


def test_an_administrator_cannot_change_their_own_role_or_leave_no_administrator(app, session):
    admin = signed_in(app, ADMIN)
    own = accounts(session)[ADMIN[0]].user_id
    refused = role(admin, own, "user")
    assert refused.status_code == 409 and "your own role" in refused.json()["detail"]
    assert accounts(session)[ADMIN[0]].role == "admin"


def test_deactivated_accounts_are_stopped_and_can_be_activated_again(app, session):
    user_browser = signed_in(app, USER)
    admin = signed_in(app, ADMIN)
    target = accounts(session)[USER[0]].user_id
    assert admin.post(f"/api/admin/users/{target}/suspend", headers=ORIGIN).json()["status"] == "suspended"
    assert user_browser.get("/api/events").status_code == 401
    _, refused = sign_in(app, *USER)
    assert refused.status_code == 403 and "deactivated" in refused.json()["detail"]
    assert role(admin, target, "admin").status_code == 409  # not while deactivated
    assert admin.post(f"/api/admin/users/{target}/reactivate", headers=ORIGIN).json()["status"] == "active"
    assert sign_in(app, *USER)[1].status_code == 200


# --- 5, 7. existing sign-in, and the administrator's reset without email ---------------------


def test_existing_accounts_sign_in_and_out_as_before(app):
    for account in (ADMIN, USER):
        browser = signed_in(app, account)
        assert browser.get("/api/auth/me").json()["must_change_password"] is False
        assert browser.post("/api/auth/logout", headers=ORIGIN).json() == {"ok": True}
        assert browser.get("/api/auth/me").status_code == 401


def test_an_administrator_resets_another_administrators_password_but_not_their_own(app, session):
    admin = signed_in(app, ADMIN)
    temporary = create(admin, name="Second Admin", email="second@example.com", role="admin").json()["temporary_password"]
    second, _ = sign_in(app, "second@example.com", temporary)
    second.post("/api/auth/password", json={"current_password": temporary, "new_password": NEW_PASSWORD}, headers=ORIGIN)
    second_id = accounts(session)["second@example.com"].user_id
    reset = admin.post(f"/api/auth/accounts/{second_id}/temporary-password", json={"current_password": ADMIN[1]}, headers=ORIGIN)
    assert reset.status_code == 200
    assert second.get("/api/auth/me").status_code == 401  # signed out everywhere
    _, again = sign_in(app, "second@example.com", reset.json()["temporary_password"])
    assert again.json()["must_change_password"] is True
    own = admin.post(f"/api/auth/accounts/{accounts(session)[ADMIN[0]].user_id}/temporary-password", json={"current_password": ADMIN[1]}, headers=ORIGIN)
    assert own.status_code == 400 and "Your own password" in own.json()["detail"]
