"""Central registries for the platform.

Each registry owns one cross-cutting concern that modules contribute to:

- `tool_pack.py`       — MCP tool packs (groups of tools)
- `retrieval_source.py`— named retrieval sources with activation selectors
- `module_registry.py` — the entrypoint that wires modules into the above

Registries are intentionally simple in-memory containers in Step A; persistence
or hot-reload can be added later behind the same interface.
"""

from ragent_python.infra.registries.module_registry import ModuleRegistry, default_module_registry
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
    "ModuleRegistry",
    "RetrievalSourceRegistry",
    "RetrievalSourceSpec",
    "ToolPack",
    "ToolPackRegistry",
    "default_module_registry",
    "default_retrieval_source_registry",
    "default_tool_pack_registry",
]
