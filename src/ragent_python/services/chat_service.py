from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterator
from uuid import uuid4

from ragent_python.contracts.internal_api import InternalChatRequestModel
from ragent_python.contracts.mcp import MCPActorModel, MCPExecuteRequestModel, MCPExecutionContextModel, MCPPlannedToolCallModel
from ragent_python.contracts.public_api import (
    ChatCompletedEvent,
    ChatPlanModel,
    ChatStartedEvent,
    ChatTurnResponseModel,
    ConversationModel,
    MessageCompletedEvent,
    MessageDeltaEvent,
    MessageModel,
    ThinkingCompletedEvent,
    ThinkingDeltaEvent,
    TraceStageModel,
    ToolCallEvent,
    ToolCallModel,
    utc_now_iso,
)
from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.services.mcp_service import execute_mcp_runtime
from ragent_python.services.retrieval_service import execute_retrieval


@dataclass(slots=True)
class ChatArtifacts:
    trace_id: str
    conversation: ConversationModel
    user_message: MessageModel
    assistant_message: MessageModel
    plan: ChatPlanModel
    tool_calls: list[ToolCallModel]
    trace_stages: list[TraceStageModel]


def _build_assistant_text(request: InternalChatRequestModel) -> str:
    return f"Python chat runtime is active. Received message: {request.message.strip()}"


def _plan_tool_call(request: InternalChatRequestModel, trace_id: str) -> MCPPlannedToolCallModel | None:
    lowered = request.message.lower()
    if "knowledge base" in lowered or "knowledge bases" in lowered or "kb" in lowered:
        return MCPPlannedToolCallModel(
            toolCallId=f"{trace_id}_tool_kb",
            toolName="list_knowledge_bases",
            args={"limit": 10},
        )
    if "setting" in lowered:
        return MCPPlannedToolCallModel(
            toolCallId=f"{trace_id}_tool_setting",
            toolName="get_system_setting",
            args={"key": "chat.defaultModel"},
        )
    return None


def _normalize_trace_stages(raw_trace_stages: list[dict[str, object]] | None) -> list[TraceStageModel]:
    normalized: list[TraceStageModel] = []
    if not raw_trace_stages:
        return normalized

    for raw_stage in raw_trace_stages:
        stage = raw_stage.get("stage")
        status = raw_stage.get("status")
        if not isinstance(stage, str) or not isinstance(status, str):
            continue
        if status not in {"pending", "running", "succeeded", "failed", "cancelled"}:
            continue

        metadata = raw_stage.get("metadata")
        normalized.append(
            TraceStageModel(
                stage=stage,
                status=status,
                metadata=metadata if isinstance(metadata, dict) else {},
                startedAt=raw_stage.get("startedAt") if isinstance(raw_stage.get("startedAt"), str) else None,
                finishedAt=raw_stage.get("finishedAt") if isinstance(raw_stage.get("finishedAt"), str) else None,
                durationMs=(
                    max(0, round(raw_stage["durationMs"]))
                    if isinstance(raw_stage.get("durationMs"), (int, float))
                    else None
                ),
            )
        )
    return normalized


def create_chat_artifacts(request: InternalChatRequestModel) -> ChatArtifacts:
    timestamp = utc_now_iso()
    trace_id = f"chat_{uuid4().hex[:12]}"
    conversation_id = request.conversationId or f"conv_{uuid4().hex[:12]}"
    user_message_id = f"msg_user_{uuid4().hex[:12]}"
    assistant_message_id = f"msg_assistant_{uuid4().hex[:12]}"

    conversation = ConversationModel(
        conversationId=conversation_id,
        userId=request.userId,
        tenantId=request.tenantId,
        orgId=request.orgId,
        title="Untitled conversation",
        createdAt=timestamp,
        updatedAt=timestamp,
    )
    user_message = MessageModel(
        messageId=user_message_id,
        conversationId=conversation_id,
        role="user",
        content=request.message.strip(),
        metadata={
            "tenantId": request.tenantId,
            "orgId": request.orgId,
            "userId": request.userId,
        },
        createdAt=timestamp,
    )
    retrieval_response = execute_retrieval(
        InternalRetrievalRequestModel(
            traceId=trace_id,
            query=request.message.strip(),
            conversationId=conversation_id,
            userId=request.userId,
            role=request.role,
            tenantId=request.tenantId,
            orgId=request.orgId,
        )
    )
    has_retrieval = len(retrieval_response.chunks) > 0
    planned_tool_call = _plan_tool_call(request, trace_id)
    tool_runtime = (
        execute_mcp_runtime(
            MCPExecuteRequestModel(
                plannedCalls=[planned_tool_call],
                context=MCPExecutionContextModel(
                    traceId=trace_id,
                    actor=MCPActorModel(
                        userId=request.userId,
                        role=request.role,
                        tenantId=request.tenantId,
                        orgId=request.orgId,
                    ),
                ),
            )
        )
        if planned_tool_call is not None
        else None
    )
    tool_calls = (
        [
            ToolCallModel(
                toolCallId=tool_call.toolCallId,
                toolName=tool_call.toolName,
                status=tool_call.status,
                args=tool_call.args,
                output=tool_call.output,
            )
            for tool_call in tool_runtime.toolCalls
        ]
        if tool_runtime is not None
        else []
    )
    completed_tool_calls = [tool_call for tool_call in tool_calls if tool_call.status in {"succeeded", "failed"}]
    used_tools = len(completed_tool_calls) > 0
    plan = ChatPlanModel(
        useRetrieval=has_retrieval,
        useTools=used_tools,
        retrievalReason=(
            "Local Python retrieval found matching evidence."
            if has_retrieval
            else "Python phase-1 chat path is active without matching retrieval evidence."
        ),
    )
    assistant_text = _build_assistant_text(request)
    if has_retrieval:
        top_chunk = retrieval_response.chunks[0]
        assistant_text = (
            f"{assistant_text} Top evidence: {top_chunk.title} - {top_chunk.content}"
        )
    if completed_tool_calls:
        last_tool = completed_tool_calls[-1]
        if last_tool.status == "succeeded" and isinstance(last_tool.output, dict):
            summary = last_tool.output.get("summary")
            if isinstance(summary, str) and summary:
                assistant_text = f"{assistant_text} Tool summary: {summary}"
    trace_stages = list(retrieval_response.traceStages)
    if planned_tool_call is not None:
        trace_stages.append(
            TraceStageModel(
                stage="tool.plan",
                status="succeeded",
                metadata={
                    "toolCallId": planned_tool_call.toolCallId,
                    "toolName": planned_tool_call.toolName,
                    "args": planned_tool_call.args,
                },
                startedAt=timestamp,
                finishedAt=timestamp,
                durationMs=0,
            )
        )
    trace_stages.extend(_normalize_trace_stages(tool_runtime.traceStages if tool_runtime is not None else None))
    trace_stages.append(
        TraceStageModel(
            stage="generation.completed",
            status="succeeded",
            metadata={
                "provider": "python-backend",
                "mode": "phase1-local-retrieval",
                "model": "internal-phase1",
                "outputChars": len(assistant_text),
            },
            startedAt=timestamp,
            finishedAt=timestamp,
            durationMs=0,
        )
    )
    assistant_message = MessageModel(
        messageId=assistant_message_id,
        conversationId=conversation_id,
        role="assistant",
        content=assistant_text,
        metadata={
            "traceId": trace_id,
            "source": "python-backend",
            "toolCalls": [tool_call.model_dump(mode="json") for tool_call in completed_tool_calls],
            "retrievalSource": retrieval_response.source if has_retrieval else None,
            "context": {
                "evidenceCount": len(retrieval_response.chunks),
            },
            "retrievalExecution": retrieval_response.model_dump(mode="json"),
            "generation": {
                "provider": "python-backend",
                "mode": "phase1-local-retrieval",
                "model": "internal-phase1",
            },
            "tenantId": request.tenantId,
            "orgId": request.orgId,
            "userId": request.userId,
        },
        createdAt=timestamp,
    )

    return ChatArtifacts(
        trace_id=trace_id,
        conversation=conversation,
        user_message=user_message,
        assistant_message=assistant_message,
        plan=plan,
        tool_calls=tool_calls,
        trace_stages=trace_stages,
    )


def build_chat_turn_response(request: InternalChatRequestModel) -> ChatTurnResponseModel:
    artifacts = create_chat_artifacts(request)
    return ChatTurnResponseModel(
        traceId=artifacts.trace_id,
        conversation=artifacts.conversation,
        userMessage=artifacts.user_message,
        assistantMessage=artifacts.assistant_message,
        plan=artifacts.plan,
        traceStages=artifacts.trace_stages,
    )


def _chunk_text(text: str, max_chunk_size: int = 24) -> Iterator[str]:
    for start in range(0, len(text), max_chunk_size):
        yield text[start : start + max_chunk_size]


def iter_chat_stream_events(request: InternalChatRequestModel) -> Iterator[str]:
    artifacts = create_chat_artifacts(request)

    yield _to_ndjson(
        ChatStartedEvent(
            traceId=artifacts.trace_id,
            conversation=artifacts.conversation,
            userMessage=artifacts.user_message,
        )
    )
    yield _to_ndjson(
        ThinkingDeltaEvent(
            traceId=artifacts.trace_id,
            delta="Preparing Python phase-1 response.",
        )
    )
    yield _to_ndjson(
        ThinkingCompletedEvent(
            traceId=artifacts.trace_id,
        )
    )
    for tool_call in artifacts.tool_calls:
        yield _to_ndjson(
            ToolCallEvent(
                traceId=artifacts.trace_id,
                toolCall=tool_call,
            )
        )
    for chunk in _chunk_text(artifacts.assistant_message.content):
        yield _to_ndjson(
            MessageDeltaEvent(
                traceId=artifacts.trace_id,
                delta=chunk,
            )
        )
    yield _to_ndjson(
        MessageCompletedEvent(
            traceId=artifacts.trace_id,
            assistantMessage=artifacts.assistant_message,
        )
    )
    yield _to_ndjson(
        ChatCompletedEvent(
            traceId=artifacts.trace_id,
            plan=artifacts.plan,
            traceStages=artifacts.trace_stages,
        )
    )


def _to_ndjson(model) -> str:
    return json.dumps(model.model_dump(mode="json"), ensure_ascii=False) + "\n"
