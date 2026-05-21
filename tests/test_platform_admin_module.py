from __future__ import annotations

import unittest

from ragent_python.core.modules.contract import Module, ModuleHookResult
from ragent_python.infra.eval.registry import EvalSuiteRegistry
from ragent_python.infra.ingestion.schema_adapter import IngestionSchemaAdapterRegistry
from ragent_python.infra.registries.intent_pattern import IntentPatternRegistry
from ragent_python.infra.registries.module_registry import ModuleRegistry
from ragent_python.infra.registries.renderer_block import RendererBlockRegistry
from ragent_python.infra.registries.retrieval_source import RetrievalSourceRegistry
from ragent_python.infra.registries.tool_pack import ToolPackRegistry
from ragent_python.mcp.registry import get_mcp_tool, list_mcp_tools
from ragent_python.modules import bootstrap_default_modules
from ragent_python.modules.platform_admin import (
    PLATFORM_ADMIN_TOOLS,
    PlatformAdminModule,
    get_ingestion_task_tool,
    get_system_setting_tool,
    list_knowledge_bases_tool,
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


class PlatformAdminModuleTests(unittest.TestCase):
    def test_module_satisfies_module_protocol(self) -> None:
        self.assertIsInstance(PlatformAdminModule(), Module)
        self.assertEqual(PlatformAdminModule.name, "platform_admin")

    def test_register_returns_pack_with_three_legacy_tools(self) -> None:
        result = PlatformAdminModule().register()
        self.assertIsInstance(result, ModuleHookResult)
        self.assertIsNotNone(result.tool_pack)
        pack = result.tool_pack
        assert pack is not None  # narrow for type-checkers
        self.assertEqual(pack.name, "platform_admin")
        self.assertEqual(pack.module, "platform_admin")
        self.assertEqual(
            tuple(tool.name for tool in pack.tools),
            ("list_knowledge_bases", "get_system_setting", "get_ingestion_task"),
        )
        self.assertEqual(pack.tools, PLATFORM_ADMIN_TOOLS)

    def test_tools_preserve_legacy_metadata(self) -> None:
        self.assertFalse(list_knowledge_bases_tool.requires_admin)
        self.assertTrue(get_system_setting_tool.requires_admin)
        self.assertTrue(get_ingestion_task_tool.requires_admin)
        self.assertIn("knowledge base", list_knowledge_bases_tool.keywords)
        self.assertIn("setting", get_system_setting_tool.keywords)
        self.assertIn("ingestion task", get_ingestion_task_tool.keywords)

    def test_bootstrap_default_modules_publishes_pack_into_tool_pack_registry(
        self,
    ) -> None:
        registry = _build_isolated_registry()
        bootstrap_default_modules(registry=registry)

        self.assertEqual(
            [pack.name for pack in registry.tool_packs.list_packs()],
            ["platform_admin"],
        )
        self.assertEqual(
            tuple(tool.name for tool in registry.tool_packs.list_tools()),
            ("list_knowledge_bases", "get_system_setting", "get_ingestion_task"),
        )
        self.assertIs(
            registry.tool_packs.get_tool("list_knowledge_bases"),
            list_knowledge_bases_tool,
        )

    def test_bootstrap_default_modules_is_idempotent(self) -> None:
        registry = _build_isolated_registry()
        bootstrap_default_modules(registry=registry)
        # Second call must not raise duplicate-registration errors.
        bootstrap_default_modules(registry=registry)
        bootstrap_default_modules(registry=registry)
        self.assertEqual(len(registry.tool_packs.list_packs()), 1)
        self.assertEqual(len(registry.tool_packs.list_tools()), 3)

    def test_bootstrap_default_modules_survives_clear_cycle(self) -> None:
        registry = _build_isolated_registry()
        bootstrap_default_modules(registry=registry)
        self.assertEqual(len(registry.tool_packs.list_packs()), 1)

        registry.clear()
        self.assertEqual(registry.tool_packs.list_packs(), [])

        bootstrap_default_modules(registry=registry)
        self.assertEqual(
            tuple(tool.name for tool in registry.tool_packs.list_tools()),
            ("list_knowledge_bases", "get_system_setting", "get_ingestion_task"),
        )

    def test_legacy_mcp_registry_facade_returns_relocated_tools(self) -> None:
        # `get_mcp_tool` / `list_mcp_tools` now lazily bootstrap the default
        # `platform_admin` module against the global registry. The call must
        # still return the same three tools by name, with identity matching
        # the tools owned by the module.
        tools_by_name = {tool.name: tool for tool in list_mcp_tools()}
        self.assertIn("list_knowledge_bases", tools_by_name)
        self.assertIn("get_system_setting", tools_by_name)
        self.assertIn("get_ingestion_task", tools_by_name)

        self.assertIs(get_mcp_tool("list_knowledge_bases"), list_knowledge_bases_tool)
        self.assertIs(get_mcp_tool("get_system_setting"), get_system_setting_tool)
        self.assertIs(get_mcp_tool("get_ingestion_task"), get_ingestion_task_tool)
        self.assertIsNone(get_mcp_tool("does_not_exist"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
