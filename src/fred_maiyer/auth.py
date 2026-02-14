"""Kroger OAuth2 authentication."""

from __future__ import annotations

import base64

import httpx

from fred_maiyer.models import TokenResponse

KROGER_TOKEN_URL = "https://api.kroger.com/v1/connect/oauth2/token"


class AuthError(Exception):
    """Raised when authentication with the Kroger API fails."""


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
