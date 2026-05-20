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
REQUIRED_CHAT_STAGES = {
    "chat",
    "retrieval.plan",
    "retrieval.execute",
    "tool.plan",
    "tool.runtime.started",
    "tool.runtime.completed",
    "generation.completed",
}


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
    headers = {
        "x-ragent-user-id": config.user_id,
        "x-ragent-user-name": config.user_name,
        "x-ragent-role": config.role,
        "x-ragent-tenant-id": config.tenant_id,
        "x-ragent-org-id": config.org_id,
    }
    prompt = "Please check setting chat.defaultModel and explain what the atlas launch memo requires before production unlock."

    task = request_json(
        "POST",
        f"{config.web_base_url}/api/admin/ingestion/tasks",
        headers=headers,
        payload={
            "traceId": f"trace_chat_trace_{timestamp}",
            "knowledgeBaseId": "kb_chat_trace_verify",
            "documentId": f"doc_chat_trace_verify_{timestamp}",
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
            "metadata": {"initiatedFrom": "verify_chat_trace_e2e"},
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
        payload={"title": "Trace verification"},
    )

    chat_response = request_json(
        "POST",
        f"{config.web_base_url}/api/chat",
        headers=headers,
        payload={
            "conversationId": conversation["conversationId"],
            "message": prompt,
        },
    )
    chat_trace = trace_records_for(config.web_base_url, headers, chat_response["traceId"])
    assert_trace_stages(chat_trace, REQUIRED_CHAT_STAGES, "chat")

    stream_events = request_ndjson(
        "POST",
        f"{config.web_base_url}/api/chat/stream",
        headers=headers,
        payload={
            "conversationId": conversation["conversationId"],
            "message": prompt,
        },
    )
    stream_started = next((event for event in stream_events if event.get("type") == "chat.started"), None)
    stream_completed = next((event for event in stream_events if event.get("type") == "chat.completed"), None)
    if not stream_started or not stream_completed:
        raise AssertionError("stream trace verification did not receive started/completed events")
    stream_trace = trace_records_for(config.web_base_url, headers, stream_started["traceId"])
    assert_trace_stages(stream_trace, REQUIRED_CHAT_STAGES, "chat.stream")

    summary = {
        "taskId": task["taskId"],
        "conversationId": conversation["conversationId"],
        "chatTraceId": chat_response["traceId"],
        "chatStages": sorted({item["stage"] for item in chat_trace}),
        "streamTraceId": stream_started["traceId"],
        "streamStages": sorted({item["stage"] for item in stream_trace}),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def trace_records_for(web_base_url: str, headers: dict[str, str], trace_id: str) -> list[dict]:
    trace_response = request_json("GET", f"{web_base_url}/api/trace", headers=headers)
    records = trace_response.get("records") or trace_response.get("items") or []
    return [item for item in records if item.get("traceId") == trace_id]


def assert_trace_stages(records: list[dict], expected_stages: set[str], label: str) -> None:
    stages = {str(item.get("stage")) for item in records}
    missing = sorted(expected_stages - stages)
    if missing:
        raise AssertionError(f"{label} trace missing stages: {missing!r}; saw={sorted(stages)!r}")


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


def assert_in(value: object, collection: list[object], label: str) -> None:
    if value not in collection:
        raise AssertionError(f"{label} missing expected value: {value!r}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - script path
        print(f"[verify_chat_trace_e2e] {exc}", file=sys.stderr)
        raise SystemExit(1)
