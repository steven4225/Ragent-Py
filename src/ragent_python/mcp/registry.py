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


def _list_knowledge_bases(_: dict[str, Any], __: MCPExecutionContextModel) -> dict[str, Any]:
    items = [
        {
            "knowledgeBaseId": "kb_policy",
            "name": "Policy Base",
            "documentCount": 12,
        },
        {
            "knowledgeBaseId": "kb_ops",
            "name": "Ops Handbook",
            "documentCount": 8,
        },
        {
            "knowledgeBaseId": "kb_product",
            "name": "Product Notes",
            "documentCount": 16,
        },
    ]
    return {
        "summary": f"Listed {len(items)} knowledge bases.",
        "data": {
            "total": len(items),
            "items": items,
        },
    }


def _get_system_setting(args: dict[str, Any], context: MCPExecutionContextModel) -> dict[str, Any]:
    settings = {
        "chat.defaultModel": {
            "value": "gpt-5.4-mini",
            "description": "Default chat model in the control plane.",
        },
        "retrieval.adapter": {
            "value": "python-local-retrieval",
            "description": "Current retrieval adapter id.",
        },
    }
    key = str(args.get("key", "")).strip()
    item = settings.get(key)
    if not item:
        raise ValueError(f"System setting '{key}' not found for actor {context.actor.userId}.")
    return {
        "summary": f"Read system setting '{key}'.",
        "data": {
            "key": key,
            "value": item["value"],
            "description": item["description"],
        },
    }


TOOLS: tuple[MCPToolDefinition, ...] = (
    MCPToolDefinition(
        name="list_knowledge_bases",
        description="List available knowledge bases.",
        keywords=("knowledge base", "knowledge bases", "kb list", "kb"),
        requires_admin=False,
        execute=_list_knowledge_bases,
    ),
    MCPToolDefinition(
        name="get_system_setting",
        description="Read one system setting by key.",
        keywords=("setting", "settings", "system setting"),
        requires_admin=True,
        execute=_get_system_setting,
    ),
)


def list_mcp_tools() -> list[MCPToolDefinition]:
    return list(TOOLS)


def get_mcp_tool(name: str) -> MCPToolDefinition | None:
    for tool in TOOLS:
        if tool.name == name:
            return tool
    return None
