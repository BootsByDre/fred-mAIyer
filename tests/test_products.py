"""Tests for the products module."""

import respx
from httpx import Response

from fred_maiyer.products import ProductSearchError, search_products


@respx.mock
async def test_search_products(access_token: str, location_id: str):
    respx.get("https://api.kroger.com/v1/products").mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "productId": "0001111041700",
                        "description": "Kroger Vitamin D Whole Milk",
                        "brand": "Kroger",
                        "items": [
                            {
                                "size": "1 gal",
                                "price": {"regular": 3.49},
                                "inventory": {"stockLevel": "HIGH"},
                            }
                        ],
                    }
                ]
            },
        )
    )
    products = await search_products("whole milk", access_token, location_id)
    assert len(products) == 1
    assert products[0].product_id == "0001111041700"
    assert products[0].name == "Kroger Vitamin D Whole Milk"
    assert products[0].price == 3.49
    assert products[0].in_stock is True


@respx.mock
async def test_search_products_failure(access_token: str, location_id: str):
    respx.get("https://api.kroger.com/v1/products").mock(
        return_value=Response(500, text="Internal Server Error")
    )
    try:
        await search_products("milk", access_token, location_id)
        assert False, "Expected ProductSearchError"
    except ProductSearchError:
        pass
