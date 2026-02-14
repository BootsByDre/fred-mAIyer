"""Shared test fixtures."""

import pytest


@pytest.fixture()
def client_id() -> str:
    return "test-client-id"


@pytest.fixture()
def client_secret() -> str:
    return "test-client-secret"


@pytest.fixture()
def access_token() -> str:
    return "test-access-token"


@pytest.fixture()
def location_id() -> str:
    return "70100153"
