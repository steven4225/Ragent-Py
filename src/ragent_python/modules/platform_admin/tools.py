"""Platform-admin tool implementations.

These are the three tools that previously lived in `mcp/registry.py` as a
hard-coded `TOOLS` tuple. They keep the same names, descriptions, keywords,
admin-guard flags, and runtime behaviour so the existing TS/Python contract
(and the `test_mcp_service.py` suite) is unaffected.
"""

from __future__ import annotations

from typing import Any

from ragent_python.contracts.mcp import MCPExecutionContextModel
from ragent_python.mcp.platform_state import get_scoped_setting
from ragent_python.mcp.registry import MCPToolDefinition
from ragent_python.services.ingestion_service import get_ingestion_task


def _list_knowledge_bases(
    _: dict[str, Any], __: MCPExecutionContextModel
) -> dict[str, Any]:
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


def _get_system_setting(
    args: dict[str, Any], context: MCPExecutionContextModel
) -> dict[str, Any]:
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


def _get_ingestion_task(
    args: dict[str, Any], context: MCPExecutionContextModel
) -> dict[str, Any]:
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


list_knowledge_bases_tool = MCPToolDefinition(
    name="list_knowledge_bases",
    description="List available knowledge bases.",
    keywords=("knowledge base", "knowledge bases", "kb list", "kb"),
    requires_admin=False,
    execute=_list_knowledge_bases,
)

get_system_setting_tool = MCPToolDefinition(
    name="get_system_setting",
    description="Read one system setting by key.",
    keywords=("setting", "settings", "system setting"),
    requires_admin=True,
    execute=_get_system_setting,
)

get_ingestion_task_tool = MCPToolDefinition(
    name="get_ingestion_task",
    description="Read one ingestion task by task id.",
    keywords=("ingestion task", "task status", "ingestion status"),
    requires_admin=True,
    execute=_get_ingestion_task,
)


PLATFORM_ADMIN_TOOLS: tuple[MCPToolDefinition, ...] = (
    list_knowledge_bases_tool,
    get_system_setting_tool,
    get_ingestion_task_tool,
)
