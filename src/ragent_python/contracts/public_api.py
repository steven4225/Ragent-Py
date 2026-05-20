from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationModel(BaseModel):
    conversationId: str
    userId: str
    orgId: str | None = None
    tenantId: str | None = None
    title: str
    summary: str = ""
    lastSummarizedMessageId: str = ""
    createdAt: str = Field(default_factory=utc_now_iso)
    updatedAt: str = Field(default_factory=utc_now_iso)


class MessageModel(BaseModel):
    messageId: str
    conversationId: str
    role: Literal["user", "assistant"]
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    createdAt: str = Field(default_factory=utc_now_iso)


class ToolCallModel(BaseModel):
    toolCallId: str
    toolName: str
    status: Literal["queued", "running", "succeeded", "failed"]
    args: dict[str, Any] = Field(default_factory=dict)
    output: Any | None = None


class ChatPlanModel(BaseModel):
    useRetrieval: bool
    useTools: bool
    retrievalReason: str


class TraceStageModel(BaseModel):
    stage: str
    status: Literal["pending", "running", "succeeded", "failed", "cancelled"]
    metadata: dict[str, Any] = Field(default_factory=dict)
    startedAt: str | None = None
    finishedAt: str | None = None
    durationMs: int | None = None


class RetrievalChunkModel(BaseModel):
    chunkId: str
    knowledgeBaseId: str
    documentId: str
    title: str
    content: str
    score: float
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalTimingModel(BaseModel):
    totalMs: float


class RetrievalResponseModel(BaseModel):
    traceId: str
    chunks: list[RetrievalChunkModel]
    timing: RetrievalTimingModel
    source: str
    traceStages: list[TraceStageModel] = Field(default_factory=list)


class ChatTurnResponseModel(BaseModel):
    traceId: str
    conversation: ConversationModel
    userMessage: MessageModel
    assistantMessage: MessageModel
    plan: ChatPlanModel
    traceStages: list[TraceStageModel] = Field(default_factory=list)


class ChatStartedEvent(BaseModel):
    type: Literal["chat.started"] = "chat.started"
    traceId: str
    conversation: ConversationModel
    userMessage: MessageModel


class ToolCallEvent(BaseModel):
    type: Literal["tool.call"] = "tool.call"
    traceId: str
    toolCall: ToolCallModel


class MessageDeltaEvent(BaseModel):
    type: Literal["message.delta"] = "message.delta"
    traceId: str
    delta: str


class MessageCompletedEvent(BaseModel):
    type: Literal["message.completed"] = "message.completed"
    traceId: str
    assistantMessage: MessageModel


class ChatCompletedEvent(BaseModel):
    type: Literal["chat.completed"] = "chat.completed"
    traceId: str
    plan: ChatPlanModel
    traceStages: list[TraceStageModel] = Field(default_factory=list)


class ThinkingDeltaEvent(BaseModel):
    type: Literal["thinking.delta"] = "thinking.delta"
    traceId: str
    delta: str


class ThinkingCompletedEvent(BaseModel):
    type: Literal["thinking.completed"] = "thinking.completed"
    traceId: str


class ChatErrorEvent(BaseModel):
    type: Literal["chat.error"] = "chat.error"
    traceId: str
    code: str
    message: str
