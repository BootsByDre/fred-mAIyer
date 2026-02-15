"""Kroger OAuth2 authentication."""

from __future__ import annotations

import base64
from urllib.parse import urlencode

import httpx

from fred_maiyer.models import TokenResponse

KROGER_AUTH_URL = "https://api.kroger.com/v1/connect/oauth2/authorize"
KROGER_TOKEN_URL = "https://api.kroger.com/v1/connect/oauth2/token"
DEFAULT_REDIRECT_URI = "http://localhost:8888/callback"


class AuthError(Exception):
    """Raised when authentication with the Kroger API fails."""


def build_authorization_url(
    client_id: str,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
    scope: str = "product.compact cart.basic:write",
) -> str:
    """Build the OAuth2 authorization URL for user consent."""
    params = {
        "scope": scope,
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
    }
    return f"{KROGER_AUTH_URL}?{urlencode(params)}"


async def get_client_token(
    client_id: str,
    client_secret: str,
) -> TokenResponse:
    """Obtain a client credentials token (no user context)."""
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            KROGER_TOKEN_URL,
            headers={"Authorization": f"Basic {credentials}"},
            data={
                "grant_type": "client_credentials",
                "scope": "product.compact",
            },
        )
        if response.status_code != 200:
            raise AuthError(
                f"Failed to get client token: {response.status_code} {response.text}"
            )
        return TokenResponse.model_validate(response.json())


async def exchange_auth_code(
    client_id: str,
    client_secret: str,
    auth_code: str,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
) -> TokenResponse:
    """Exchange an authorization code for access and refresh tokens."""
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            KROGER_TOKEN_URL,
            headers={"Authorization": f"Basic {credentials}"},
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": redirect_uri,
            },
        )
        if response.status_code != 200:
            raise AuthError(
                f"Failed to exchange auth code: {response.status_code} {response.text}"
            )
        return TokenResponse.model_validate(response.json())


async def refresh_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> TokenResponse:
    """Refresh an expired access token."""
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            KROGER_TOKEN_URL,
            headers={"Authorization": f"Basic {credentials}"},
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        if response.status_code != 200:
            raise AuthError(
                f"Failed to refresh token: {response.status_code} {response.text}"
            )
        return TokenResponse.model_validate(response.json())
