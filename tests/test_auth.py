"""Tests for the auth module."""

import respx
from httpx import Response

from fred_maiyer.auth import (
    AuthError,
    build_authorization_url,
    exchange_auth_code,
    get_client_token,
    refresh_access_token,
)


@respx.mock
async def test_get_client_token(client_id: str, client_secret: str):
    respx.post("https://api.kroger.com/v1/connect/oauth2/token").mock(
        return_value=Response(
            200,
            json={
                "access_token": "abc123",
                "token_type": "Bearer",
                "expires_in": 1800,
            },
        )
    )
    token = await get_client_token(client_id, client_secret)
    assert token.access_token == "abc123"
    assert token.token_type == "Bearer"


@respx.mock
async def test_get_client_token_failure(client_id: str, client_secret: str):
    respx.post("https://api.kroger.com/v1/connect/oauth2/token").mock(
        return_value=Response(401, text="Unauthorized")
    )
    try:
        await get_client_token(client_id, client_secret)
        assert False, "Expected AuthError"
    except AuthError:
        pass


@respx.mock
async def test_refresh_access_token(client_id: str, client_secret: str):
    respx.post("https://api.kroger.com/v1/connect/oauth2/token").mock(
        return_value=Response(
            200,
            json={
                "access_token": "refreshed-token",
                "refresh_token": "new-refresh",
                "token_type": "Bearer",
                "expires_in": 1800,
            },
        )
    )
    token = await refresh_access_token(client_id, client_secret, "old-refresh")
    assert token.access_token == "refreshed-token"
    assert token.refresh_token == "new-refresh"


def test_build_authorization_url(client_id: str):
    url = build_authorization_url(client_id)
    assert "api.kroger.com" in url
    assert f"client_id={client_id}" in url
    assert "response_type=code" in url
    assert "cart.basic" in url


def test_build_authorization_url_custom_redirect(client_id: str):
    url = build_authorization_url(client_id, redirect_uri="http://example.com/cb")
    assert "example.com" in url


@respx.mock
async def test_exchange_auth_code(client_id: str, client_secret: str):
    respx.post("https://api.kroger.com/v1/connect/oauth2/token").mock(
        return_value=Response(
            200,
            json={
                "access_token": "user-token",
                "refresh_token": "user-refresh",
                "token_type": "Bearer",
                "expires_in": 1800,
            },
        )
    )
    token = await exchange_auth_code(client_id, client_secret, "test-auth-code")
    assert token.access_token == "user-token"
    assert token.refresh_token == "user-refresh"


@respx.mock
async def test_exchange_auth_code_failure(client_id: str, client_secret: str):
    respx.post("https://api.kroger.com/v1/connect/oauth2/token").mock(
        return_value=Response(400, text="Bad Request")
    )
    try:
        await exchange_auth_code(client_id, client_secret, "bad-code")
        assert False, "Expected AuthError"
    except AuthError:
        pass
