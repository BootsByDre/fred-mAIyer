"""Tests for the cart module."""

import respx
from httpx import Response

from fred_maiyer.cart import CartError, add_to_cart
from fred_maiyer.models import CartItem


@respx.mock
async def test_add_to_cart(access_token: str):
    respx.put("https://api.kroger.com/v1/cart/add").mock(return_value=Response(204))
    items = [CartItem(product_id="0001111041700", quantity=1)]
    await add_to_cart(items, access_token)


@respx.mock
async def test_add_to_cart_failure(access_token: str):
    respx.put("https://api.kroger.com/v1/cart/add").mock(
        return_value=Response(401, text="Unauthorized")
    )
    try:
        await add_to_cart([CartItem(product_id="123", quantity=1)], access_token)
        assert False, "Expected CartError"
    except CartError:
        pass
