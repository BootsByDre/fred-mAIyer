"""Product search against the Kroger catalog."""

from __future__ import annotations

import httpx

from fred_maiyer.models import Product

KROGER_PRODUCTS_URL = "https://api.kroger.com/v1/products"


class ProductSearchError(Exception):
    """Raised when a product search fails."""


async def search_products(
    term: str,
    access_token: str,
    location_id: str,
    limit: int = 10,
) -> list[Product]:
    """Search for products by keyword at a specific store."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            KROGER_PRODUCTS_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "filter.term": term,
                "filter.locationId": location_id,
                "filter.limit": limit,
            },
        )
        if response.status_code != 200:
            raise ProductSearchError(
                f"Product search failed: {response.status_code} {response.text}"
            )
        data = response.json().get("data", [])
        return [_parse_product(item) for item in data]


def _parse_product(item: dict) -> Product:
    """Parse a raw Kroger API product item into a Product model."""
    first_item = item.get("items", [{}])[0]
    price_data = first_item.get("price", {})
    stock_level = first_item.get("inventory", {}).get("stockLevel", "")
    return Product(
        product_id=item.get("productId", ""),
        name=item.get("description", ""),
        description=item.get("description", ""),
        brand=item.get("brand", ""),
        size=first_item.get("size", ""),
        price=price_data.get("regular"),
        in_stock=stock_level != "TEMPORARILY_OUT_OF_STOCK",
    )
