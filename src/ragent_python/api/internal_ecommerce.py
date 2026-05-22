"""Internal preview endpoints for the ecommerce module.

Step D / D.1 scope: `chat_service` is intentionally untouched, so the
`ProductCardBlock` and `SpecCompareBlock` reach the frontend through
these dedicated preview routes instead of the chat stream. The two
endpoints read `modules.ecommerce.catalog` directly and convert hits
into the matching renderer block payloads. No LLM, no retrieval
fusion, no auth gate — deterministic preview lanes for the TS preview
page and for tests.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ragent_python.modules.ecommerce.blocks import (
    SPEC_COMPARE_MAX_PRODUCTS,
    ProductCardBlock,
    SpecCompareBlock,
    build_spec_compare_block,
    product_to_card_block,
)
from ragent_python.modules.ecommerce.catalog import (
    ProductCatalogFilters,
    get_products_by_ids,
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


class EcommerceCompareRequest(BaseModel):
    product_ids: list[str] = Field(default_factory=list)


class EcommerceCompareResponse(BaseModel):
    source: Literal["ecommerce-compare-preview"] = "ecommerce-compare-preview"
    requested_ids: list[str]
    resolved_ids: list[str]
    missing_ids: list[str]
    truncated: bool
    block: SpecCompareBlock


@router.post("/compare", response_model=EcommerceCompareResponse)
async def internal_ecommerce_compare(
    request: EcommerceCompareRequest,
) -> EcommerceCompareResponse:
    requested = list(request.product_ids)
    resolved_products = get_products_by_ids(requested)
    resolved_id_set = {product.product_id for product in resolved_products}
    missing = [pid for pid in requested if pid not in resolved_id_set]
    truncated = len(resolved_products) > SPEC_COMPARE_MAX_PRODUCTS
    block = build_spec_compare_block(resolved_products)
    return EcommerceCompareResponse(
        requested_ids=requested,
        resolved_ids=[column.product_id for column in block.columns],
        missing_ids=missing,
        truncated=truncated,
        block=block,
    )
