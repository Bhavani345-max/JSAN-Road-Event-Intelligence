"""Reviewer sign-in (14 October 2026, migration 0007).

Every route except health and sign-in needs a session. A session is an
opaque cookie; only its digest is stored, and signing out revokes it.
"""

import hashlib
import threading
from collections import defaultdict

import pytest
from fastapi.testclient import TestClient

from app.api.routes import auth
from app.models import AuthSession
from app.services.auth_service import seed_admin_user

EMAIL = "Reviewer@Example.com"
PASSWORD = "correct horse battery staple"


@pytest.fixture
def anonymous(app, session, monkeypatch):
    """A client that has not signed in, with one reviewer account on record."""
    monkeypatch.setattr(auth, "_LOGIN_ATTEMPTS", defaultdict(auth.deque))
    seed_admin_user(session, EMAIL, PASSWORD)
    session.commit()
    with TestClient(app) as client:
        yield client


def sign_in(client, password=PASSWORD):
    return client.post("/api/auth/login", json={"email": EMAIL, "password": password})


def test_only_health_and_sign_in_are_open_without_a_session(anonymous):
    assert anonymous.get("/api/health").status_code == 200
    for path in ("/api/events", "/api/sources", "/api/cities", "/api/merge-candidates", "/api/auth/me"):
        assert anonymous.get(path).status_code == 401, path
    assert anonymous.post("/api/ingestion/run").status_code == 401


def test_a_wrong_password_or_unknown_email_is_refused_alike(anonymous):
    wrong = sign_in(anonymous, password="not the password at all")
    unknown = anonymous.post("/api/auth/login", json={"email": "nobody@example.com", "password": PASSWORD})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert "rei_session" not in anonymous.cookies


def test_signing_in_opens_the_api_and_signing_out_closes_it(anonymous, session):
    response = sign_in(anonymous)
    assert response.status_code == 200
    assert response.json()["email"] == EMAIL.lower()
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "path=/api" in cookie
    # Only a digest of the token is stored.
    token = anonymous.cookies["rei_session"]
    stored = {row.token_hash for row in session.query(AuthSession)}
    assert token not in stored and hashlib.sha256(token.encode("ascii")).hexdigest() in stored

    assert anonymous.get("/api/auth/me").json()["email"] == EMAIL.lower()
    assert anonymous.get("/api/events").status_code == 200

    assert anonymous.post("/api/auth/logout").json() == {"ok": True}
    anonymous.cookies.set("rei_session", token)  # replaying the old cookie
    assert anonymous.get("/api/auth/me").status_code == 401
    assert anonymous.get("/api/events").status_code == 401


def test_signing_in_and_out_do_not_wait_for_a_source_run_on_postgresql(anonymous, app, session, monkeypatch):
    """A run holds the run lock throughout, minutes for a first run of a large feed."""
    assert auth._one_writer_at_a_time(session)  # the tests' SQLite still waits
    monkeypatch.setattr(auth, "_one_writer_at_a_time", lambda session: False)
    statuses = []

    def sign_in_and_out():
        statuses.append(sign_in(anonymous).status_code)
        statuses.append(anonymous.post("/api/auth/logout").status_code)

    with app.state.ingestion_service.lock:  # a source run in progress
        worker = threading.Thread(target=sign_in_and_out)
        worker.start()
        worker.join(timeout=10)
        assert not worker.is_alive(), "signing in waited for the run"
    assert statuses == [200, 200]


def test_changes_from_another_website_are_refused(anonymous):
    assert sign_in(anonymous).status_code == 200
    foreign = anonymous.post("/api/ingestion/run", headers={"Origin": "https://elsewhere.example"})
    assert foreign.status_code == 403
    own = anonymous.post("/api/ingestion/run", headers={"Origin": "http://localhost:3000"})
    assert own.status_code == 200


def test_repeated_failed_sign_ins_are_slowed_down(anonymous, monkeypatch):
    monkeypatch.setattr(auth, "_ATTEMPT_LIMIT", 2)
    assert sign_in(anonymous, password="wrong password one").status_code == 401
    assert sign_in(anonymous, password="wrong password two").status_code == 401
    assert sign_in(anonymous).status_code == 429
