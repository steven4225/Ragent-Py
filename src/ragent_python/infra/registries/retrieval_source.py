"""Retrieval source registry.

The existing `HybridRetrievalProvider` is a single hybrid pipeline that fuses
Qdrant + BM25 over one shared corpus. Modules that want their own corpus
(e.g. an e-commerce product catalogue with structured payload filters)
register a `RetrievalSourceSpec`; the resolver activates sources whose
selector matches the request.

Step A only ships the registry shape. The wiring inside
`retrieval/providers.py` is migrated in Step C.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
    from ragent_python.retrieval.providers import SearchProvider


@dataclass(frozen=True, slots=True)
class RetrievalSourceSpec:
    name: str
    module: str
    build_provider: Callable[[], "SearchProvider"]
    selector: Callable[["InternalRetrievalRequestModel"], bool]
    fusion_weight: float = 1.0
    description: str = ""


class RetrievalSourceRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, RetrievalSourceSpec] = {}

    def register(self, spec: RetrievalSourceSpec) -> None:
        if spec.name in self._specs:
            raise ValueError(f"Retrieval source '{spec.name}' already registered.")
        self._specs[spec.name] = spec

    def get(self, name: str) -> RetrievalSourceSpec | None:
        return self._specs.get(name)

    def list_specs(self) -> list[RetrievalSourceSpec]:
        return list(self._specs.values())

    def resolve(
        self, request: "InternalRetrievalRequestModel"
    ) -> list[RetrievalSourceSpec]:
        return [spec for spec in self._specs.values() if spec.selector(request)]

    def clear(self) -> None:
        self._specs.clear()


default_retrieval_source_registry = RetrievalSourceRegistry()
