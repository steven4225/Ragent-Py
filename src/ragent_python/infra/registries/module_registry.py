"""Module registry — the platform entrypoint that fans a module's contributions
out to the sub-registries.

Usage at startup (Step B+):

    registry = default_module_registry
    registry.register(PlatformAdminModule())
    registry.register(EcommerceModule())
    registry.bootstrap()

`bootstrap()` is idempotent and calls each module's `register()` exactly once,
publishing its tool packs, retrieval sources, ingestion adapters, renderer
blocks, intent patterns, and eval suites into the corresponding default
sub-registries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ragent_python.core.modules.contract import Module, ModuleHookResult
from ragent_python.infra.registries.retrieval_source import (
    RetrievalSourceRegistry,
    default_retrieval_source_registry,
)
from ragent_python.infra.registries.tool_pack import (
    ToolPackRegistry,
    default_tool_pack_registry,
)

if TYPE_CHECKING:
    from pydantic import BaseModel

    from ragent_python.core.router.intent import IntentPattern
    from ragent_python.infra.eval.contract import EvalSuite
    from ragent_python.infra.ingestion.schema_adapter import IngestionSchemaAdapter


class ModuleRegistry:
    def __init__(
        self,
        *,
        tool_packs: ToolPackRegistry | None = None,
        retrieval_sources: RetrievalSourceRegistry | None = None,
    ) -> None:
        self._modules: dict[str, Module] = {}
        self._bootstrapped: set[str] = set()
        self._tool_packs = tool_packs or default_tool_pack_registry
        self._retrieval_sources = retrieval_sources or default_retrieval_source_registry

        self._ingestion_adapters: list["IngestionSchemaAdapter"] = []
        self._renderer_blocks: list[type["BaseModel"]] = []
        self._intent_patterns: list["IntentPattern"] = []
        self._eval_suites: list["EvalSuite"] = []

    def register(self, module: Module) -> None:
        if module.name in self._modules:
            raise ValueError(f"Module '{module.name}' already registered.")
        self._modules[module.name] = module

    def list_modules(self) -> list[Module]:
        return list(self._modules.values())

    def bootstrap(self) -> None:
        for name, module in self._modules.items():
            if name in self._bootstrapped:
                continue
            result = module.register()
            self._apply(result)
            self._bootstrapped.add(name)

    def _apply(self, result: ModuleHookResult) -> None:
        if result.tool_pack is not None:
            self._tool_packs.register(result.tool_pack)
        for source in result.retrieval_sources:
            self._retrieval_sources.register(source)
        self._ingestion_adapters.extend(result.ingestion_adapters)
        self._renderer_blocks.extend(result.renderer_blocks)
        self._intent_patterns.extend(result.intent_patterns)
        self._eval_suites.extend(result.evals)

    @property
    def ingestion_adapters(self) -> list["IngestionSchemaAdapter"]:
        return list(self._ingestion_adapters)

    @property
    def renderer_blocks(self) -> list[type["BaseModel"]]:
        return list(self._renderer_blocks)

    @property
    def intent_patterns(self) -> list["IntentPattern"]:
        return list(self._intent_patterns)

    @property
    def eval_suites(self) -> list["EvalSuite"]:
        return list(self._eval_suites)

    def clear(self) -> None:
        self._modules.clear()
        self._bootstrapped.clear()
        self._ingestion_adapters.clear()
        self._renderer_blocks.clear()
        self._intent_patterns.clear()
        self._eval_suites.clear()


default_module_registry = ModuleRegistry()
