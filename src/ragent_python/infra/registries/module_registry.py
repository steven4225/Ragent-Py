"""Module registry — the platform entrypoint that fans a module's
contributions out to dedicated sub-registries.

Usage at startup (Step B+):

    registry = default_module_registry
    registry.register(PlatformAdminModule())
    registry.register(EcommerceModule())
    registry.bootstrap()

`bootstrap()` is idempotent and calls each module's `register()` exactly
once. The returned `ModuleHookResult` is fanned out so that every artifact
a module ships ends up globally discoverable on its own sub-registry:

    tool_pack            -> ToolPackRegistry
    retrieval_sources    -> RetrievalSourceRegistry
    ingestion_adapters   -> IngestionSchemaAdapterRegistry
    renderer_blocks      -> RendererBlockRegistry
    intent_patterns      -> IntentPatternRegistry
    evals                -> EvalSuiteRegistry

`ModuleRegistry` itself does *not* keep parallel internal lists. The
properties below are thin proxies onto the sub-registries, so there is a
single source of truth per artifact type. `clear()` cascades into every
sub-registry it coordinates so that a `clear → register → bootstrap`
cycle starts from a clean slate (this is what tests rely on).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ragent_python.core.modules.contract import Module, ModuleHookResult
from ragent_python.infra.eval.registry import (
    EvalSuiteRegistry,
    default_eval_suite_registry,
)
from ragent_python.infra.ingestion.schema_adapter import (
    IngestionSchemaAdapterRegistry,
    default_ingestion_schema_adapter_registry,
)
from ragent_python.infra.registries.intent_pattern import (
    IntentPatternRegistry,
    default_intent_pattern_registry,
)
from ragent_python.infra.registries.renderer_block import (
    RendererBlockRegistry,
    default_renderer_block_registry,
)
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
        ingestion_adapters: IngestionSchemaAdapterRegistry | None = None,
        renderer_blocks: RendererBlockRegistry | None = None,
        intent_patterns: IntentPatternRegistry | None = None,
        eval_suites: EvalSuiteRegistry | None = None,
    ) -> None:
        self._modules: dict[str, Module] = {}
        self._bootstrapped: set[str] = set()
        self._tool_packs = tool_packs or default_tool_pack_registry
        self._retrieval_sources = retrieval_sources or default_retrieval_source_registry
        self._ingestion_adapters = (
            ingestion_adapters or default_ingestion_schema_adapter_registry
        )
        self._renderer_blocks = renderer_blocks or default_renderer_block_registry
        self._intent_patterns = intent_patterns or default_intent_pattern_registry
        self._eval_suites = eval_suites or default_eval_suite_registry

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
        for adapter in result.ingestion_adapters:
            self._ingestion_adapters.register(adapter)
        for block_cls in result.renderer_blocks:
            self._renderer_blocks.register(block_cls)
        for pattern in result.intent_patterns:
            self._intent_patterns.register(pattern)
        for suite in result.evals:
            self._eval_suites.register(suite)

    @property
    def tool_packs(self) -> ToolPackRegistry:
        return self._tool_packs

    @property
    def retrieval_sources(self) -> RetrievalSourceRegistry:
        return self._retrieval_sources

    @property
    def ingestion_adapters(self) -> list["IngestionSchemaAdapter"]:
        return self._ingestion_adapters.list_adapters()

    @property
    def renderer_blocks(self) -> list[type["BaseModel"]]:
        return self._renderer_blocks.list_blocks()

    @property
    def intent_patterns(self) -> list["IntentPattern"]:
        return self._intent_patterns.list_patterns()

    @property
    def eval_suites(self) -> list["EvalSuite"]:
        return self._eval_suites.list_suites()

    def clear(self) -> None:
        """Reset this registry *and* every sub-registry it coordinates.

        After `clear()` the same `ModuleRegistry` instance can be reused via
        `register() → bootstrap()` without triggering duplicate-registration
        errors on the sub-registries. Tests use this for isolation.
        """

        self._modules.clear()
        self._bootstrapped.clear()
        self._tool_packs.clear()
        self._retrieval_sources.clear()
        self._ingestion_adapters.clear()
        self._renderer_blocks.clear()
        self._intent_patterns.clear()
        self._eval_suites.clear()


default_module_registry = ModuleRegistry()
