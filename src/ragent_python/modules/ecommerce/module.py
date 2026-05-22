"""`EcommerceModule` — first business module.

Contributes:

- a `RetrievalSourceSpec` named ``"ecommerce_catalog"`` backed by
  `ProductCatalogRetrievalProvider`. The selector activates the source
  when the request has no knowledge-base filter or when it explicitly
  targets the ecommerce KB id.
- the `ProductCardBlock` renderer block (the first non-universal block).

The module deliberately does **not** patch `chat_service` in Step D;
the renderer block reaches the frontend via the dedicated
`/internal/ecommerce/search` endpoint described in
`api/internal_ecommerce`.
"""

from __future__ import annotations

from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.core.modules.contract import ModuleHookResult
from ragent_python.infra.registries.retrieval_source import RetrievalSourceSpec
from ragent_python.modules.ecommerce.blocks import ProductCardBlock
from ragent_python.modules.ecommerce.provider import (
    PRODUCT_KNOWLEDGE_BASE_ID,
    ProductCatalogRetrievalProvider,
)


ECOMMERCE_SOURCE_NAME = "ecommerce_catalog"


def _ecommerce_catalog_selector(request: InternalRetrievalRequestModel) -> bool:
    if not request.knowledgeBaseIds:
        return True
    return PRODUCT_KNOWLEDGE_BASE_ID in request.knowledgeBaseIds


def build_ecommerce_catalog_retrieval_source_spec() -> RetrievalSourceSpec:
    return RetrievalSourceSpec(
        name=ECOMMERCE_SOURCE_NAME,
        module="ecommerce",
        build_provider=ProductCatalogRetrievalProvider,
        selector=_ecommerce_catalog_selector,
        fusion_weight=1.0,
        description=(
            "Static 3C-product fixture (~18 SKUs across laptop / phone / "
            "tablet / earbuds / monitor) owned by modules/ecommerce. "
            "Step D registers the source for global discoverability; the "
            "preview endpoint /internal/ecommerce/search reads the same "
            "catalogue directly to emit ProductCardBlock payloads."
        ),
    )


class EcommerceModule:
    name = "ecommerce"
    version = "0.1.0"

    def register(self) -> ModuleHookResult:
        return ModuleHookResult(
            retrieval_sources=(build_ecommerce_catalog_retrieval_source_spec(),),
            renderer_blocks=(ProductCardBlock,),
        )
