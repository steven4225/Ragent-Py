from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MCPActorModel(BaseModel):
    userId: str
    role: Literal["user", "admin"]
    tenantId: str | None = None
    orgId: str | None = None


class MCPExecutionContextModel(BaseModel):
    traceId: str
    actor: MCPActorModel


class MCPPlannedToolCallModel(BaseModel):
    toolCallId: str
    toolName: str
    args: dict[str, Any] = Field(default_factory=dict)


class MCPExecuteRequestModel(BaseModel):
    plannedCalls: list[MCPPlannedToolCallModel]
    context: MCPExecutionContextModel


class MCPToolResultModel(BaseModel):
    toolCallId: str
    toolName: str
    status: Literal["queued", "running", "succeeded", "failed"]
    args: dict[str, Any] = Field(default_factory=dict)
    output: Any | None = None


class MCPExecuteResponseModel(BaseModel):
    toolCalls: list[MCPToolResultModel]
    traceStages: list[dict[str, Any]] = Field(default_factory=list)
