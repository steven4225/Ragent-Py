"""Ecommerce module.

The first business module on the platform: owns a static 3C product
fixture (~18 SKUs), the `ProductCatalogRetrievalProvider` that searches
it, the `ProductCardBlock` renderer block, and the
`RetrievalSourceSpec` that publishes the source to
`RetrievalSourceRegistry`.

The frontend-facing path is `/internal/ecommerce/search`, exposed by
`api/internal_ecommerce`. That endpoint reads `catalog.search_products`
directly to emit deterministic `ProductCardBlock` payloads; the chat
pipeline is intentionally **not** changed in Step D.
"""

from ragent_python.modules.ecommerce.blocks import (
    ProductCardBlock,
    ProductSpecItem,
    product_to_card_block,
)
from ragent_python.modules.ecommerce.catalog import (
    PRODUCT_CATEGORIES,
    Product,
    ProductCatalogFilters,
    load_products,
    search_products,
)
from ragent_python.modules.ecommerce.module import (
    ECOMMERCE_SOURCE_NAME,
    EcommerceModule,
    build_ecommerce_catalog_retrieval_source_spec,
)
from ragent_python.modules.ecommerce.provider import (
    PRODUCT_KNOWLEDGE_BASE_ID,
    ProductCatalogRetrievalProvider,
)

__all__ = [
    "ECOMMERCE_SOURCE_NAME",
    "EcommerceModule",
    "PRODUCT_CATEGORIES",
    "PRODUCT_KNOWLEDGE_BASE_ID",
    "Product",
    "ProductCardBlock",
    "ProductCatalogFilters",
    "ProductCatalogRetrievalProvider",
    "ProductSpecItem",
    "build_ecommerce_catalog_retrieval_source_spec",
    "load_products",
    "product_to_card_block",
    "search_products",
]
