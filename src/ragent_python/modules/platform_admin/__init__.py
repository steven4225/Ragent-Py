"""Platform-admin module.

Owns the platform-level introspection tools (knowledge-base listing, system
setting reads, ingestion task status) that used to live inline in
`mcp/registry.py`. After Step B these are contributed via a regular module
`ToolPack` so the rest of the platform stops treating them as built-ins.
"""

from ragent_python.modules.platform_admin.module import PlatformAdminModule
from ragent_python.modules.platform_admin.tools import (
    PLATFORM_ADMIN_TOOLS,
    get_ingestion_task_tool,
    get_system_setting_tool,
    list_knowledge_bases_tool,
)

__all__ = [
    "PLATFORM_ADMIN_TOOLS",
    "PlatformAdminModule",
    "get_ingestion_task_tool",
    "get_system_setting_tool",
    "list_knowledge_bases_tool",
]
