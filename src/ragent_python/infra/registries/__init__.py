"""Central registries for the platform.

Each registry owns one cross-cutting concern that modules contribute to:

- `tool_pack.py`       — MCP tool packs (groups of tools)
- `retrieval_source.py`— named retrieval sources with activation selectors
- `intent_pattern.py`  — module activation vocabulary used by the router
- `renderer_block.py`  — typed UI blocks emitted in assistant messages
- `module_registry.py` — the entrypoint that wires modules into the above
                         (plus `IngestionSchemaAdapterRegistry` from
                         `infra/ingestion` and `EvalSuiteRegistry` from
                         `infra/eval`)

Registries are intentionally simple in-memory containers in Step A;
persistence or hot-reload can be added later behind the same interface.
"""

from ragent_python.infra.registries.intent_pattern import (
    IntentPatternRegistry,
    default_intent_pattern_registry,
)
from ragent_python.infra.registries.module_registry import ModuleRegistry, default_module_registry
from ragent_python.infra.registries.renderer_block import (
    RendererBlockRegistry,
    default_renderer_block_registry,
)
from ragent_python.infra.registries.retrieval_source import (
    RetrievalSourceRegistry,
    RetrievalSourceSpec,
    default_retrieval_source_registry,
)
from ragent_python.infra.registries.tool_pack import (
    ToolPack,
    ToolPackRegistry,
    default_tool_pack_registry,
)

__all__ = [
    "IntentPatternRegistry",
    "ModuleRegistry",
    "RendererBlockRegistry",
    "RetrievalSourceRegistry",
    "RetrievalSourceSpec",
    "ToolPack",
    "ToolPackRegistry",
    "default_intent_pattern_registry",
    "default_module_registry",
    "default_renderer_block_registry",
    "default_retrieval_source_registry",
    "default_tool_pack_registry",
]
