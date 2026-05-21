"""Ingestion infra: schema adapter contract + adapter registry.

The existing text-only worker pipeline lives in `worker/ingestion_worker.py`
and stays the default fallback path. Modules that need to ingest structured
records (e.g. product feeds) plug in via `IngestionSchemaAdapter`.
"""

from ragent_python.infra.ingestion.schema_adapter import (
    IngestionSchemaAdapter,
    IngestionSchemaAdapterRegistry,
    StructuredRecord,
    default_ingestion_schema_adapter_registry,
)

__all__ = [
    "IngestionSchemaAdapter",
    "IngestionSchemaAdapterRegistry",
    "StructuredRecord",
    "default_ingestion_schema_adapter_registry",
]
