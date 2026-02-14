"""Cart operations for the Kroger API."""

from __future__ import annotations

import httpx

from fred_maiyer.models import CartItem

KROGER_CART_URL = "https://api.kroger.com/v1/cart/add"


class CartError(Exception):
    """Raised when a cart operation fails."""


async def add_to_cart(
    items: list[CartItem],
    access_token: str,
) -> None:
    """Add one or more items to the authenticated user's cart."""
    payload = {
        "items": [{"upc": item.product_id, "quantity": item.quantity} for item in items]
    }
    async with httpx.AsyncClient() as client:
        response = await client.put(
            KROGER_CART_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            json=payload,
        )
        if response.status_code not in (200, 204):
            raise CartError(
                f"Failed to add items to cart: {response.status_code} {response.text}"
            )
