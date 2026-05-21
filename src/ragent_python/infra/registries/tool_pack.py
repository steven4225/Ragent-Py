"""Tool pack registry.

A `ToolPack` is a named group of MCP tools contributed by one module. The
existing platform-admin tools in `mcp/registry.py` will be migrated to a pack
named ``"platform_admin"`` in Step B; until then, this registry simply exists
as the seam.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ragent_python.mcp.registry import MCPToolDefinition


@dataclass(frozen=True, slots=True)
class ToolPack:
    name: str
    module: str
    tools: tuple["MCPToolDefinition", ...]
    description: str = ""


class ToolPackRegistry:
    def __init__(self) -> None:
        self._packs: dict[str, ToolPack] = {}

    def register(self, pack: ToolPack) -> None:
        if pack.name in self._packs:
            raise ValueError(f"Tool pack '{pack.name}' already registered.")
        self._packs[pack.name] = pack

    def get_pack(self, name: str) -> ToolPack | None:
        return self._packs.get(name)

    def list_packs(self) -> list[ToolPack]:
        return list(self._packs.values())

    def list_tools(self, *, packs: list[str] | None = None) -> list["MCPToolDefinition"]:
        if packs is None:
            return [tool for pack in self._packs.values() for tool in pack.tools]
        return [
            tool
            for name in packs
            if (pack := self._packs.get(name)) is not None
            for tool in pack.tools
        ]

    def get_tool(self, tool_name: str) -> "MCPToolDefinition | None":
        for pack in self._packs.values():
            for tool in pack.tools:
                if tool.name == tool_name:
                    return tool
        return None

    def clear(self) -> None:
        self._packs.clear()


default_tool_pack_registry = ToolPackRegistry()
