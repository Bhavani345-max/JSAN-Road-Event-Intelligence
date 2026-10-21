"""Shared by every test folder."""

import pytest


@pytest.fixture(autouse=True)
def no_retry_pause(monkeypatch):
    """The official feeds wait a few seconds before asking again (a dropped
    connection, a server error, TfL's odd answer); tests do not wait."""
    import connectors.official.common as common

    monkeypatch.setattr(common, "_sleep", lambda seconds: None)
