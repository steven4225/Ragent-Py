from __future__ import annotations

from typing import Any

from ragent_python.contracts.mcp import (
    MCPExecuteRequestModel,
    MCPExecuteResponseModel,
    MCPToolResultModel,
)
from ragent_python.mcp.registry import get_mcp_tool


def execute_mcp_runtime(request: MCPExecuteRequestModel) -> MCPExecuteResponseModel:
    tool_calls: list[MCPToolResultModel] = []
    trace_stages: list[dict[str, Any]] = []

    for planned_call in request.plannedCalls:
        tool_calls.append(
            MCPToolResultModel(
                toolCallId=planned_call.toolCallId,
                toolName=planned_call.toolName,
                status="queued",
                args=planned_call.args,
            )
        )
        tool = get_mcp_tool(planned_call.toolName)
        if tool is None:
            tool_calls.append(
                MCPToolResultModel(
                    toolCallId=planned_call.toolCallId,
                    toolName=planned_call.toolName,
                    status="failed",
                    args=planned_call.args,
                    output={
                        "error": f"Tool '{planned_call.toolName}' is not registered.",
                    },
                )
            )
            trace_stages.append(
                {
                    "stage": "tool.runtime.failed",
                    "status": "failed",
                    "metadata": {
                        "toolCallId": planned_call.toolCallId,
                        "toolName": planned_call.toolName,
                        "reason": "tool-not-registered",
                    },
                }
            )
            continue

        if tool.requires_admin and request.context.actor.role != "admin":
            tool_calls.append(
                MCPToolResultModel(
                    toolCallId=planned_call.toolCallId,
                    toolName=planned_call.toolName,
                    status="failed",
                    args=planned_call.args,
                    output={
                        "error": "Tool requires admin scope.",
                    },
                )
            )
            trace_stages.append(
                {
                    "stage": "tool.runtime.failed",
                    "status": "failed",
                    "metadata": {
                        "toolCallId": planned_call.toolCallId,
                        "toolName": planned_call.toolName,
                        "reason": "guard-denied",
                    },
                }
            )
            continue

        tool_calls.append(
            MCPToolResultModel(
                toolCallId=planned_call.toolCallId,
                toolName=planned_call.toolName,
                status="running",
                args=planned_call.args,
            )
        )
        trace_stages.append(
            {
                "stage": "tool.runtime.started",
                "status": "running",
                "metadata": {
                    "toolCallId": planned_call.toolCallId,
                    "toolName": planned_call.toolName,
                    "args": planned_call.args,
                },
            }
        )

        try:
            result = tool.execute(planned_call.args, request.context)
            tool_calls.append(
                MCPToolResultModel(
                    toolCallId=planned_call.toolCallId,
                    toolName=planned_call.toolName,
                    status="succeeded",
                    args=planned_call.args,
                    output=result,
                )
            )
            trace_stages.append(
                {
                    "stage": "tool.runtime.completed",
                    "status": "succeeded",
                    "metadata": {
                        "toolCallId": planned_call.toolCallId,
                        "toolName": planned_call.toolName,
                        "outputSummary": result.get("summary"),
                    },
                }
            )
        except Exception as error:  # noqa: BLE001
            tool_calls.append(
                MCPToolResultModel(
                    toolCallId=planned_call.toolCallId,
                    toolName=planned_call.toolName,
                    status="failed",
                    args=planned_call.args,
                    output={
                        "error": str(error),
                    },
                )
            )
            trace_stages.append(
                {
                    "stage": "tool.runtime.failed",
                    "status": "failed",
                    "metadata": {
                        "toolCallId": planned_call.toolCallId,
                        "toolName": planned_call.toolName,
                        "error": str(error),
                    },
                }
            )

    return MCPExecuteResponseModel(
        toolCalls=tool_calls,
        traceStages=trace_stages,
    )
