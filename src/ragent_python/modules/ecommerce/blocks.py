"""Renderer block schemas owned by the ecommerce module.

The frontend dispatches on the literal `type` field; `product_card` is
this module's exclusive value. The block intentionally collapses a
product into a flat, render-ready shape — the TS side does not need to
re-parse the product domain model.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ragent_python.modules.ecommerce.catalog import Product


class ProductSpecItem(BaseModel):
    label: str
    value: str


class ProductCardBlock(BaseModel):
    type: Literal["product_card"] = "product_card"
    product_id: str
    name: str
    brand: str
    category: str
    price_usd: float
    summary: str
    image_url: str
    release_year: int
    specs: list[ProductSpecItem] = Field(default_factory=list)


def _format_storage(storage_gb: int | None) -> str | None:
    if storage_gb is None:
        return None
    if storage_gb >= 1024:
        whole = storage_gb // 1024
        if storage_gb % 1024 == 0:
            return f"{whole} TB"
        return f"{storage_gb / 1024:.1f} TB"
    return f"{storage_gb} GB"


def _format_ram(ram_gb: int | None) -> str | None:
    if ram_gb is None:
        return None
    return f"{ram_gb} GB"


def _format_battery(battery_wh: int | None) -> str | None:
    if battery_wh is None or battery_wh <= 0:
        return None
    return f"{battery_wh} Wh"


def _format_weight(weight_g: int | None) -> str | None:
    if weight_g is None:
        return None
    if weight_g >= 1000:
        return f"{weight_g / 1000:.2f} kg"
    return f"{weight_g} g"


def product_to_card_block(product: Product) -> ProductCardBlock:
    spec_candidates: list[ProductSpecItem] = []
    if product.screen:
        spec_candidates.append(ProductSpecItem(label="Display", value=product.screen))
    if product.chip:
        spec_candidates.append(ProductSpecItem(label="Chip", value=product.chip))
    ram_value = _format_ram(product.ram_gb)
    if ram_value:
        spec_candidates.append(ProductSpecItem(label="Memory", value=ram_value))
    storage_value = _format_storage(product.storage_gb)
    if storage_value:
        spec_candidates.append(ProductSpecItem(label="Storage", value=storage_value))
    battery_value = _format_battery(product.battery_wh)
    if battery_value:
        spec_candidates.append(ProductSpecItem(label="Battery", value=battery_value))
    weight_value = _format_weight(product.weight_g)
    if weight_value:
        spec_candidates.append(ProductSpecItem(label="Weight", value=weight_value))

    return ProductCardBlock(
        product_id=product.product_id,
        name=product.name,
        brand=product.brand,
        category=product.category,
        price_usd=product.price_usd,
        summary=product.summary,
        image_url=product.image_url,
        release_year=product.release_year,
        specs=spec_candidates,
    )
