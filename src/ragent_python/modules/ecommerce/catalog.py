"""Product catalog domain.

Loads the static fixture under `data/products.json` and provides a
deterministic, network-free filter API. Step D scope: structured filters
(brand / category / price band / min ram) + keyword overlap against the
name + summary. Semantic / embedding-driven search is intentionally out
of scope; that lands when the embedding adapter is wired (Step E or
later).

The catalogue is intentionally module-owned — the file lives under
`modules/ecommerce/data/` — mirroring how `modules/demo_corpus/` owns
its six chunks. No external HTTP, no live ecommerce API.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class Product:
    product_id: str
    name: str
    brand: str
    category: str
    price_usd: float
    summary: str
    image_url: str
    screen: str | None
    chip: str | None
    ram_gb: int | None
    storage_gb: int | None
    battery_wh: int | None
    weight_g: int | None
    release_year: int
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Product":
        known = {
            "product_id",
            "name",
            "brand",
            "category",
            "price_usd",
            "summary",
            "image_url",
            "screen",
            "chip",
            "ram_gb",
            "storage_gb",
            "battery_wh",
            "weight_g",
            "release_year",
        }
        extras = {key: value for key, value in payload.items() if key not in known}
        return cls(
            product_id=str(payload["product_id"]),
            name=str(payload["name"]),
            brand=str(payload["brand"]),
            category=str(payload["category"]),
            price_usd=float(payload["price_usd"]),
            summary=str(payload["summary"]),
            image_url=str(payload["image_url"]),
            screen=payload.get("screen"),
            chip=payload.get("chip"),
            ram_gb=payload.get("ram_gb"),
            storage_gb=payload.get("storage_gb"),
            battery_wh=payload.get("battery_wh"),
            weight_g=payload.get("weight_g"),
            release_year=int(payload["release_year"]),
            extras=extras,
        )


@dataclass(frozen=True, slots=True)
class ProductCatalogFilters:
    brand: str | None = None
    category: str | None = None
    min_price_usd: float | None = None
    max_price_usd: float | None = None
    min_ram_gb: int | None = None
    min_release_year: int | None = None


PRODUCT_CATEGORIES = ("laptop", "phone", "tablet", "earbuds", "monitor")


_DATA_FILE = Path(__file__).resolve().parent / "data" / "products.json"


@lru_cache(maxsize=1)
def _load_raw_payload() -> dict[str, Any]:
    with _DATA_FILE.open("r", encoding="utf-8") as fp:
        return json.load(fp)


@lru_cache(maxsize=1)
def load_products() -> tuple[Product, ...]:
    payload = _load_raw_payload()
    products = payload.get("products", [])
    return tuple(Product.from_dict(item) for item in products)


def _normalize_query_terms(query: str) -> list[str]:
    return [
        term.strip().lower()
        for term in query.split()
        if term.strip() and len(term.strip()) >= 2
    ]


def _keyword_match_score(product: Product, terms: list[str]) -> int:
    if not terms:
        return 1
    haystack = " ".join(
        [
            product.name,
            product.brand,
            product.category,
            product.summary,
            product.chip or "",
            product.screen or "",
        ]
    ).lower()
    return sum(1 for term in terms if term in haystack)


def _passes_filters(product: Product, filters: ProductCatalogFilters) -> bool:
    if filters.brand is not None and product.brand.lower() != filters.brand.lower():
        return False
    if filters.category is not None and product.category.lower() != filters.category.lower():
        return False
    if filters.min_price_usd is not None and product.price_usd < filters.min_price_usd:
        return False
    if filters.max_price_usd is not None and product.price_usd > filters.max_price_usd:
        return False
    if filters.min_ram_gb is not None:
        if product.ram_gb is None or product.ram_gb < filters.min_ram_gb:
            return False
    if filters.min_release_year is not None and product.release_year < filters.min_release_year:
        return False
    return True


def search_products(
    query: str,
    filters: ProductCatalogFilters | None = None,
    limit: int = 6,
) -> list[Product]:
    """Return products matching `filters` and ordered by keyword overlap.

    Empty query returns the catalog ordered by `release_year` desc then
    price asc, capped at `limit`. Any keyword match boosts a product; ties
    are broken by newer release year then lower price.
    """

    effective_filters = filters or ProductCatalogFilters()
    terms = _normalize_query_terms(query)
    candidates = [
        product for product in load_products() if _passes_filters(product, effective_filters)
    ]

    if not terms:
        ordered = sorted(
            candidates, key=lambda p: (-p.release_year, p.price_usd, p.name.lower())
        )
        return ordered[: max(0, limit)]

    scored: list[tuple[int, Product]] = []
    for product in candidates:
        score = _keyword_match_score(product, terms)
        if score <= 0:
            continue
        scored.append((score, product))

    scored.sort(
        key=lambda item: (
            -item[0],
            -item[1].release_year,
            item[1].price_usd,
            item[1].name.lower(),
        )
    )
    return [product for _, product in scored][: max(0, limit)]
