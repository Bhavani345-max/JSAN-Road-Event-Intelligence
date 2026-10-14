"""A source REI may not read cannot be run, even by hand: one whose terms forbid automated
access (decision 0024), or one the user removed from REI (decision 0026)."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.support import sign_in


@pytest.fixture
def registry_client(engine, session):
    """The API with the real source registry: no connector is replaced."""
    settings = Settings(
        _env_file=None, database_url="sqlite://", auto_migrate=False,
        ingestion_scheduler_enabled=False,
    )  # fmt: skip
    with TestClient(create_app(settings, engine=engine)) as client:
        yield sign_in(client)


@pytest.mark.parametrize("source_id", ["siasat", "siasat-mumbai"])
def test_a_restricted_source_cannot_be_run_and_says_why(registry_client, source_id):
    assert source_id not in registry_client.app.state.ingestion_service.connector_factories
    assert registry_client.post("/api/ingestion/run", params={"source_id": source_id}).status_code == 404

    source = registry_client.get(f"/api/sources/{source_id}").json()
    assert source["integration_status"] == "TERMS_REVIEW_REQUIRED"
    assert source["active"] is False
    assert source["terms_status"] == "RESTRICTED"
    assert source["commercial_use"] == "NOT_PERMITTED"


def test_a_removed_source_cannot_be_run_and_says_why(registry_client):
    assert "the-hans-india" not in registry_client.app.state.ingestion_service.connector_factories
    response = registry_client.post("/api/ingestion/run", params={"source_id": "the-hans-india"})
    assert response.status_code == 404

    source = registry_client.get("/api/sources/the-hans-india").json()
    assert source["integration_status"] == "NOT_USABLE"
    assert source["active"] is False
    # Read, not formally reviewed: not marked restricted.
    assert source["terms_status"] == "REVIEW_REQUIRED"
    assert source["terms_reviewed"] is False
    assert source["commercial_use"] == "NOT_PERMITTED"
    assert "Removed from REI" in source["notes"]
