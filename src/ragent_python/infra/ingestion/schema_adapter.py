"""Ingestion schema adapter.

A module that ingests structured input (product feeds, FAQ tables, ticket
exports, ...) implements `IngestionSchemaAdapter`. The worker pipeline
consults the registry: the first adapter whose `accepts()` matches the source
takes the record path; otherwise the generic text pipeline runs.

The adapter pipeline is:

    raw bytes ─parse()──> StructuredRecord[]
                        └─to_chunks()──> Chunk[]
                                       └─build_payload()──> dict (vector store payload)

`StructuredRecord` is intentionally an opaque pydantic model. Modules declare
their own concrete record types (e.g. `ProductRecord`) and the adapter is
parameterised over them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from pydantic import BaseModel

if TYPE_CHECKING:
    from ragent_python.contracts.ingestion import IngestionSourceModel


class StructuredRecord(BaseModel):
    """Base class for module-specific structured records.

    Subclass this in module code and add domain fields (e.g. ProductRecord
    with sku/brand/price/specs). Adapters are typed against the subclass.
    """

    model_config = {"extra": "allow"}


class IngestionChunk(BaseModel):
    chunk_id: str
    title: str
    content: str
    payload: dict[str, Any] = {}


@runtime_checkable
class IngestionSchemaAdapter(Protocol):
    name: str
    module: str

    def accepts(self, source: "IngestionSourceModel") -> bool: ...

    def parse(self, raw: bytes, source: "IngestionSourceModel") -> list[StructuredRecord]: ...

    def to_chunks(self, records: list[StructuredRecord]) -> list[IngestionChunk]: ...


class IngestionSchemaAdapterRegistry:
    def __init__(self) -> None:
        self._adapters: list[IngestionSchemaAdapter] = []

    def register(self, adapter: IngestionSchemaAdapter) -> None:
        for existing in self._adapters:
            if existing.name == adapter.name:
                raise ValueError(
                    f"Ingestion schema adapter '{adapter.name}' already registered."
                )
        self._adapters.append(adapter)

    def list_adapters(self) -> list[IngestionSchemaAdapter]:
        return list(self._adapters)

    def resolve(self, source: "IngestionSourceModel") -> IngestionSchemaAdapter | None:
        for adapter in self._adapters:
            if adapter.accepts(source):
                return adapter
        return None

    def clear(self) -> None:
        self._adapters.clear()


default_ingestion_schema_adapter_registry = IngestionSchemaAdapterRegistry()
