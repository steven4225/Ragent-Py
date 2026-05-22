from __future__ import annotations

import unittest

from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.core.modules.contract import Module, ModuleHookResult
from ragent_python.infra.eval.registry import EvalSuiteRegistry
from ragent_python.infra.ingestion.schema_adapter import IngestionSchemaAdapterRegistry
from ragent_python.infra.registries.intent_pattern import IntentPatternRegistry
from ragent_python.infra.registries.module_registry import ModuleRegistry
from ragent_python.infra.registries.renderer_block import RendererBlockRegistry
from ragent_python.infra.registries.retrieval_source import (
    RetrievalSourceRegistry,
    RetrievalSourceSpec,
)
from ragent_python.infra.registries.tool_pack import ToolPackRegistry
from ragent_python.modules import bootstrap_default_modules
from ragent_python.modules.demo_corpus import (
    DEMO_CORPUS_SOURCE_NAME,
    LOCAL_KNOWLEDGE,
    DemoCorpusModule,
    LocalStaticRetrievalProvider,
    iter_local_corpus,
)


def _build_isolated_registry() -> ModuleRegistry:
    return ModuleRegistry(
        tool_packs=ToolPackRegistry(),
        retrieval_sources=RetrievalSourceRegistry(),
        ingestion_adapters=IngestionSchemaAdapterRegistry(),
        renderer_blocks=RendererBlockRegistry(),
        intent_patterns=IntentPatternRegistry(),
        eval_suites=EvalSuiteRegistry(),
    )


class DemoCorpusModuleTests(unittest.TestCase):
    def test_module_satisfies_module_protocol(self) -> None:
        self.assertIsInstance(DemoCorpusModule(), Module)
        self.assertEqual(DemoCorpusModule.name, "demo_corpus")
        self.assertEqual(DemoCorpusModule.version, "0.1.0")

    def test_register_emits_single_retrieval_source_spec(self) -> None:
        result = DemoCorpusModule().register()
        self.assertIsInstance(result, ModuleHookResult)
        self.assertIsNone(result.tool_pack)
        self.assertEqual(len(result.retrieval_sources), 1)
        spec = result.retrieval_sources[0]
        self.assertIsInstance(spec, RetrievalSourceSpec)
        self.assertEqual(spec.name, DEMO_CORPUS_SOURCE_NAME)
        self.assertEqual(spec.module, "demo_corpus")
        self.assertEqual(spec.fusion_weight, 1.0)
        self.assertTrue(spec.description)

    def test_spec_build_provider_returns_local_static_provider(self) -> None:
        spec = DemoCorpusModule().register().retrieval_sources[0]
        provider = spec.build_provider()
        self.assertIsInstance(provider, LocalStaticRetrievalProvider)
        self.assertEqual(provider.provider_name, "python-local-retrieval")

    def test_selector_activates_when_no_kb_filter(self) -> None:
        spec = DemoCorpusModule().register().retrieval_sources[0]
        request = InternalRetrievalRequestModel(traceId="t1", query="payroll")
        self.assertTrue(spec.selector(request))

    def test_selector_activates_when_demo_kb_is_requested(self) -> None:
        spec = DemoCorpusModule().register().retrieval_sources[0]
        request = InternalRetrievalRequestModel(
            traceId="t1", query="payroll", knowledgeBaseIds=["kb_policy"]
        )
        self.assertTrue(spec.selector(request))

    def test_selector_skips_when_only_unknown_kbs_requested(self) -> None:
        spec = DemoCorpusModule().register().retrieval_sources[0]
        request = InternalRetrievalRequestModel(
            traceId="t1", query="payroll", knowledgeBaseIds=["kb_ingested_only"]
        )
        self.assertFalse(spec.selector(request))

    def test_provider_returns_expected_chunks_for_payroll_query(self) -> None:
        provider = LocalStaticRetrievalProvider()
        request = InternalRetrievalRequestModel(traceId="t1", query="payroll benefits")
        results = provider.search(request, ["payroll", "benefits"])
        chunk_ids = [chunk.chunkId for chunk in results]
        self.assertIn("chunk_policy_payroll", chunk_ids)
        for chunk in results:
            self.assertEqual(chunk.source, "python-local-retrieval")
            self.assertEqual(chunk.metadata["provider"], "local-static")

    def test_provider_search_falls_back_to_internal_term_extraction(self) -> None:
        provider = LocalStaticRetrievalProvider()
        request = InternalRetrievalRequestModel(traceId="t1", query="payroll benefits")
        explicit = provider.search(request, ["payroll", "benefits"])
        implicit = provider.search(request)
        self.assertEqual(
            [chunk.chunkId for chunk in explicit],
            [chunk.chunkId for chunk in implicit],
        )

    def test_iter_local_corpus_back_compat_shape_preserved(self) -> None:
        request = InternalRetrievalRequestModel(traceId="t1", query="anything")
        chunks = iter_local_corpus(request)
        self.assertEqual(len(chunks), len(LOCAL_KNOWLEDGE))
        self.assertEqual(
            tuple(chunk.chunk_id for chunk in chunks),
            tuple(chunk.chunk_id for chunk in LOCAL_KNOWLEDGE),
        )
        for chunk in chunks:
            self.assertEqual(chunk.source, "python-local-retrieval")
            self.assertEqual(chunk.metadata, {"provider": "local-static"})

    def test_iter_local_corpus_filters_by_requested_kbs(self) -> None:
        request = InternalRetrievalRequestModel(
            traceId="t1", query="anything", knowledgeBaseIds=["kb_policy"]
        )
        chunks = iter_local_corpus(request)
        self.assertEqual(
            sorted(chunk.knowledge_base_id for chunk in chunks),
            ["kb_policy", "kb_policy"],
        )

    def test_retrieval_corpus_re_exports_from_module(self) -> None:
        from ragent_python.retrieval import corpus as legacy_corpus

        self.assertIs(legacy_corpus.iter_local_corpus, iter_local_corpus)
        self.assertIs(legacy_corpus.LOCAL_KNOWLEDGE, LOCAL_KNOWLEDGE)

    def test_retrieval_providers_re_exports_local_static_provider(self) -> None:
        from ragent_python.retrieval import providers as legacy_providers

        self.assertIs(legacy_providers.LocalStaticRetrievalProvider, LocalStaticRetrievalProvider)

    def test_bootstrap_default_modules_publishes_spec_into_retrieval_source_registry(
        self,
    ) -> None:
        registry = _build_isolated_registry()
        bootstrap_default_modules(registry=registry)

        specs = registry.retrieval_sources.list_specs()
        self.assertEqual(
            sorted(spec.name for spec in specs),
            [DEMO_CORPUS_SOURCE_NAME],
        )
        spec = registry.retrieval_sources.get(DEMO_CORPUS_SOURCE_NAME)
        self.assertIsNotNone(spec)
        assert spec is not None  # narrow for type-checkers
        self.assertEqual(spec.module, "demo_corpus")

    def test_resolve_returns_demo_spec_for_default_request(self) -> None:
        registry = _build_isolated_registry()
        bootstrap_default_modules(registry=registry)

        request = InternalRetrievalRequestModel(traceId="t1", query="payroll")
        resolved = registry.retrieval_sources.resolve(request)
        self.assertEqual([spec.name for spec in resolved], [DEMO_CORPUS_SOURCE_NAME])

    def test_resolve_skips_demo_spec_when_request_targets_unknown_kb(self) -> None:
        registry = _build_isolated_registry()
        bootstrap_default_modules(registry=registry)

        request = InternalRetrievalRequestModel(
            traceId="t1", query="payroll", knowledgeBaseIds=["kb_ingested_only"]
        )
        self.assertEqual(registry.retrieval_sources.resolve(request), [])

    def test_resolved_provider_search_matches_legacy_local_provider(self) -> None:
        registry = _build_isolated_registry()
        bootstrap_default_modules(registry=registry)

        request = InternalRetrievalRequestModel(
            traceId="t1", query="incident response runbook"
        )
        resolved = registry.retrieval_sources.resolve(request)
        self.assertEqual(len(resolved), 1)
        provider = resolved[0].build_provider()
        via_registry = provider.search(request, ["incident", "response", "runbook"])
        via_legacy = LocalStaticRetrievalProvider().search(
            request, ["incident", "response", "runbook"]
        )
        self.assertEqual(
            [chunk.chunkId for chunk in via_registry],
            [chunk.chunkId for chunk in via_legacy],
        )
        self.assertEqual(
            [chunk.score for chunk in via_registry],
            [chunk.score for chunk in via_legacy],
        )

    def test_bootstrap_default_modules_is_idempotent_for_demo_corpus(self) -> None:
        registry = _build_isolated_registry()
        bootstrap_default_modules(registry=registry)
        bootstrap_default_modules(registry=registry)
        bootstrap_default_modules(registry=registry)
        self.assertEqual(len(registry.retrieval_sources.list_specs()), 1)

    def test_bootstrap_default_modules_survives_clear_cycle(self) -> None:
        registry = _build_isolated_registry()
        bootstrap_default_modules(registry=registry)
        self.assertEqual(len(registry.retrieval_sources.list_specs()), 1)

        registry.clear()
        self.assertEqual(registry.retrieval_sources.list_specs(), [])

        bootstrap_default_modules(registry=registry)
        names = sorted(spec.name for spec in registry.retrieval_sources.list_specs())
        self.assertEqual(names, [DEMO_CORPUS_SOURCE_NAME])


if __name__ == "__main__":
    unittest.main()
