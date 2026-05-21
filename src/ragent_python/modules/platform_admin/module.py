"""`PlatformAdminModule` — first real `core.modules.Module` implementation.

It contributes a single `ToolPack` named ``"platform_admin"`` that bundles the
three legacy MCP tools (`list_knowledge_bases`, `get_system_setting`,
`get_ingestion_task`). The module declares no retrieval sources, ingestion
adapters, renderer blocks, intent patterns or eval suites yet; those land in
later steps if/when platform-admin grows them.
"""

from __future__ import annotations

from ragent_python.core.modules.contract import ModuleHookResult
from ragent_python.infra.registries.tool_pack import ToolPack
from ragent_python.modules.platform_admin.tools import PLATFORM_ADMIN_TOOLS


class PlatformAdminModule:
    name = "platform_admin"
    version = "0.1.0"

    def register(self) -> ModuleHookResult:
        pack = ToolPack(
            name="platform_admin",
            module=self.name,
            tools=PLATFORM_ADMIN_TOOLS,
            description=(
                "Platform-level introspection tools (knowledge base listing, "
                "system setting reads, ingestion task status)."
            ),
        )
        return ModuleHookResult(tool_pack=pack)
