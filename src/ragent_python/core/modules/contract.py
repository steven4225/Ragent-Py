"""Module contract.

A module is the unit of business capability that plugs into the platform. It
exposes a stable set of hooks; the platform calls them at well-defined times.

Step A only fixes the shape of those hooks. No registry wiring, no discovery,
no auto-import. A module instance is registered explicitly via the
ModuleRegistry in `infra/registries/module_registry.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pydantic import BaseModel

    from ragent_python.core.router.intent import IntentPattern
    from ragent_python.infra.eval.contract import EvalSuite
    from ragent_python.infra.ingestion.schema_adapter import IngestionSchemaAdapter
    from ragent_python.infra.registries.retrieval_source import RetrievalSourceSpec
    from ragent_python.infra.registries.tool_pack import ToolPack


@dataclass(frozen=True, slots=True)
class ModuleHookResult:
    """Container for the things a module contributes at registration time."""

    tool_pack: "ToolPack | None" = None
    retrieval_sources: tuple["RetrievalSourceSpec", ...] = ()
    ingestion_adapters: tuple["IngestionSchemaAdapter", ...] = ()
    renderer_blocks: tuple[type["BaseModel"], ...] = ()
    intent_patterns: tuple["IntentPattern", ...] = ()
    evals: tuple["EvalSuite", ...] = ()


@runtime_checkable
class Module(Protocol):
    """Contract every business / platform module must satisfy.

    Implementations live in `modules/<name>/module.py`. The registry calls
    `register()` once at startup; the returned `ModuleHookResult` is fanned out
    to the appropriate sub-registries (tool pack, retrieval source, ingestion
    adapter, renderer block, intent pattern, eval suite).
    """

    name: str
    version: str

    def register(self) -> ModuleHookResult: ...
