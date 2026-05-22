"""Renderer block schemas owned by the ecommerce module.

The frontend dispatches on the literal `type` field; this module owns
`product_card` (single SKU) and `spec_compare` (aligned spec table
across several SKUs). Each block flattens the product domain into a
ready-to-render shape so the TS side never has to re-parse the
catalogue.
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


SPEC_COMPARE_MAX_PRODUCTS = 4
SPEC_COMPARE_PLACEHOLDER = "\u2014"  # em dash for "no value"


def _format_price(price_usd: float) -> str:
    if price_usd >= 100:
        return f"${price_usd:,.0f}"
    return f"${price_usd:,.2f}"


def _format_release_year(year: int) -> str:
    return str(year)


_SPEC_ROW_LABELS: tuple[str, ...] = (
    "Price",
    "Display",
    "Chip",
    "Memory",
    "Storage",
    "Battery",
    "Weight",
    "Released",
)


def _extract_spec_value(label: str, product: Product) -> str | None:
    if label == "Price":
        return _format_price(product.price_usd)
    if label == "Display":
        return product.screen
    if label == "Chip":
        return product.chip
    if label == "Memory":
        return _format_ram(product.ram_gb)
    if label == "Storage":
        return _format_storage(product.storage_gb)
    if label == "Battery":
        return _format_battery(product.battery_wh)
    if label == "Weight":
        return _format_weight(product.weight_g)
    if label == "Released":
        return _format_release_year(product.release_year)
    return None


class SpecCompareColumn(BaseModel):
    product_id: str
    name: str
    brand: str
    category: str
    image_url: str


class SpecCompareRow(BaseModel):
    label: str
    values: list[str] = Field(default_factory=list)
    has_data: bool


class SpecCompareBlock(BaseModel):
    type: Literal["spec_compare"] = "spec_compare"
    columns: list[SpecCompareColumn] = Field(default_factory=list)
    rows: list[SpecCompareRow] = Field(default_factory=list)
    placeholder: str = SPEC_COMPARE_PLACEHOLDER


def build_spec_compare_block(products: list[Product]) -> SpecCompareBlock:
    """Assemble a `SpecCompareBlock` from a small list of `Product`.

    Truncates to `SPEC_COMPARE_MAX_PRODUCTS` to keep the preview table
    width sane. Rows where every product lacks the value are dropped
    entirely; rows where at least one product has a value emit
    `SPEC_COMPARE_PLACEHOLDER` for the missing cells so the table stays
    rectangular.
    """

    capped = products[:SPEC_COMPARE_MAX_PRODUCTS]
    columns = [
        SpecCompareColumn(
            product_id=product.product_id,
            name=product.name,
            brand=product.brand,
            category=product.category,
            image_url=product.image_url,
        )
        for product in capped
    ]

    rows: list[SpecCompareRow] = []
    for label in _SPEC_ROW_LABELS:
        raw_values = [_extract_spec_value(label, product) for product in capped]
        if not any(value is not None for value in raw_values):
            continue
        rows.append(
            SpecCompareRow(
                label=label,
                values=[
                    value if value is not None else SPEC_COMPARE_PLACEHOLDER
                    for value in raw_values
                ],
                has_data=True,
            )
        )

    return SpecCompareBlock(columns=columns, rows=rows)
