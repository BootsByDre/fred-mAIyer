"""Tests for the store module."""

import respx
from httpx import Response

from fred_maiyer.store import StoreError, find_stores


@respx.mock
async def test_find_stores(access_token: str):
    respx.get("https://api.kroger.com/v1/locations").mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "locationId": "70100153",
                        "name": "Fred Meyer - Hawthorne",
                        "address": {
                            "addressLine1": "3805 SE Hawthorne Blvd",
                            "city": "Portland",
                            "state": "OR",
                            "zipCode": "97214",
                        },
                    }
                ]
            },
        )
    )
    stores = await find_stores("97214", access_token)
    assert len(stores) == 1
    assert stores[0].location_id == "70100153"
    assert stores[0].name == "Fred Meyer - Hawthorne"
    assert "Portland" in stores[0].address


@respx.mock
async def test_find_stores_failure(access_token: str):
    respx.get("https://api.kroger.com/v1/locations").mock(
        return_value=Response(500, text="Internal Server Error")
    )
    try:
        await find_stores("97214", access_token)
        assert False, "Expected StoreError"
    except StoreError:
        pass
