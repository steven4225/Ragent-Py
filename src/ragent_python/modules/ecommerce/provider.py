"""`ProductCatalogRetrievalProvider` — second `SearchProvider` implementation.

Wraps `catalog.search_products` so the ecommerce module can participate
in the global `RetrievalSourceRegistry` the same way `demo_corpus` does.
Step D itself does not route the chat pipeline through this provider —
the `/internal/ecommerce/search` endpoint goes straight to `catalog`.
Registering the spec makes the source globally discoverable for future
chat-side integration without touching `chat_service` in this push.

Each returned `RetrievalChunkModel` packs the structured product fields
in `metadata` so downstream consumers (e.g. the renderer-block builder
in `api/internal_ecommerce`) never have to re-parse JSON.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.contracts.public_api import RetrievalChunkModel
from ragent_python.modules.ecommerce.catalog import (
    Product,
    ProductCatalogFilters,
    search_products,
)


PRODUCT_KNOWLEDGE_BASE_ID = "kb_ecommerce_products"


def _extract_filters(request: InternalRetrievalRequestModel) -> ProductCatalogFilters:
    raw = request.filters or {}

    def _as_float(value: object) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str) and value.strip():
            try:
                return float(value)
            except ValueError:
                return None
        return None

    def _as_int(value: object) -> int | None:
        as_float = _as_float(value)
        if as_float is None:
            return None
        return int(as_float)

    def _as_str(value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    return ProductCatalogFilters(
        brand=_as_str(raw.get("brand")),
        category=_as_str(raw.get("category")),
        min_price_usd=_as_float(raw.get("min_price_usd")),
        max_price_usd=_as_float(raw.get("max_price_usd")),
        min_ram_gb=_as_int(raw.get("min_ram_gb")),
        min_release_year=_as_int(raw.get("min_release_year")),
    )


def _product_to_chunk(product: Product, score: int) -> RetrievalChunkModel:
    payload = asdict(product)
    extras = payload.pop("extras", {})
    metadata = {
        "provider": "ecommerce-catalog",
        **payload,
        **extras,
    }
    return RetrievalChunkModel(
        chunkId=f"product:{product.product_id}",
        knowledgeBaseId=PRODUCT_KNOWLEDGE_BASE_ID,
        documentId=product.product_id,
        title=product.name,
        content=product.summary,
        score=float(score),
        source=ProductCatalogRetrievalProvider.provider_name,
        metadata=metadata,
    )


class ProductCatalogRetrievalProvider:
    provider_name = "python-ecommerce-catalog"

    def search(
        self,
        request: InternalRetrievalRequestModel,
        query_terms: list[str] | None = None,
    ) -> list[RetrievalChunkModel]:
        filters = _extract_filters(request)
        results = search_products(
            request.query,
            filters=filters,
            limit=request.topK or 6,
        )
        chunks: list[RetrievalChunkModel] = []
        for index, product in enumerate(results):
            score = max(1, len(results) - index)
            chunks.append(_product_to_chunk(product, score))
        return chunks


def iter_product_catalog() -> Iterable[Product]:
    """Pass-through iterator for tests / debug; defined here so callers
    do not have to reach into `catalog`'s private cache."""

    from ragent_python.modules.ecommerce.catalog import load_products

    return load_products()
