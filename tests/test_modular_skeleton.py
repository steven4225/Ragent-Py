from __future__ import annotations

import asyncio
import unittest
from typing import Literal

from pydantic import BaseModel

from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.core.generation.adapter import (
    GenerationAdapter,
    GenerationMessage,
    GenerationRequest,
)
from ragent_python.core.modules.contract import Module, ModuleHookResult
from ragent_python.core.router.intent import IntentPattern
from ragent_python.infra.eval.contract import EvalCase, EvalMetric, EvalMetricResult, EvalSuite
from ragent_python.infra.eval.registry import EvalSuiteRegistry
from ragent_python.infra.ingestion.schema_adapter import (
    IngestionSchemaAdapter,
    IngestionSchemaAdapterRegistry,
    StructuredRecord,
)
from ragent_python.infra.llm.mock import MockGenerationAdapter
from ragent_python.infra.llm.resolver import (
    clear_resolver_cache,
    list_known_providers,
    resolve_generation_adapter,
)
from ragent_python.infra.registries.intent_pattern import IntentPatternRegistry
from ragent_python.infra.registries.module_registry import ModuleRegistry
from ragent_python.infra.registries.renderer_block import RendererBlockRegistry
from ragent_python.infra.registries.retrieval_source import (
    RetrievalSourceRegistry,
    RetrievalSourceSpec,
)
from ragent_python.infra.registries.tool_pack import (
    ToolPack,
    ToolPackRegistry,
)
from ragent_python.mcp.registry import MCPToolDefinition
from ragent_python.ui_contracts.blocks import (
    AssistantMessageBlocks,
    EvidenceBlock,
    EvidenceChunk,
    TextBlock,
    ToolCallBlock,
)


class _StubModule:
    name = "stub"
    version = "0.1.0"

    def __init__(self, hooks: ModuleHookResult) -> None:
        self._hooks = hooks

    def register(self) -> ModuleHookResult:
        return self._hooks


class ModularSkeletonTests(unittest.TestCase):
    def test_module_protocol_runtime_check_accepts_stub(self) -> None:
        module = _StubModule(ModuleHookResult())
        self.assertIsInstance(module, Module)

    def test_tool_pack_registry_round_trip(self) -> None:
        registry = ToolPackRegistry()
        tool = MCPToolDefinition(
            name="echo",
            description="Echo args.",
            keywords=("echo",),
            requires_admin=False,
            execute=lambda args, ctx: {"summary": "ok", "data": args},
        )
        pack = ToolPack(name="demo", module="stub", tools=(tool,))
        registry.register(pack)

        self.assertEqual(registry.list_packs(), [pack])
        self.assertEqual(registry.list_tools(packs=["demo"]), [tool])
        self.assertIs(registry.get_tool("echo"), tool)
        self.assertIsNone(registry.get_tool("missing"))

        with self.assertRaises(ValueError):
            registry.register(pack)

    def test_retrieval_source_registry_resolves_by_selector(self) -> None:
        registry = RetrievalSourceRegistry()

        class _StubProvider:
            provider_name = "stub"

            def search(self, *_args, **_kwargs):  # pragma: no cover - not invoked
                return []

        always_spec = RetrievalSourceSpec(
            name="always",
            module="stub",
            build_provider=_StubProvider,
            selector=lambda _request: True,
        )
        never_spec = RetrievalSourceSpec(
            name="never",
            module="stub",
            build_provider=_StubProvider,
            selector=lambda _request: False,
        )
        registry.register(always_spec)
        registry.register(never_spec)

        request = InternalRetrievalRequestModel(traceId="t1", query="hello")
        resolved = registry.resolve(request)
        self.assertEqual([spec.name for spec in resolved], ["always"])

    def test_module_registry_bootstrap_fan_out(self) -> None:
        hooks, harness = _build_full_hook_fixture()
        registry = _build_isolated_module_registry(harness)

        registry.register(_StubModule(hooks))
        registry.bootstrap()
        registry.bootstrap()

        self.assertEqual(harness.tool_packs.list_packs(), [hooks.tool_pack])
        self.assertEqual(
            [spec.name for spec in harness.retrieval_sources.list_specs()],
            [hooks.retrieval_sources[0].name],
        )
        self.assertEqual(
            harness.ingestion_adapters.list_adapters(),
            list(hooks.ingestion_adapters),
        )
        self.assertEqual(
            harness.renderer_blocks.list_blocks(),
            list(hooks.renderer_blocks),
        )
        self.assertEqual(
            harness.intent_patterns.list_patterns(),
            list(hooks.intent_patterns),
        )
        self.assertEqual(
            harness.eval_suites.list_suites(),
            list(hooks.evals),
        )

        self.assertEqual(registry.ingestion_adapters, list(hooks.ingestion_adapters))
        self.assertEqual(registry.renderer_blocks, list(hooks.renderer_blocks))
        self.assertEqual(registry.intent_patterns, list(hooks.intent_patterns))
        self.assertEqual(registry.eval_suites, list(hooks.evals))

    def test_module_registry_clear_resets_sub_registries(self) -> None:
        hooks, harness = _build_full_hook_fixture()
        registry = _build_isolated_module_registry(harness)

        registry.register(_StubModule(hooks))
        registry.bootstrap()

        registry.clear()
        self.assertEqual(harness.tool_packs.list_packs(), [])
        self.assertEqual(harness.retrieval_sources.list_specs(), [])
        self.assertEqual(harness.ingestion_adapters.list_adapters(), [])
        self.assertEqual(harness.renderer_blocks.list_blocks(), [])
        self.assertEqual(harness.intent_patterns.list_patterns(), [])
        self.assertEqual(harness.eval_suites.list_suites(), [])

        registry.register(_StubModule(hooks))
        registry.bootstrap()
        self.assertEqual(harness.tool_packs.list_packs(), [hooks.tool_pack])
        self.assertEqual(
            harness.eval_suites.list_suites(),
            list(hooks.evals),
        )

    def test_ingestion_schema_adapter_registry_resolves_first_match(self) -> None:
        registry = IngestionSchemaAdapterRegistry()

        class _StubAdapter:
            name = "stub.adapter"
            module = "stub"

            def __init__(self, accept: bool) -> None:
                self._accept = accept

            def accepts(self, source) -> bool:
                return self._accept

            def parse(self, raw, source):  # pragma: no cover - not invoked
                return []

            def to_chunks(self, records):  # pragma: no cover - not invoked
                return []

        rejecting = _StubAdapter(accept=False)
        accepting = _StubAdapter(accept=True)
        registry.register(rejecting)
        accepting.name = "stub.accepting"
        registry.register(accepting)

        from ragent_python.contracts.ingestion import IngestionSourceModel

        source = IngestionSourceModel(
            sourceType="knowledge-import",
            uri="data:application/json,{}",
            filename="x.json",
            mimeType="application/json",
            sizeBytes=2,
        )
        self.assertIs(registry.resolve(source), accepting)
        self.assertIsInstance(accepting, IngestionSchemaAdapter)
        self.assertIsInstance(StructuredRecord(), StructuredRecord)

    def test_mock_generation_adapter_renders_legacy_template(self) -> None:
        adapter = MockGenerationAdapter()
        self.assertIsInstance(adapter, GenerationAdapter)
        request = GenerationRequest(
            messages=[GenerationMessage(role="user", content="hello world")],
        )
        result = asyncio.run(adapter.generate(request))
        self.assertEqual(result.provider, "mock")
        self.assertEqual(result.finish_reason, "stop")
        self.assertIn("hello world", result.text)
        self.assertIn("Python chat runtime is active.", result.text)

    def test_resolver_falls_back_to_mock_when_only_mock_is_known(self) -> None:
        clear_resolver_cache()
        adapter = resolve_generation_adapter()
        self.assertEqual(adapter.name, "mock")
        self.assertIn("mock", list_known_providers())

    def test_renderer_blocks_serialize(self) -> None:
        payload = AssistantMessageBlocks(
            trace_id="chat_abc",
            blocks=[
                TextBlock(content="hello"),
                EvidenceBlock(
                    chunks=[
                        EvidenceChunk(
                            chunk_id="c1",
                            title="t",
                            content="body",
                            source="local",
                            score=0.9,
                        )
                    ]
                ),
                ToolCallBlock(
                    tool_call_id="tc1",
                    tool_name="echo",
                    status="succeeded",
                    args={"x": 1},
                    summary="ok",
                ),
            ],
        )
        dumped = payload.model_dump()
        self.assertEqual([block["type"] for block in dumped["blocks"]], ["text", "evidence", "tool_call"])

    def test_eval_suite_holds_metrics_and_cases(self) -> None:
        def _ones(_q: str, _a: str, _c: list[str]) -> EvalMetricResult:
            return EvalMetricResult(metric="stub", score=1.0)

        from ragent_python.infra.eval.contract import EvalMetric

        suite = EvalSuite(
            name="stub.suite",
            module="stub",
            cases=(EvalCase(case_id="c1", query="hello"),),
            metrics=(EvalMetric(name="stub", description="constant", compute=_ones),),
        )
        self.assertEqual(suite.cases[0].case_id, "c1")
        self.assertEqual(suite.metrics[0].compute("", "", []).score, 1.0)


class _StubRendererBlock(BaseModel):
    type: Literal["stub.block"] = "stub.block"
    value: str = ""


class _RegistryHarness:
    def __init__(self) -> None:
        self.tool_packs = ToolPackRegistry()
        self.retrieval_sources = RetrievalSourceRegistry()
        self.ingestion_adapters = IngestionSchemaAdapterRegistry()
        self.renderer_blocks = RendererBlockRegistry()
        self.intent_patterns = IntentPatternRegistry()
        self.eval_suites = EvalSuiteRegistry()


class _StubProvider:
    provider_name = "stub"

    def search(self, *_args, **_kwargs):  # pragma: no cover - not invoked
        return []


class _StubIngestionAdapter:
    name = "stub.ingestion"
    module = "stub"

    def accepts(self, _source) -> bool:  # pragma: no cover - not invoked
        return False

    def parse(self, _raw, _source):  # pragma: no cover - not invoked
        return []

    def to_chunks(self, _records):  # pragma: no cover - not invoked
        return []


def _stub_metric(_q: str, _a: str, _c: list[str]) -> EvalMetricResult:
    return EvalMetricResult(metric="stub", score=1.0)


def _build_full_hook_fixture() -> tuple[ModuleHookResult, _RegistryHarness]:
    tool = MCPToolDefinition(
        name="echo",
        description="Echo args.",
        keywords=("echo",),
        requires_admin=False,
        execute=lambda args, ctx: {"summary": "ok", "data": args},
    )
    pack = ToolPack(name="stub-pack", module="stub", tools=(tool,))
    retrieval_spec = RetrievalSourceSpec(
        name="stub.source",
        module="stub",
        build_provider=_StubProvider,
        selector=lambda _request: True,
    )
    intent = IntentPattern(name="stub.intent", module="stub", keywords=("foo",))
    suite = EvalSuite(
        name="stub.suite",
        module="stub",
        cases=(EvalCase(case_id="c1", query="hello"),),
        metrics=(EvalMetric(name="stub", description="constant", compute=_stub_metric),),
    )
    hooks = ModuleHookResult(
        tool_pack=pack,
        retrieval_sources=(retrieval_spec,),
        ingestion_adapters=(_StubIngestionAdapter(),),
        renderer_blocks=(_StubRendererBlock,),
        intent_patterns=(intent,),
        evals=(suite,),
    )
    return hooks, _RegistryHarness()


def _build_isolated_module_registry(harness: _RegistryHarness) -> ModuleRegistry:
    return ModuleRegistry(
        tool_packs=harness.tool_packs,
        retrieval_sources=harness.retrieval_sources,
        ingestion_adapters=harness.ingestion_adapters,
        renderer_blocks=harness.renderer_blocks,
        intent_patterns=harness.intent_patterns,
        eval_suites=harness.eval_suites,
    )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
