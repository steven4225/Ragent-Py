"""Module-internal chat orchestration for the ecommerce preview lane.

The flow is the simplest end-to-end shape the platform supports:

  1. Run the local catalog filter (`search_products`) against the user
     query — same code path the `/internal/ecommerce/search` preview
     route uses, so retrieval is deterministic and offline.
  2. Render each hit into a `ProductCardBlock` so the preview UI shares
     a renderer with the search lane.
  3. Build a `GenerationRequest` whose system prompt embeds the
     retrieved SKUs as compact context, then call the resolved
     `GenerationAdapter`. With no key configured, the resolver returns
     the `MockGenerationAdapter`, keeping the path deterministic for
     tests and dev.
  4. Return retrieval, blocks, and the model's answer together so the
     caller can render all three in one preview turn.

This is preview-only: `services/chat_service.py` is untouched and the
main `/api/chat` stream is not involved. The orchestration deliberately
does not call `stream()`; the preview endpoint returns a single JSON
payload per turn.
"""

from __future__ import annotations

from dataclasses import dataclass

from ragent_python.config import get_settings
from ragent_python.core.generation.adapter import (
    GenerationAdapter,
    GenerationMessage,
    GenerationRequest,
    GenerationResult,
)
from ragent_python.modules.ecommerce.blocks import (
    ProductCardBlock,
    product_to_card_block,
)
from ragent_python.modules.ecommerce.catalog import (
    Product,
    ProductCatalogFilters,
    search_products,
)


SYSTEM_PROMPT = (
    "You are a concise product advisor for a small consumer-electronics "
    "catalog. You will be given a user query and a short list of candidate "
    "products retrieved from a static catalog. Recommend at most three of "
    "the listed products, explain trade-offs in two or three short "
    "sentences each, and always reference products by their exact name. "
    "Do not invent products that are not in the candidate list. If nothing "
    "in the list matches, say so plainly and suggest what filter the user "
    "might relax."
)


@dataclass(frozen=True, slots=True)
class EcommerceChatTurn:
    query: str
    retrieved_products: list[Product]
    blocks: list[ProductCardBlock]
    answer: GenerationResult


def _format_product_line(product: Product) -> str:
    bits: list[str] = [
        f"id={product.product_id}",
        f"name={product.name}",
        f"brand={product.brand}",
        f"category={product.category}",
        f"price=${product.price_usd:.0f}",
    ]
    if product.chip:
        bits.append(f"chip={product.chip}")
    if product.ram_gb is not None:
        bits.append(f"ram={product.ram_gb}GB")
    if product.storage_gb is not None:
        bits.append(f"storage={product.storage_gb}GB")
    if product.screen:
        bits.append(f"display={product.screen}")
    bits.append(f"year={product.release_year}")
    return "- " + ", ".join(bits)


def build_chat_request(
    query: str,
    products: list[Product],
    *,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> GenerationRequest:
    settings = get_settings()
    catalog_lines = (
        "\n".join(_format_product_line(product) for product in products)
        if products
        else "(no candidate products matched the catalog filter)"
    )
    system_content = (
        f"{SYSTEM_PROMPT}\n\nCandidate products:\n{catalog_lines}"
    )
    return GenerationRequest(
        messages=[
            GenerationMessage(role="system", content=system_content),
            GenerationMessage(role="user", content=query),
        ],
        temperature=settings.llm_temperature if temperature is None else temperature,
        max_input_tokens=settings.llm_max_input_tokens,
        max_output_tokens=(
            settings.llm_max_output_tokens
            if max_output_tokens is None
            else max_output_tokens
        ),
    )


async def run_ecommerce_chat_turn(
    query: str,
    *,
    adapter: GenerationAdapter,
    filters: ProductCatalogFilters | None = None,
    retrieval_limit: int = 5,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> EcommerceChatTurn:
    products = search_products(
        query,
        filters=filters or ProductCatalogFilters(),
        limit=max(0, retrieval_limit),
    )
    blocks = [product_to_card_block(product) for product in products]
    generation_request = build_chat_request(
        query,
        products,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )
    result = await adapter.generate(generation_request)
    return EcommerceChatTurn(
        query=query,
        retrieved_products=products,
        blocks=blocks,
        answer=result,
    )
