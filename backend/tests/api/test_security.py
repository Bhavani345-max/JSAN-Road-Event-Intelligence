"""Security fixes of 15 October 2026 (production audit, docs/audit/production-audit-2026-10-15.md).

- The API's documentation is for signed-in users only.
- Sign-in limits count failures per account and per visitor's address, not
  per connection: behind the console's proxy every visitor shares one.
- Roles: a viewer reads, a reviewer also records decisions, an admin also
  runs sources.
"""

import uuid
from collections import defaultdict

import pytest
from fastapi.testclient import TestClient

from app.api.routes import auth
from app.models import User
from app.services.auth_service import hash_password
from packages.common.time import utc_now

PASSWORD = "correct horse battery staple"
ORIGIN = {"Origin": "http://localhost:3000"}


def add_user(session, email, role):
    now = utc_now()
    session.add(
        User(
            user_id=str(uuid.uuid4()), email=email, display_name=email.split("@")[0],
            password_hash=hash_password(PASSWORD), role=role, is_active=True,
            created_at=now, updated_at=now,
        )
    )  # fmt: skip
    session.commit()


@pytest.fixture
def client(app, session, monkeypatch):
    """Not signed in; one admin, one reviewer and one viewer on record."""
    monkeypatch.setattr(auth, "_LOGIN_ATTEMPTS", defaultdict(auth.deque))
    for email, role in (("admin@example.com", "admin"), ("reviewer@example.com", "reviewer"),
                        ("viewer@example.com", "viewer")):  # fmt: skip
        add_user(session, email, role)
    with TestClient(app) as client:
        yield client


def sign_in(client, email, password=PASSWORD, forwarded=None):
    headers = {"X-Forwarded-For": forwarded} if forwarded else {}
    return client.post("/api/auth/login", json={"email": email, "password": password}, headers=headers)


# --- documentation --------------------------------------------------------------------


def test_the_api_documentation_is_not_public(client):
    assert client.get("/api/docs").status_code == 401
    assert client.get("/api/openapi.json").status_code == 401
    # FastAPI's other default addresses are not served at all.
    assert client.get("/redoc").status_code == 404
    assert client.get("/docs").status_code == 404


def test_a_signed_in_user_can_read_the_documentation(client):
    assert sign_in(client, "viewer@example.com").status_code == 200
    assert "swagger" in client.get("/api/docs").text.lower()
    schema = client.get("/api/openapi.json").json()
    assert "/api/events" in schema["paths"]
    # The documentation routes do not list themselves.
    assert "/api/docs" not in schema["paths"]


# --- sign-in limits -------------------------------------------------------------------


def test_one_accounts_failures_do_not_lock_out_another(client, monkeypatch):
    monkeypatch.setattr(auth, "_ATTEMPT_LIMIT", 2)
    for _ in range(2):
        assert sign_in(client, "viewer@example.com", "wrong password").status_code == 401
    assert sign_in(client, "viewer@example.com").status_code == 429
    # Same connection (the console's proxy), another account: still allowed.
    assert sign_in(client, "reviewer@example.com").status_code == 200


def test_one_address_cannot_try_many_accounts(client, monkeypatch):
    monkeypatch.setattr(auth, "_ADDRESS_ATTEMPT_LIMIT", 3)
    for n in range(3):
        assert sign_in(client, f"guess{n}@example.com", "wrong", forwarded="203.0.113.7").status_code == 401
    assert sign_in(client, "admin@example.com", forwarded="203.0.113.7").status_code == 429
    # Another visitor is not affected.
    assert sign_in(client, "admin@example.com", forwarded="198.51.100.4").status_code == 200


def test_the_address_is_the_last_one_the_proxy_added(client, monkeypatch):
    """Entries a visitor writes before the edge's own are ignored."""
    monkeypatch.setattr(auth, "_ADDRESS_ATTEMPT_LIMIT", 2)
    for spoofed in ("10.0.0.1", "10.0.0.2"):
        response = sign_in(client, f"x-{spoofed}@example.com", "wrong", forwarded=f"{spoofed}, 203.0.113.9")
        assert response.status_code == 401
    assert sign_in(client, "admin@example.com", forwarded="10.0.0.3, 203.0.113.9").status_code == 429


def test_a_successful_sign_in_clears_the_accounts_failures(client, monkeypatch):
    monkeypatch.setattr(auth, "_ATTEMPT_LIMIT", 2)
    assert sign_in(client, "viewer@example.com", "wrong password").status_code == 401
    assert sign_in(client, "viewer@example.com").status_code == 200
    assert sign_in(client, "viewer@example.com", "wrong password").status_code == 401
    assert sign_in(client, "viewer@example.com").status_code == 200


# --- roles ----------------------------------------------------------------------------


def test_a_viewer_reads_but_cannot_change_anything(client):
    assert sign_in(client, "viewer@example.com").status_code == 200
    assert client.get("/api/events").status_code == 200
    refused = client.post(
        "/api/events/EVT-NOSUCHEVENT/status", json={"status": "REJECTED", "reason": "test"}, headers=ORIGIN
    )
    assert refused.status_code == 403
    assert client.post("/api/ingestion/run", headers=ORIGIN).status_code == 403


def test_a_reviewer_records_decisions_but_cannot_run_sources(client):
    assert sign_in(client, "reviewer@example.com").status_code == 200
    decision = client.post(
        "/api/events/EVT-NOSUCHEVENT/status", json={"status": "REJECTED", "reason": "test"}, headers=ORIGIN
    )
    assert decision.status_code == 404  # allowed through; the event does not exist
    assert client.post("/api/ingestion/run", headers=ORIGIN).status_code == 403


def test_an_admin_can_run_sources(client):
    assert sign_in(client, "admin@example.com").status_code == 200
    assert client.post("/api/ingestion/run", headers=ORIGIN).status_code == 200


def test_signing_out_is_open_to_every_role(client):
    assert sign_in(client, "viewer@example.com").status_code == 200
    assert client.post("/api/auth/logout", headers=ORIGIN).json() == {"ok": True}


def test_made_up_emails_do_not_pile_up_in_memory(client, monkeypatch):
    """Failures age out, and checking a limit records nothing."""
    attempts = auth._LOGIN_ATTEMPTS
    assert sign_in(client, "admin@example.com").status_code == 200
    assert not attempts  # a successful sign-in leaves nothing behind
    monkeypatch.setattr(auth, "_ATTEMPT_WINDOW_SECONDS", 0)
    monkeypatch.setattr(auth, "_MAX_TRACKED_KEYS", 3)
    for n in range(10):
        assert sign_in(client, f"made-up-{n}@example.com", "wrong").status_code == 401
    # With a zero window every failure has aged out: the sweep keeps the table small.
    assert len(attempts) <= 3 + 2
