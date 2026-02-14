"""Pydantic models for Kroger API responses and requests."""

from pydantic import BaseModel


class Product(BaseModel):
    """A product from the Kroger catalog."""

    product_id: str
    name: str
    description: str = ""
    brand: str = ""
    size: str = ""
    price: float | None = None
    in_stock: bool = True


class CartItem(BaseModel):
    """An item to add to the cart."""

    product_id: str
    quantity: int = 1


class Store(BaseModel):
    """A Kroger/Fred Meyer store location."""

    location_id: str
    name: str
    address: str = ""
    zip_code: str = ""


class TokenResponse(BaseModel):
    """OAuth2 token response from the Kroger API."""

    access_token: str
    refresh_token: str = ""
    token_type: str = "Bearer"
    expires_in: int = 1800
