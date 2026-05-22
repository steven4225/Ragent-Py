from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

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
from ragent_python.main import create_app
from ragent_python.modules import bootstrap_default_modules
from ragent_python.modules.ecommerce import (
    ECOMMERCE_SOURCE_NAME,
    EcommerceModule,
    PRODUCT_CATEGORIES,
    PRODUCT_KNOWLEDGE_BASE_ID,
    Product,
    ProductCardBlock,
    ProductCatalogFilters,
    ProductCatalogRetrievalProvider,
    load_products,
    product_to_card_block,
    search_products,
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


class EcommerceModuleProtocolTests(unittest.TestCase):
    def test_module_satisfies_module_protocol(self) -> None:
        self.assertIsInstance(EcommerceModule(), Module)

    def test_module_metadata(self) -> None:
        module = EcommerceModule()
        self.assertEqual(module.name, "ecommerce")
        self.assertTrue(module.version)

    def test_register_returns_expected_artifacts(self) -> None:
        result = EcommerceModule().register()
        self.assertIsInstance(result, ModuleHookResult)
        self.assertEqual(len(result.retrieval_sources), 1)
        spec = result.retrieval_sources[0]
        self.assertIsInstance(spec, RetrievalSourceSpec)
        self.assertEqual(spec.name, ECOMMERCE_SOURCE_NAME)
        self.assertEqual(spec.module, "ecommerce")
        self.assertEqual(spec.build_provider, ProductCatalogRetrievalProvider)
        self.assertEqual(len(result.renderer_blocks), 1)
        self.assertIs(result.renderer_blocks[0], ProductCardBlock)
        self.assertIsNone(result.tool_pack)
        self.assertEqual(result.ingestion_adapters, ())
        self.assertEqual(result.intent_patterns, ())
        self.assertEqual(result.evals, ())


class ProductCatalogTests(unittest.TestCase):
    def test_load_products_returns_fixture(self) -> None:
        products = load_products()
        self.assertGreaterEqual(len(products), 15)
        self.assertTrue(all(isinstance(item, Product) for item in products))
        categories = {product.category for product in products}
        for required_category in ("laptop", "phone", "tablet", "earbuds", "monitor"):
            self.assertIn(required_category, categories)

    def test_product_categories_constant_is_complete(self) -> None:
        products = load_products()
        for product in products:
            self.assertIn(product.category, PRODUCT_CATEGORIES)

    def test_empty_query_returns_recent_first(self) -> None:
        results = search_products("", limit=5)
        self.assertEqual(len(results), 5)
        years = [product.release_year for product in results]
        self.assertEqual(years, sorted(years, reverse=True))

    def test_category_filter_constrains_results(self) -> None:
        results = search_products(
            "",
            filters=ProductCatalogFilters(category="phone"),
            limit=10,
        )
        self.assertTrue(results)
        self.assertTrue(all(product.category == "phone" for product in results))

    def test_max_price_filter(self) -> None:
        results = search_products(
            "",
            filters=ProductCatalogFilters(max_price_usd=800.0),
            limit=20,
        )
        self.assertTrue(results)
        self.assertTrue(all(product.price_usd <= 800.0 for product in results))

    def test_min_ram_filter_skips_missing_ram_products(self) -> None:
        results = search_products(
            "",
            filters=ProductCatalogFilters(min_ram_gb=16),
            limit=20,
        )
        self.assertTrue(results)
        for product in results:
            self.assertIsNotNone(product.ram_gb)
            assert product.ram_gb is not None  # for type narrowing
            self.assertGreaterEqual(product.ram_gb, 16)

    def test_keyword_search_orders_by_score(self) -> None:
        results = search_products("macbook", limit=10)
        self.assertTrue(results)
        for product in results:
            haystack = (
                product.name + " " + product.brand + " " + product.summary
            ).lower()
            self.assertIn("macbook", haystack)


class ProductCardBlockTests(unittest.TestCase):
    def test_block_type_literal(self) -> None:
        product = load_products()[0]
        block = product_to_card_block(product)
        self.assertIsInstance(block, ProductCardBlock)
        self.assertEqual(block.type, "product_card")
        self.assertEqual(block.product_id, product.product_id)
        self.assertEqual(block.price_usd, product.price_usd)

    def test_block_includes_human_specs(self) -> None:
        product = next(
            item for item in load_products() if item.product_id == "laptop-macbook-pro-14-m3pro"
        )
        block = product_to_card_block(product)
        labels = [spec.label for spec in block.specs]
        self.assertIn("Display", labels)
        self.assertIn("Chip", labels)
        self.assertIn("Memory", labels)
        self.assertIn("Storage", labels)

    def test_block_omits_specs_for_monitors_without_chip(self) -> None:
        product = next(
            item for item in load_products() if item.category == "monitor"
        )
        block = product_to_card_block(product)
        labels = [spec.label for spec in block.specs]
        self.assertNotIn("Chip", labels)
        self.assertNotIn("Memory", labels)


class ProductCatalogRetrievalProviderTests(unittest.TestCase):
    def test_search_returns_chunks_with_product_metadata(self) -> None:
        provider = ProductCatalogRetrievalProvider()
        request = InternalRetrievalRequestModel(
            traceId="trace-eco-1",
            query="macbook",
            knowledgeBaseIds=[PRODUCT_KNOWLEDGE_BASE_ID],
            topK=3,
        )
        chunks = provider.search(request)
        self.assertGreater(len(chunks), 0)
        self.assertLessEqual(len(chunks), 3)
        for chunk in chunks:
            self.assertTrue(chunk.chunkId.startswith("product:"))
            self.assertEqual(chunk.knowledgeBaseId, PRODUCT_KNOWLEDGE_BASE_ID)
            self.assertEqual(chunk.source, provider.provider_name)
            self.assertIn("price_usd", chunk.metadata)
            self.assertIn("brand", chunk.metadata)
            self.assertEqual(chunk.metadata["provider"], "ecommerce-catalog")

    def test_filters_passed_through(self) -> None:
        provider = ProductCatalogRetrievalProvider()
        request = InternalRetrievalRequestModel(
            traceId="trace-eco-2",
            query="",
            knowledgeBaseIds=[PRODUCT_KNOWLEDGE_BASE_ID],
            topK=20,
            filters={"category": "phone", "max_price_usd": 900.0},
        )
        chunks = provider.search(request)
        self.assertTrue(chunks)
        for chunk in chunks:
            self.assertEqual(chunk.metadata["category"], "phone")
            self.assertLessEqual(float(chunk.metadata["price_usd"]), 900.0)


class EcommerceBootstrapTests(unittest.TestCase):
    def test_bootstrap_registers_ecommerce_alongside_existing_modules(self) -> None:
        registry = _build_isolated_registry()
        bootstrap_default_modules(registry)
        names = {module.name for module in registry.list_modules()}
        self.assertEqual(
            names, {"platform_admin", "demo_corpus", "ecommerce"}
        )

    def test_bootstrap_publishes_retrieval_source_and_renderer_block(self) -> None:
        registry = _build_isolated_registry()
        bootstrap_default_modules(registry)
        source_names = {spec.name for spec in registry.retrieval_sources.list_specs()}
        self.assertIn(ECOMMERCE_SOURCE_NAME, source_names)
        block_classes = registry.renderer_blocks
        type_literals = {
            cls.model_fields["type"].default for cls in block_classes
        }
        self.assertIn("product_card", type_literals)

    def test_bootstrap_is_idempotent(self) -> None:
        registry = _build_isolated_registry()
        bootstrap_default_modules(registry)
        bootstrap_default_modules(registry)
        self.assertEqual(len(registry.list_modules()), 3)
        self.assertEqual(
            len(registry.retrieval_sources.list_specs()),
            2,  # demo_corpus + ecommerce_catalog
        )

    def test_selector_activates_on_empty_kb_filter(self) -> None:
        spec = (
            EcommerceModule()
            .register()
            .retrieval_sources[0]
        )
        request = InternalRetrievalRequestModel(traceId="t", query="x")
        self.assertTrue(spec.selector(request))

    def test_selector_activates_on_matching_kb(self) -> None:
        spec = (
            EcommerceModule()
            .register()
            .retrieval_sources[0]
        )
        request = InternalRetrievalRequestModel(
            traceId="t",
            query="x",
            knowledgeBaseIds=[PRODUCT_KNOWLEDGE_BASE_ID, "kb_other"],
        )
        self.assertTrue(spec.selector(request))

    def test_selector_skips_unrelated_kb(self) -> None:
        spec = (
            EcommerceModule()
            .register()
            .retrieval_sources[0]
        )
        request = InternalRetrievalRequestModel(
            traceId="t",
            query="x",
            knowledgeBaseIds=["kb_policy"],
        )
        self.assertFalse(spec.selector(request))


class InternalEcommerceEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_search_returns_product_card_blocks(self) -> None:
        response = self.client.post(
            "/internal/ecommerce/search",
            json={"query": "macbook", "limit": 3},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["source"], "ecommerce-catalog-preview")
        self.assertEqual(body["query"], "macbook")
        self.assertGreaterEqual(body["total"], 1)
        self.assertLessEqual(body["total"], 3)
        for block in body["blocks"]:
            self.assertEqual(block["type"], "product_card")
            self.assertIn("name", block)
            self.assertIn("price_usd", block)
            self.assertIn("specs", block)

    def test_search_respects_filters(self) -> None:
        response = self.client.post(
            "/internal/ecommerce/search",
            json={
                "query": "",
                "filters": {"category": "monitor"},
                "limit": 5,
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertGreaterEqual(body["total"], 1)
        for block in body["blocks"]:
            self.assertEqual(block["category"], "monitor")

    def test_empty_query_returns_recent_catalog(self) -> None:
        response = self.client.post(
            "/internal/ecommerce/search",
            json={"query": "", "limit": 5},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 5)


if __name__ == "__main__":
    unittest.main()
