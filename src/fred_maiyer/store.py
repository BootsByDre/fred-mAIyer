"""Store location resolution for Fred Meyer / Kroger."""

from __future__ import annotations

import httpx

from fred_maiyer.models import Store

KROGER_LOCATIONS_URL = "https://api.kroger.com/v1/locations"


class StoreError(Exception):
    """Raised when store lookup fails."""


async def find_stores(
    zip_code: str,
    access_token: str,
    chain: str = "FRED MEYER",
    limit: int = 5,
) -> list[Store]:
    """Find Fred Meyer stores near a ZIP code."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            KROGER_LOCATIONS_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "filter.zipCode.near": zip_code,
                "filter.chain": chain,
                "filter.limit": limit,
            },
        )
        if response.status_code != 200:
            raise StoreError(
                f"Store lookup failed: {response.status_code} {response.text}"
            )
        data = response.json().get("data", [])
        return [_parse_store(item) for item in data]


def _parse_store(item: dict) -> Store:
    """Parse a raw Kroger API location into a Store model."""
    address = item.get("address", {})
    line1 = address.get("addressLine1", "")
    city = address.get("city", "")
    state = address.get("state", "")
    return Store(
        location_id=item.get("locationId", ""),
        name=item.get("name", ""),
        address=f"{line1}, {city}, {state}",
        zip_code=address.get("zipCode", ""),
    )
