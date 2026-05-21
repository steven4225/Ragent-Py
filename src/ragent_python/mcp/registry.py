"""MCP tool registry — thin facade over the platform `ToolPackRegistry`.

Historically this module hard-coded the platform-admin tools. After Step B,
each `MCPToolDefinition` is owned by a `core.modules.Module` and contributed
via a `ToolPack`; this file only exposes:

- `MCPToolDefinition` / `ToolExecutor` — the shared tool dataclass and the
  executor callable type (used by tool implementations across modules and by
  `infra/registries/tool_pack.py`'s typing).
- `list_mcp_tools()` / `get_mcp_tool()` — back-compat lookup helpers that
  forward to the shared `ToolPackRegistry`. Call sites (e.g.
  `services/mcp_service.py`) do not need to know that tools now flow through
  modules.

A lazy `_ensure_default_modules_bootstrapped()` is invoked at the top of each
lookup so the platform-admin module is registered exactly once, idempotently,
even when callers reach the MCP runtime directly without going through
`main.create_app()` (e.g. service-level unit tests).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ragent_python.contracts.mcp import MCPExecutionContextModel


ToolExecutor = Callable[[dict[str, Any], MCPExecutionContextModel], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class MCPToolDefinition:
    name: str
    description: str
    keywords: tuple[str, ...]
    requires_admin: bool
    execute: ToolExecutor


def _ensure_default_modules_bootstrapped() -> None:
    """Register and bootstrap the default platform modules if not already.

    Delegates to the canonical `bootstrap_default_modules()` in
    `ragent_python.modules`, which is idempotent and survives the
    `ModuleRegistry.clear()` cascade (since clearing the global registry
    also resets the sub-registries, the next call here will simply
    re-register and re-bootstrap).

    The import is deferred to avoid a top-level cycle:
    `modules/platform_admin/tools.py` imports `MCPToolDefinition` from
    this module.
    """

    from ragent_python.modules import bootstrap_default_modules

    bootstrap_default_modules()


def list_mcp_tools() -> list[MCPToolDefinition]:
    _ensure_default_modules_bootstrapped()
    from ragent_python.infra.registries.tool_pack import default_tool_pack_registry

    return default_tool_pack_registry.list_tools()


def get_mcp_tool(name: str) -> MCPToolDefinition | None:
    _ensure_default_modules_bootstrapped()
    from ragent_python.infra.registries.tool_pack import default_tool_pack_registry

    return default_tool_pack_registry.get_tool(name)
