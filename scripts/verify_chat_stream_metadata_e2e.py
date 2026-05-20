from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


DEFAULT_WEB_BASE_URL = "http://127.0.0.1:3000"
DEFAULT_QDRANT_COLLECTION = "ragent_python_chunks"


@dataclass(frozen=True, slots=True)
class VerificationConfig:
    web_base_url: str
    qdrant_collection: str
    tenant_id: str
    org_id: str
    user_id: str
    user_name: str
    role: str


def main() -> int:
    config = VerificationConfig(
        web_base_url=os.environ.get("RAGENT_WEB_BASE_URL", DEFAULT_WEB_BASE_URL).rstrip("/"),
        qdrant_collection=os.environ.get("RAGENT_QDRANT_COLLECTION", DEFAULT_QDRANT_COLLECTION).strip()
        or DEFAULT_QDRANT_COLLECTION,
        tenant_id=os.environ.get("RAGENT_TENANT_ID", "tenant_demo"),
        org_id=os.environ.get("RAGENT_ORG_ID", "org_demo"),
        user_id=os.environ.get("RAGENT_USER_ID", "admin_demo"),
        user_name=os.environ.get("RAGENT_USER_NAME", "Demo Admin"),
        role=os.environ.get("RAGENT_USER_ROLE", "admin"),
    )

    timestamp = int(time.time() * 1000)
    phrase = (
        "Atlas launch memo says rollback approval requires two green canary "
        "windows before production unlock."
    )
    data_uri = "data:text/plain;base64," + base64.b64encode(phrase.encode("utf-8")).decode("ascii")
    trace_id = f"trace_stream_metadata_{timestamp}"

    headers = {
        "x-ragent-user-id": config.user_id,
        "x-ragent-user-name": config.user_name,
        "x-ragent-role": config.role,
        "x-ragent-tenant-id": config.tenant_id,
        "x-ragent-org-id": config.org_id,
    }

    task = request_json(
        "POST",
        f"{config.web_base_url}/api/admin/ingestion/tasks",
        headers=headers,
        payload={
            "traceId": trace_id,
            "knowledgeBaseId": "kb_stream_metadata_verify",
            "documentId": "doc_stream_metadata_verify",
            "requestedBy": config.user_id,
            "tenantId": config.tenant_id,
            "orgId": config.org_id,
            "source": {
                "sourceType": "upload",
                "uri": data_uri,
                "filename": "atlas-launch.txt",
                "mimeType": "text/plain",
                "sizeBytes": len(phrase.encode("utf-8")),
            },
            "executionPlan": {
                "parser": {"parserType": "mock-parser", "mode": "mock"},
                "chunking": {"strategy": "paragraph", "targetSize": 1200, "overlap": 120},
                "embedding": {"enabled": True, "model": "mock-embed", "adapter": "local"},
                "indexing": {
                    "enabled": True,
                    "indexName": config.qdrant_collection,
                    "storeType": "qdrant",
                },
            },
            "metadata": {"initiatedFrom": "verify_chat_stream_metadata_e2e"},
        },
    )

    worker = request_json(
        "POST",
        f"{config.web_base_url}/api/admin/ingestion/worker",
        headers=headers,
        payload={"limit": 1, "taskIds": [task["taskId"]]},
    )
    assert_in(task["taskId"], worker["succeededTaskIds"], "worker succeeded task ids")

    conversation = request_json(
        "POST",
        f"{config.web_base_url}/api/conversations",
        headers=headers,
        payload={"title": "Stream metadata verification"},
    )

    message = "Please check setting chat.defaultModel and explain what the atlas launch memo requires before production unlock."
    events = request_ndjson(
        "POST",
        f"{config.web_base_url}/api/chat/stream",
        headers=headers,
        payload={
            "conversationId": conversation["conversationId"],
            "message": message,
        },
    )

    started = next((event for event in events if event.get("type") == "chat.started"), None)
    thinking_delta = next((event for event in events if event.get("type") == "thinking.delta"), None)
    thinking_completed = next((event for event in events if event.get("type") == "thinking.completed"), None)
    message_completed = next((event for event in events if event.get("type") == "message.completed"), None)
    chat_completed = next((event for event in events if event.get("type") == "chat.completed"), None)
    tool_events = [
        event for event in events
        if event.get("type") == "tool.call" and event.get("toolCall", {}).get("toolName") == "get_system_setting"
    ]

    if not started or not thinking_delta or not thinking_completed or not message_completed or not chat_completed:
        raise AssertionError("Stream event chain is incomplete.")

    tool_statuses = [event["toolCall"]["status"] for event in tool_events]
    if tool_statuses != ["queued", "running", "succeeded"]:
        raise AssertionError(f"Unexpected tool.call status chain: {tool_statuses!r}")

    assistant_message = message_completed["assistantMessage"]
    assistant_text = str(assistant_message.get("content", ""))
    metadata = assistant_message.get("metadata", {})
    retrieval_execution = metadata.get("retrievalExecution", {})
    chunks = retrieval_execution.get("chunks", [])
    top_chunk = chunks[0] if chunks else None
    tool_calls = metadata.get("toolCalls", [])

    if phrase not in assistant_text:
        raise AssertionError("Assistant response did not quote the ingested evidence in stream mode.")
    assert_equal(metadata.get("retrievalSource"), "python-composite-retrieval", "stream retrieval source")
    assert_equal(metadata.get("context", {}).get("evidenceCount", 0) > 0, True, "stream evidence count positive")
    assert_equal(len(chunks) > 0, True, "stream retrieval chunks present")
    assert_equal(len(tool_calls) > 0, True, "stream assistant metadata toolCalls present")
    assert_equal(tool_calls[-1].get("toolName"), "get_system_setting", "stream final tool name")
    assert_equal(tool_calls[-1].get("status"), "succeeded", "stream final tool status")
    assert_equal(top_chunk.get("source") if top_chunk else None, "python-qdrant-retrieval", "stream top chunk source")
    assert_equal(top_chunk.get("metadata", {}).get("retrievalMode") if top_chunk else None, "hybrid", "stream top retrieval mode")
    assert_equal(top_chunk.get("metadata", {}).get("keywordSource") if top_chunk else None, "python-bm25-retrieval", "stream keyword source")

    summary = {
        "taskId": task["taskId"],
        "traceId": started["traceId"],
        "conversationId": conversation["conversationId"],
        "eventTypes": [event.get("type") for event in events],
        "toolStatuses": tool_statuses,
        "assistant": assistant_text,
        "retrievalSource": metadata.get("retrievalSource"),
        "evidenceCount": metadata.get("context", {}).get("evidenceCount"),
        "toolCallsCount": len(tool_calls),
        "topChunkSource": top_chunk.get("source") if top_chunk else None,
        "topChunkTitle": top_chunk.get("title") if top_chunk else None,
        "topChunkRetrievalMode": top_chunk.get("metadata", {}).get("retrievalMode") if top_chunk else None,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    payload: dict | None = None,
) -> dict:
    encoded = None
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    if payload is not None:
        encoded = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=encoded, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with {exc.code}: {body}") from exc


def request_ndjson(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    payload: dict | None = None,
) -> list[dict]:
    encoded = None
    request_headers = {"Accept": "application/x-ndjson"}
    if headers:
        request_headers.update(headers)
    if payload is not None:
        encoded = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=encoded, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            text = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with {exc.code}: {body}") from exc

    events: list[dict] = []
    for line in text.splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def assert_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label} mismatch: expected={expected!r} actual={actual!r}")


def assert_in(value: object, collection: list[object], label: str) -> None:
    if value not in collection:
        raise AssertionError(f"{label} missing expected value: {value!r}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - script path
        print(f"[verify_chat_stream_metadata_e2e] {exc}", file=sys.stderr)
        raise SystemExit(1)
