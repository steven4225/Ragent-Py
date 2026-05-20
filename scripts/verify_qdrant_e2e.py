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
DEFAULT_QDRANT_URL = "http://127.0.0.1:6333"
DEFAULT_QDRANT_COLLECTION = "ragent_python_chunks"


@dataclass(frozen=True, slots=True)
class VerificationConfig:
    web_base_url: str
    qdrant_url: str
    qdrant_collection: str
    tenant_id: str
    org_id: str
    user_id: str
    user_name: str
    role: str


def main() -> int:
    config = VerificationConfig(
        web_base_url=os.environ.get("RAGENT_WEB_BASE_URL", DEFAULT_WEB_BASE_URL).rstrip("/"),
        qdrant_url=os.environ.get("RAGENT_QDRANT_URL", DEFAULT_QDRANT_URL).rstrip("/"),
        qdrant_collection=os.environ.get("RAGENT_QDRANT_COLLECTION", DEFAULT_QDRANT_COLLECTION).strip()
        or DEFAULT_QDRANT_COLLECTION,
        tenant_id=os.environ.get("RAGENT_TENANT_ID", "tenant_demo"),
        org_id=os.environ.get("RAGENT_ORG_ID", "org_demo"),
        user_id=os.environ.get("RAGENT_USER_ID", "admin_demo"),
        user_name=os.environ.get("RAGENT_USER_NAME", "Demo Admin"),
        role=os.environ.get("RAGENT_USER_ROLE", "admin"),
    )

    timestamp = int(time.time() * 1000)
    trace_id = f"trace_qdrant_verify_{timestamp}"
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

    task = request_json(
        "POST",
        f"{config.web_base_url}/api/admin/ingestion/tasks",
        headers=headers,
        payload={
            "traceId": trace_id,
            "knowledgeBaseId": "kb_qdrant_verify",
            "documentId": "doc_qdrant_verify",
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
            "metadata": {},
        },
    )

    worker = request_json(
        "POST",
        f"{config.web_base_url}/api/admin/ingestion/worker",
        headers=headers,
        payload={"limit": 1, "taskIds": [task["taskId"]]},
    )

    task_after = request_json(
        "GET",
        f"{config.web_base_url}/api/admin/ingestion/tasks/{task['taskId']}",
        headers=headers,
    )
    assert_equal(task_after["status"], "succeeded", "ingestion task status")
    assert_equal(task_after["currentStage"], "completed", "ingestion task stage")
    assert_equal(task_after["indexWriteResult"]["source"], "python-qdrant-indexer", "indexing source")
    assert_in(task["taskId"], worker["succeededTaskIds"], "worker succeeded task ids")

    active_collection = (
        task_after.get("indexWriteResult", {})
        .get("metadata", {})
        .get("collection")
        or config.qdrant_collection
    )

    scroll = request_json(
        "POST",
        f"{config.qdrant_url}/collections/{active_collection}/points/scroll",
        payload={"limit": 20, "with_payload": True, "with_vector": False},
    )
    points = scroll.get("result", {}).get("points", [])
    point = next(
        (
            item
            for item in points
            if item.get("payload", {}).get("taskId") == task["taskId"]
        ),
        None,
    )
    if point is None:
        raise AssertionError("Qdrant collection did not contain the ingested task payload.")

    conversation = request_json(
        "POST",
        f"{config.web_base_url}/api/conversations",
        headers=headers,
        payload={"title": "Qdrant verification"},
    )
    chat = request_json(
        "POST",
        f"{config.web_base_url}/api/chat",
        headers=headers,
        payload={
            "conversationId": conversation["conversationId"],
            "message": "What does the atlas launch memo require before production unlock?",
        },
    )

    assistant_text = chat["assistantMessage"]["content"]
    retrieval_execution = chat["assistantMessage"]["metadata"]["retrievalExecution"]
    top_chunk = retrieval_execution["chunks"][0]
    top_chunk_metadata = top_chunk.get("metadata", {})

    if phrase not in assistant_text:
        raise AssertionError("Assistant response did not quote the newly indexed evidence.")
    assert_equal(top_chunk["source"], "python-qdrant-retrieval", "top retrieval chunk source")
    if phrase != top_chunk["content"]:
        raise AssertionError("Top retrieval chunk content does not match the ingested text.")
    assert_equal(top_chunk_metadata.get("retrievalMode"), "hybrid", "top retrieval mode")
    assert_equal(top_chunk_metadata.get("fusionStrategy"), "rrf", "top fusion strategy")
    assert_equal(top_chunk_metadata.get("rerankApplied"), True, "top rerank applied")
    assert_equal(top_chunk_metadata.get("rerankSource"), "heuristic-reranker", "top reranker source")
    assert_equal(top_chunk_metadata.get("denseSource"), "python-qdrant-retrieval", "top dense source")
    assert_equal(top_chunk_metadata.get("keywordSource"), "python-bm25-retrieval", "top keyword source")

    summary = {
        "taskId": task["taskId"],
        "traceId": chat["traceId"],
        "qdrantCollection": active_collection,
        "qdrantPointId": point["id"],
        "assistant": assistant_text,
        "retrievalSource": chat["assistantMessage"]["metadata"]["retrievalSource"],
        "topChunkSource": top_chunk["source"],
        "topChunkTitle": top_chunk["title"],
        "topChunkRetrievalMode": top_chunk_metadata.get("retrievalMode"),
        "topChunkFusionStrategy": top_chunk_metadata.get("fusionStrategy"),
        "topChunkRerankSource": top_chunk_metadata.get("rerankSource"),
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
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with {exc.code}: {body}") from exc


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
        print(f"[verify_qdrant_e2e] {exc}", file=sys.stderr)
        raise SystemExit(1)
