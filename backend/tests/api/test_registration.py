"""Registration, email verification, administrator approval and reset links (decision 0045).

Self-registration is off by default (decision 0046, test_user_management.py);
these tests switch it on (REGISTRATION_ENABLED) to keep the dormant flow working
for the day it is opened again. A test email service records what would be sent;
no email leaves the tests. Every test runs on an in-memory database.
"""

import logging
import re
from collections import defaultdict
from datetime import timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.api.routes import auth
from app.core.config import Settings
from app.main import create_app
from app.models import AuthSession, EmailToken, SecurityEvent, User
from app.services.email_service import EmailDeliveryFailed, EmailMessage, ResendSender, send_quietly
from packages.common.time import utc_now

ADMIN = ("admin@example.com", "admin test password 1")
USER = ("user@example.com", "user test password 22")
ORIGIN = {"Origin": "http://localhost:3000"}
NEW = ("Pavan Kumar", "pavan@jsan.example", "long enough phrase 7")
GENERIC = "Thank you. If this email can be registered"


class Outbox:
    """Stands in for the email service: keeps every message it is given."""

    def __init__(self):
        self.messages: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.messages.append(message)

    def link(self, path: str) -> str:
        """The token of the last link to `path`."""
        for message in reversed(self.messages):
            found = re.search(rf"{path}\?token=([\w-]+)", message.text)
            if found:
                return found.group(1)
        raise AssertionError(f"no {path} link was sent")


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
        "email_provider": "resend", "email_api_key": "test-key", "email_from": "REI <rei@jsan.example>",
        "app_base_url": "https://rei.example", "allowed_email_domains": "jsan.example, JSAN-group.example",
        "registration_enabled": True,
    }  # fmt: skip
    return Settings(**(values | overrides))


@pytest.fixture
def outbox():
    return Outbox()


@pytest.fixture
def app(engine, outbox):
    application = create_app(settings(), engine=engine)
    application.state.ingestion_service.connector_factories = {}
    application.state.email_sender = outbox
    with TestClient(application):
        yield application


def client(app):
    return TestClient(app)


def sign_in(app, email, password):
    browser = client(app)
    return browser, browser.post("/api/auth/login", json={"email": email, "password": password})


def signed_in(app, account):
    browser, response = sign_in(app, *account)
    assert response.status_code == 200, response.json()
    return browser


def register(app, name=NEW[0], email=NEW[1], password=NEW[2], **extra):
    return client(app).post("/api/auth/register", json={"full_name": name, "email": email, "password": password, **extra})


def account(session, email):
    session.expire_all()
    return session.scalar(select(User).where(User.email == email))


def kinds(session, user):
    session.expire_all()
    return [event.kind for event in session.scalars(select(SecurityEvent).where(SecurityEvent.account_id == user.user_id).order_by(SecurityEvent.occurred_at))]


def registered_and_verified(app, outbox):
    assert register(app).status_code == 202
    assert client(app).post("/api/auth/verify-email", json={"token": outbox.link("/verify-email")}).status_code == 200


# --- registering --------------------------------------------------------------------------


def test_a_registration_waits_for_its_email_and_an_administrator(app, session, outbox):
    response = register(app, name="  Pavan   Kumar ", email=" Pavan@JSAN.example ")
    assert response.status_code == 202 and response.json()["message"].startswith(GENERIC)
    user = account(session, NEW[1])
    assert (user.display_name, user.role, user.status) == ("Pavan Kumar", "user", "pending_approval")
    assert user.email_verified_at is None and user.registered_at is not None
    assert NEW[2] not in user.password_hash and user.password_hash.startswith("pbkdf2_sha256$")
    # One email, to that address, with a single-use link stored only as a digest.
    [message] = outbox.messages
    assert message.to == NEW[1] and "/verify-email?token=" in message.text
    token = outbox.link("/verify-email")
    assert len(token) >= 40
    assert session.scalar(select(EmailToken.token_hash)) != token
    # Waiting: no sign-in yet, and the reason only for whoever knows the password.
    _, refused = sign_in(app, NEW[1], NEW[2])
    assert refused.status_code == 403 and "Confirm your email first" in refused.json()["detail"]
    assert "rei_session" not in refused.cookies
    assert kinds(session, user) == ["registered"]


def test_options_say_what_the_sign_in_page_can_offer(app):
    assert client(app).get("/api/auth/options").json() == {
        "registration_open": True, "email_reset": True, "allowed_domains": ["jsan-group.example", "jsan.example"],
    }  # fmt: skip


@pytest.mark.parametrize("email", ["pavan@gmail.com", "pavan@jsan.example.evil.com", "pavan@sub.jsan.example"])
def test_only_company_domains_may_register(app, session, outbox, email):
    response = register(app, email=email)
    assert response.status_code == 400 and "company email" in response.json()["detail"]
    assert account(session, email) is None and not outbox.messages


@pytest.mark.parametrize(
    "password, reason",
    [("short", "at least 8"), ("password123", "too easy"), ("aaaaaaaaaaaa", "too easy"), ("pavan-secret-99", "email's name")],
)
def test_weak_passwords_are_refused(app, session, outbox, password, reason):
    response = register(app, password=password)
    assert response.status_code == 400 and reason in response.json()["detail"]
    assert account(session, NEW[1]) is None and not outbox.messages


@pytest.mark.parametrize("body", [{"full_name": " ", "email": NEW[1], "password": NEW[2]}, {"full_name": "A", "email": "not-an-email", "password": NEW[2]}])
def test_a_blank_name_or_malformed_email_is_refused(app, body):
    assert client(app).post("/api/auth/register", json=body).status_code == 422


def test_a_registration_cannot_choose_a_role(app, session):
    assert register(app, role="admin", status="active", is_active=True).status_code == 202
    user = account(session, NEW[1])
    assert (user.role, user.status) == ("user", "pending_approval")


def test_a_taken_email_gets_the_same_answer_and_nothing_changes(app, session, outbox):
    taken = register(app, email=USER[0].replace("example.com", "jsan.example"))  # free: a real registration
    assert taken.status_code == 202
    outbox.messages.clear()
    # The seeded User's address is not a company one here; use an active company account instead.
    user = account(session, USER[0].replace("example.com", "jsan.example"))
    session.execute(update(User).where(User.user_id == user.user_id).values(status="active", email_verified_at=utc_now()))
    session.commit()
    before = account(session, user.email).password_hash
    again = register(app, email=user.email, password="a different password 5")
    assert (again.status_code, again.json()) == (taken.status_code, taken.json())
    assert account(session, user.email).password_hash == before
    assert not outbox.messages  # an active account gets no link
    assert session.scalar(select(User).where(User.email == user.email)) is not None
    assert len(session.scalars(select(User).where(User.email == user.email)).all()) == 1


def test_registering_again_before_confirming_sends_a_new_link_and_ends_the_old(app, session, outbox):
    assert register(app).status_code == 202
    first = outbox.link("/verify-email")
    assert register(app, password="another fine password 2").status_code == 202
    second = outbox.link("/verify-email")
    assert first != second
    assert client(app).post("/api/auth/verify-email", json={"token": first}).status_code == 400
    assert client(app).post("/api/auth/verify-email", json={"token": second}).status_code == 200
    # The password stays the first one: a second request cannot change it.
    assert sign_in(app, NEW[1], NEW[2])[1].json()["detail"].startswith("Your registration is waiting")


# --- confirming the email ----------------------------------------------------------------


def test_a_link_confirms_the_email_once(app, session, outbox):
    assert register(app).status_code == 202
    token = outbox.link("/verify-email")
    assert client(app).post("/api/auth/verify-email", json={"token": token}).json() == {"ok": True}
    user = account(session, NEW[1])
    assert user.email_verified_at is not None and user.status == "pending_approval"
    reused = client(app).post("/api/auth/verify-email", json={"token": token})
    assert reused.status_code == 400 and "not valid" in reused.json()["detail"]
    _, waiting = sign_in(app, NEW[1], NEW[2])
    assert waiting.status_code == 403 and "waiting for an administrator" in waiting.json()["detail"]
    assert kinds(session, user) == ["registered", "email_verified"]


def test_an_expired_or_unknown_link_is_refused(app, session, outbox):
    assert register(app).status_code == 202
    token = outbox.link("/verify-email")
    session.execute(update(EmailToken).values(expires_at=utc_now() - timedelta(minutes=1)))
    session.commit()
    for bad in (token, "made-up-token", token[:-1] + ("A" if token[-1] != "A" else "B")):
        assert client(app).post("/api/auth/verify-email", json={"token": bad}).status_code == 400
    assert account(session, NEW[1]).email_verified_at is None


def test_wrong_links_are_limited(app, monkeypatch):
    monkeypatch.setattr(auth, "_LINK_FAILURE_LIMIT", 3)
    for _ in range(3):
        assert client(app).post("/api/auth/verify-email", json={"token": "guess"}).status_code == 400
    assert client(app).post("/api/auth/verify-email", json={"token": "guess"}).status_code == 429
    assert client(app).post("/api/auth/reset-password", json={"token": "guess", "new_password": "fine new password 1"}).status_code == 429


def test_registrations_are_limited_per_email(app):
    assert [register(app).status_code for _ in range(4)] == [202, 202, 202, 429]
    assert register(app, email="someone.else@jsan.example").status_code == 202


# --- the administrator decides -----------------------------------------------------------


def test_an_administrator_approves_a_confirmed_registration(app, session, outbox):
    registered_and_verified(app, outbox)
    user = account(session, NEW[1])
    admin = signed_in(app, ADMIN)
    listed = admin.get("/api/admin/users").json()
    assert listed[0]["email"] == NEW[1] and listed[0]["status"] == "pending_approval" and listed[0]["email_verified"] is True
    approved = admin.post(f"/api/admin/users/{user.user_id}/approve", headers=ORIGIN)
    assert approved.status_code == 200
    assert (approved.json()["status"], approved.json()["role"], approved.json()["decided_by"]) == ("active", "user", "Admin")
    assert outbox.messages[-1].to == NEW[1] and "approved" in outbox.messages[-1].text
    browser, signed = sign_in(app, NEW[1], NEW[2])
    assert signed.status_code == 200 and signed.json()["role"] == "user"
    assert browser.get("/api/events").status_code == 200
    assert browser.post("/api/ingestion/run", headers=ORIGIN).status_code == 403  # view-only
    session.expire_all()
    stored = account(session, NEW[1])
    assert stored.decided_by == account(session, ADMIN[0]).user_id and stored.decided_at is not None
    assert kinds(session, stored)[-1] == "account_approved"
    history = admin.get(f"/api/admin/users/{user.user_id}/history").json()
    assert [(item["kind"], item["by"]) for item in history][:2] == [("account_approved", "Admin"), ("email_verified", NEW[0])]


def test_an_unconfirmed_registration_cannot_be_approved(app, session):
    assert register(app).status_code == 202
    user = account(session, NEW[1])
    refused = signed_in(app, ADMIN).post(f"/api/admin/users/{user.user_id}/approve", headers=ORIGIN)
    assert refused.status_code == 409 and "not confirmed its email" in refused.json()["detail"]
    assert account(session, NEW[1]).status == "pending_approval"


def test_a_rejected_registration_never_gets_in(app, session, outbox):
    registered_and_verified(app, outbox)
    user = account(session, NEW[1])
    rejected = signed_in(app, ADMIN).post(f"/api/admin/users/{user.user_id}/reject", headers=ORIGIN)
    assert rejected.status_code == 200 and rejected.json()["status"] == "rejected"
    assert "not approved" in outbox.messages[-1].text
    _, refused = sign_in(app, NEW[1], NEW[2])
    assert refused.status_code == 403 and "not approved" in refused.json()["detail"]
    assert signed_in(app, ADMIN).post(f"/api/admin/users/{user.user_id}/approve", headers=ORIGIN).status_code == 409
    assert kinds(session, user)[-1] == "account_rejected"


def test_only_an_administrator_decides(app, session, outbox):
    registered_and_verified(app, outbox)
    target = account(session, NEW[1]).user_id
    for action in ("approve", "reject", "suspend", "reactivate"):
        assert client(app).post(f"/api/admin/users/{target}/{action}", headers=ORIGIN).status_code == 401
        assert signed_in(app, USER).post(f"/api/admin/users/{target}/{action}", headers=ORIGIN).status_code == 403
    assert client(app).get("/api/admin/users").status_code == 401
    assert signed_in(app, USER).get("/api/admin/users").status_code == 403
    assert signed_in(app, USER).get(f"/api/admin/users/{target}/history").status_code == 403
    admin = signed_in(app, ADMIN)
    assert admin.post(f"/api/admin/users/{target}/approve", headers={"Origin": "https://evil.example"}).status_code == 403
    assert admin.post("/api/admin/users/no-such-id/approve", headers=ORIGIN).status_code == 404
    assert account(session, NEW[1]).status == "pending_approval"


def test_a_suspended_account_is_stopped_at_once_and_can_be_reactivated(app, session):
    user_browser = signed_in(app, USER)
    target = account(session, USER[0]).user_id
    admin = signed_in(app, ADMIN)
    assert admin.post(f"/api/admin/users/{target}/suspend", headers=ORIGIN).json()["status"] == "suspended"
    assert user_browser.get("/api/events").status_code == 401  # its session ended
    assert session.scalar(select(AuthSession).where(AuthSession.user_id == target)) is None
    _, refused = sign_in(app, *USER)
    assert refused.status_code == 403 and "deactivated" in refused.json()["detail"]
    assert admin.post(f"/api/admin/users/{target}/reactivate", headers=ORIGIN).json()["status"] == "active"
    assert sign_in(app, *USER)[1].status_code == 200
    assert kinds(session, account(session, USER[0]))[-2:] == ["account_suspended", "account_reactivated"]


def test_an_administrator_cannot_suspend_themselves_or_the_last_administrator(app, session):
    admin = signed_in(app, ADMIN)
    own = account(session, ADMIN[0]).user_id
    refused = admin.post(f"/api/admin/users/{own}/suspend", headers=ORIGIN)
    assert refused.status_code == 409 and "your own" in refused.json()["detail"]
    assert admin.get("/api/auth/me").status_code == 200


def test_a_session_of_an_account_no_longer_active_reaches_nothing(app, session):
    """Even a session that existed before the status changed (a direct database change)."""
    browser = signed_in(app, USER)
    session.execute(update(User).where(User.email == USER[0]).values(status="pending_approval"))
    session.commit()
    for path in ("/api/auth/me", "/api/events", "/api/sources", "/api/cities"):
        assert browser.get(path).status_code == 401, path


# --- reset links -------------------------------------------------------------------------


def approved_member(app, session, outbox):
    registered_and_verified(app, outbox)
    signed_in(app, ADMIN).post(f"/api/admin/users/{account(session, NEW[1]).user_id}/approve", headers=ORIGIN)
    outbox.messages.clear()


def forgot(app, email):
    return client(app).post("/api/auth/forgot", json={"email": email})


def reset(app, token, password="a fresh password 42"):
    return client(app).post("/api/auth/reset-password", json={"token": token, "new_password": password})


def test_a_reset_link_sets_a_new_password_once(app, session, outbox, caplog):
    caplog.set_level(logging.DEBUG)
    approved_member(app, session, outbox)
    browser = signed_in(app, (NEW[1], NEW[2]))
    answer = forgot(app, NEW[1])
    assert answer.status_code == 202 and answer.json()["message"].startswith("If an active account")
    token = outbox.link("/reset-password")
    assert reset(app, token).json() == {"ok": True}
    assert browser.get("/api/auth/me").status_code == 401  # signed out everywhere
    assert sign_in(app, NEW[1], NEW[2])[1].status_code == 401
    assert sign_in(app, NEW[1], "a fresh password 42")[1].status_code == 200
    assert "was just changed" in outbox.messages[-1].text  # the notice
    reused = reset(app, token, "yet another password 3")
    assert reused.status_code == 400 and "not valid" in reused.json()["detail"]
    assert kinds(session, account(session, NEW[1]))[-2:] == ["password_reset_requested", "password_reset_with_link"]
    assert token not in caplog.text and NEW[2] not in caplog.text and "a fresh password 42" not in caplog.text


def test_a_reset_link_expires_and_a_new_one_ends_the_old(app, session, outbox):
    approved_member(app, session, outbox)
    forgot(app, NEW[1])
    first = outbox.link("/reset-password")
    forgot(app, NEW[1])
    second = outbox.link("/reset-password")
    assert reset(app, first).status_code == 400
    session.execute(update(EmailToken).where(EmailToken.purpose == "reset_password").values(expires_at=utc_now() - timedelta(seconds=1)))
    session.commit()
    assert reset(app, second).status_code == 400
    assert sign_in(app, NEW[1], NEW[2])[1].status_code == 200  # unchanged


def test_a_refused_password_does_not_use_the_link(app, session, outbox):
    approved_member(app, session, outbox)
    forgot(app, NEW[1])
    token = outbox.link("/reset-password")
    assert "too easy" in reset(app, token, "password123").json()["detail"]
    assert reset(app, token).status_code == 200


@pytest.mark.parametrize("who", ["unknown", "pending registration", "seeded, email never confirmed"])
def test_only_an_active_account_with_a_confirmed_email_gets_a_link_and_the_answer_is_the_same(app, session, outbox, who):
    if who == "pending registration":
        assert register(app).status_code == 202
        email = NEW[1]
    else:
        email = "nobody@jsan.example" if who == "unknown" else ADMIN[0]
    outbox.messages.clear()
    answer = forgot(app, email)
    assert answer.status_code == 202 and answer.json()["message"].startswith("If an active account")
    assert not [message for message in outbox.messages if "/reset-password" in message.text]


def test_reset_requests_are_limited_per_email(app):
    assert [forgot(app, "someone@jsan.example").status_code for _ in range(4)] == [202, 202, 202, 429]


def test_without_email_reset_links_say_they_are_unavailable(engine):
    application = create_app(settings(email_api_key=None), engine=engine)
    application.state.ingestion_service.connector_factories = {}
    with TestClient(application) as browser:
        assert application.state.email_sender is None
        answer = browser.post("/api/auth/forgot", json={"email": ADMIN[0]})
        assert answer.status_code == 503 and "not available" in answer.json()["detail"]
        assert browser.post("/api/auth/register", json={"full_name": "A B", "email": NEW[1], "password": NEW[2]}).status_code == 503
        assert browser.get("/api/auth/options").json()["email_reset"] is False


def test_the_existing_accounts_still_sign_in_as_before(app):
    for email, password in (ADMIN, USER):
        browser, signed = sign_in(app, email, password)
        assert signed.status_code == 200 and browser.get("/api/events").status_code == 200
    assert signed_in(app, ADMIN).post("/api/ingestion/run", headers=ORIGIN).status_code == 200


# --- the email service --------------------------------------------------------------------


def test_resend_gets_the_message_with_the_key_and_nothing_else(caplog):
    seen = []

    def answer(request):
        seen.append(request)
        return httpx.Response(200, json={"id": "test"})

    sender = ResendSender("key-123", "REI <rei@jsan.example>", httpx.Client(transport=httpx.MockTransport(answer)))
    message = EmailMessage(to="a@jsan.example", subject="S", text="secret link https://x/?token=abc", kind="password reset link")
    assert send_quietly(sender, message) is True
    [request] = seen
    assert request.headers["authorization"] == "Bearer key-123"
    assert request.url == httpx.URL("https://api.resend.com/emails")
    assert b'"to":["a@jsan.example"]' in request.content.replace(b" ", b"")


def test_a_refused_email_is_reported_without_its_contents(caplog):
    caplog.set_level(logging.DEBUG)
    sender = ResendSender("key-123", "REI <rei@jsan.example>", httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(422))))
    message = EmailMessage(to="a@jsan.example", subject="S", text="https://x/?token=abc", kind="password reset link")
    with pytest.raises(EmailDeliveryFailed):
        sender.send(message)
    assert send_quietly(sender, message) is False
    assert "token=abc" not in caplog.text and "key-123" not in caplog.text
    assert "password reset link" in caplog.text
