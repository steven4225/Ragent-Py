"""Internal preview endpoint for the ecommerce module.

Step D scope: `chat_service` is intentionally untouched, so the
`ProductCardBlock` reaches the frontend through this dedicated route
instead of the chat stream. The endpoint reads
`modules.ecommerce.catalog.search_products` directly and converts each
hit into a `ProductCardBlock`, then returns the list as
`AssistantMessageBlocks`-shaped payload. No LLM, no retrieval fusion,
no auth gate — it is a deterministic preview lane for the TS preview
page and for tests.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ragent_python.modules.ecommerce.blocks import (
    ProductCardBlock,
    product_to_card_block,
)
from ragent_python.modules.ecommerce.catalog import (
    ProductCatalogFilters,
    search_products,
)


router = APIRouter(prefix="/internal/ecommerce", tags=["ecommerce"])


class EcommerceSearchFilters(BaseModel):
    brand: str | None = None
    category: str | None = None
    min_price_usd: float | None = None
    max_price_usd: float | None = None
    min_ram_gb: int | None = None
    min_release_year: int | None = None


class EcommerceSearchRequest(BaseModel):
    query: str = ""
    filters: EcommerceSearchFilters = Field(default_factory=EcommerceSearchFilters)
    limit: int = 6


class EcommerceSearchResponse(BaseModel):
    source: Literal["ecommerce-catalog-preview"] = "ecommerce-catalog-preview"
    query: str
    total: int
    blocks: list[ProductCardBlock]


def _to_domain_filters(filters: EcommerceSearchFilters) -> ProductCatalogFilters:
    return ProductCatalogFilters(
        brand=filters.brand,
        category=filters.category,
        min_price_usd=filters.min_price_usd,
        max_price_usd=filters.max_price_usd,
        min_ram_gb=filters.min_ram_gb,
        min_release_year=filters.min_release_year,
    )


@router.post("/search", response_model=EcommerceSearchResponse)
async def internal_ecommerce_search(
    request: EcommerceSearchRequest,
) -> EcommerceSearchResponse:
    products = search_products(
        request.query,
        filters=_to_domain_filters(request.filters),
        limit=max(0, request.limit),
    )
    blocks = [product_to_card_block(product) for product in products]
    return EcommerceSearchResponse(
        query=request.query,
        total=len(blocks),
        blocks=blocks,
    )
