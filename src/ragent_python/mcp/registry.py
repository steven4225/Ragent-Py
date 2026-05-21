from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ragent_python.contracts.mcp import MCPExecutionContextModel
from ragent_python.mcp.platform_state import get_scoped_setting
from ragent_python.services.ingestion_service import get_ingestion_task


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
    item = get_scoped_setting(key, context.actor.tenantId, context.actor.orgId) or settings.get(key)
    if not item:
        raise ValueError(f"System setting '{key}' not found for actor {context.actor.userId}.")
    return {
        "summary": f"Read system setting '{key}'.",
        "data": {
            "key": key,
            "value": item.get("value"),
            "description": item.get("description"),
        },
    }


def _get_ingestion_task(args: dict[str, Any], context: MCPExecutionContextModel) -> dict[str, Any]:
    task_id = str(args.get("taskId", "")).strip()
    if not task_id:
        raise ValueError("`taskId` is required.")

    task = get_ingestion_task(task_id)
    if task is None:
        raise ValueError(f"Ingestion task '{task_id}' not found.")
    if context.actor.tenantId is not None and task.tenantId != context.actor.tenantId:
        raise ValueError(f"Ingestion task '{task_id}' not found.")
    if context.actor.orgId is not None and task.orgId != context.actor.orgId:
        raise ValueError(f"Ingestion task '{task_id}' not found.")

    return {
        "summary": f"Ingestion task '{task_id}' is currently {task.status}.",
        "data": {
            "taskId": task.taskId,
            "status": task.status,
            "currentStage": task.currentStage,
            "traceId": task.traceId,
            "knowledgeBaseId": task.knowledgeBaseId,
            "documentId": task.documentId,
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
    MCPToolDefinition(
        name="get_ingestion_task",
        description="Read one ingestion task by task id.",
        keywords=("ingestion task", "task status", "ingestion status"),
        requires_admin=True,
        execute=_get_ingestion_task,
    ),
)


def list_mcp_tools() -> list[MCPToolDefinition]:
    return list(TOOLS)


def get_mcp_tool(name: str) -> MCPToolDefinition | None:
    for tool in TOOLS:
        if tool.name == name:
            return tool
    return None
