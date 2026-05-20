from __future__ import annotations

import json
import math
import os
import threading
import unittest
import uuid
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from ragent_python.contracts.ingestion import (
    IngestionExecutionPlanModel,
    IngestionSourceModel,
    IngestionTaskCreateRequestModel,
)
from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.retrieval.providers import clear_retrieval_provider_cache, extract_terms
from ragent_python.retrieval.bm25_provider import BM25RetrievalProvider
from ragent_python.retrieval.qdrant_provider import QdrantIndexProvider, QdrantIndexRecord
from ragent_python.services.ingestion_service import create_ingestion_task
from ragent_python.services.retrieval_service import execute_retrieval
from ragent_python.storage.ingestion_repository import ingestion_repository
from ragent_python.worker.ingestion_worker import run_ingestion_worker


class _FakeQdrantState:
    def __init__(self) -> None:
        self.collections: dict[str, dict[str, Any]] = {}

    def ensure_collection(self, name: str, vector_size: int) -> None:
        self.collections.setdefault(name, {"vector_size": vector_size, "points": {}})

    def upsert_points(self, collection: str, points: list[dict[str, Any]]) -> None:
        bucket = self.collections.setdefault(collection, {"vector_size": 8, "points": {}})
        for point in points:
            bucket["points"][str(point["id"])] = point

    def search(self, collection: str, vector: list[float], limit: int, payload_filter: dict[str, Any] | None) -> list[dict[str, Any]]:
        bucket = self.collections.get(collection, {"points": {}})
        hits: list[dict[str, Any]] = []
        for point in bucket["points"].values():
            payload = point.get("payload", {})
            if not _match_filter(payload, payload_filter):
                continue
            score = _cosine_similarity(vector, list(point.get("vector", [])))
            hits.append({"id": point["id"], "score": score, "payload": payload})
        hits.sort(key=lambda item: item["score"], reverse=True)
        return hits[:limit]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _match_filter(payload: dict[str, Any], payload_filter: dict[str, Any] | None) -> bool:
    if not payload_filter:
        return True
    must = payload_filter.get("must", [])
    for clause in must:
        key = clause.get("key")
        expected = clause.get("match", {}).get("value")
        if payload.get(key) != expected:
            return False
    return True


class _FakeQdrantHandler(BaseHTTPRequestHandler):
    state = _FakeQdrantState()

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/collections":
            return self._write_json(200, {"status": "ok", "result": {"collections": []}})
        if self.path.startswith("/collections/"):
            collection = self.path.split("/", 2)[2]
            stored = self.state.collections.get(collection)
            if stored is None:
                return self._write_json(404, {"status": "error", "result": None})
            return self._write_json(
                200,
                {
                    "status": "ok",
                    "result": {
                        "config": {
                            "params": {
                                "vectors": {
                                    "size": stored["vector_size"],
                                    "distance": "Cosine",
                                }
                            }
                        }
                    },
                },
            )
        return self._write_json(404, {"status": "error"})

    def do_PUT(self) -> None:  # noqa: N802
        body = self._read_json()
        if self.path.startswith("/collections/") and self.path.endswith("/points"):
            collection = self.path.split("/")[2]
            self.state.upsert_points(collection, body.get("points", []))
            return self._write_json(200, {"status": "ok", "result": {"status": "acknowledged"}})
        if self.path.startswith("/collections/"):
            collection = self.path.split("/", 2)[2]
            vectors = body.get("vectors", {})
            self.state.ensure_collection(collection, int(vectors.get("size", 8)))
            return self._write_json(200, {"status": "ok", "result": True})
        return self._write_json(404, {"status": "error"})

    def do_POST(self) -> None:  # noqa: N802
        body = self._read_json()
        if self.path.startswith("/collections/") and self.path.endswith("/points/search"):
            collection = self.path.split("/")[2]
            hits = self.state.search(
                collection=collection,
                vector=body.get("vector", []),
                limit=int(body.get("limit", 10)),
                payload_filter=body.get("filter"),
            )
            return self._write_json(200, {"status": "ok", "result": hits})
        return self._write_json(404, {"status": "error"})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        return json.loads(raw.decode("utf-8"))

    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class _FakeRerankerHandler(BaseHTTPRequestHandler):
    response_payload: dict[str, Any] = {"scores": [0.9], "indices": [0]}

    def do_POST(self) -> None:  # noqa: N802
        _ = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        self._write_json(200, self.response_payload)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


@contextmanager
def fake_qdrant_server():
    _FakeQdrantHandler.state = _FakeQdrantState()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeQdrantHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, _FakeQdrantHandler.state
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


@contextmanager
def fake_reranker_server(response_payload: dict[str, Any]):
    _FakeRerankerHandler.response_payload = response_payload
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeRerankerHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


@contextmanager
def patched_env(values: dict[str, str]):
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class QdrantProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        ingestion_repository.clear()
        clear_retrieval_provider_cache()

    def tearDown(self) -> None:
        clear_retrieval_provider_cache()

    def test_qdrant_provider_indexes_and_searches_chunks(self) -> None:
        with fake_qdrant_server() as (server, state):
            provider = QdrantIndexProvider(
                base_url=f"http://127.0.0.1:{server.server_port}",
                collection="test_chunks",
            )

            provider.upsert_records(
                [
                    QdrantIndexRecord(
                        chunk_id="chunk_qdrant_1",
                        knowledge_base_id="kb_qdrant",
                        document_id="doc_qdrant",
                        title="Phoenix Memo",
                        content="Phoenix migration memo says staging alerts must stay green for fifteen minutes before rollout approval.",
                        tenant_id="tenant_qdrant",
                        org_id="org_qdrant",
                        metadata={"filename": "phoenix.txt"},
                    )
                ],
                index_name="test_chunks",
            )

            self.assertIn("test_chunks", state.collections)
            stored_ids = list(state.collections["test_chunks"]["points"].keys())
            self.assertEqual(len(stored_ids), 1)
            uuid.UUID(stored_ids[0])

            results = provider.search(
                InternalRetrievalRequestModel(
                    traceId="trace_qdrant_search",
                    query="staging alerts rollout approval",
                    tenantId="tenant_qdrant",
                    orgId="org_qdrant",
                    knowledgeBaseIds=["kb_qdrant"],
                ),
                extract_terms("staging alerts rollout approval"),
            )

            self.assertGreater(len(results), 0)
            self.assertEqual(results[0].chunkId, "chunk_qdrant_1")
            self.assertEqual(results[0].source, "python-qdrant-retrieval")
            self.assertEqual(results[0].metadata["provider"], "qdrant")

    def test_worker_indexes_to_qdrant_and_retrieval_prefers_it(self) -> None:
        with fake_qdrant_server() as (server, state):
            with patched_env(
                {
                    "PYTHON_RETRIEVAL_BACKEND": "hybrid",
                    "PYTHON_QDRANT_URL": f"http://127.0.0.1:{server.server_port}",
                    "PYTHON_QDRANT_COLLECTION": "worker_chunks",
                }
            ):
                clear_retrieval_provider_cache()

                task = create_ingestion_task(
                    IngestionTaskCreateRequestModel(
                        traceId="trace_qdrant_worker",
                        knowledgeBaseId="kb_qdrant_ingested",
                        documentId="doc_qdrant_ingested",
                        requestedBy="admin_qdrant",
                        tenantId="tenant_qdrant",
                        orgId="org_qdrant",
                        source=IngestionSourceModel(
                            sourceType="upload",
                            uri="data:text/plain,Phoenix launch checklist says staging alerts must stay green for fifteen minutes before approval.",
                            filename="phoenix-launch.txt",
                            mimeType="text/plain",
                            sizeBytes=128,
                        ),
                        executionPlan=IngestionExecutionPlanModel(
                            embedding={"enabled": True, "model": "mock-embed", "adapter": "local"},
                            indexing={"enabled": True, "indexName": "worker_chunks", "storeType": "qdrant"},
                        ),
                    )
                )
                run_ingestion_worker(limit=1, task_ids=[task.taskId])

                self.assertIn("worker_chunks", state.collections)
                self.assertEqual(len(state.collections["worker_chunks"]["points"]), 1)

                response = execute_retrieval(
                    InternalRetrievalRequestModel(
                        traceId="trace_qdrant_retrieval",
                        query="What should staging alerts do before approval?",
                        tenantId="tenant_qdrant",
                        orgId="org_qdrant",
                        knowledgeBaseIds=["kb_qdrant_ingested"],
                    )
                )

                self.assertGreater(len(response.chunks), 0)
                self.assertEqual(response.chunks[0].source, "python-qdrant-retrieval")
                self.assertEqual(response.chunks[0].metadata["provider"], "qdrant")

    def test_hybrid_retrieval_prioritizes_qdrant_before_local_fallback(self) -> None:
        with fake_qdrant_server() as (server, state):
            with patched_env(
                {
                    "PYTHON_RETRIEVAL_BACKEND": "hybrid",
                    "PYTHON_QDRANT_URL": f"http://127.0.0.1:{server.server_port}",
                    "PYTHON_QDRANT_COLLECTION": "priority_chunks",
                }
            ):
                clear_retrieval_provider_cache()

                task = create_ingestion_task(
                    IngestionTaskCreateRequestModel(
                        traceId="trace_qdrant_priority",
                        knowledgeBaseId="kb_qdrant_priority",
                        documentId="doc_qdrant_priority",
                        requestedBy="admin_qdrant",
                        tenantId="tenant_qdrant",
                        orgId="org_qdrant",
                        source=IngestionSourceModel(
                            sourceType="upload",
                            uri="data:text/plain,Atlas launch memo says rollback approval requires two green canary windows before production unlock.",
                            filename="atlas-priority.txt",
                            mimeType="text/plain",
                            sizeBytes=128,
                        ),
                        executionPlan=IngestionExecutionPlanModel(
                            embedding={"enabled": True, "model": "mock-embed", "adapter": "local"},
                            indexing={"enabled": True, "indexName": "priority_chunks", "storeType": "qdrant"},
                        ),
                    )
                )
                run_ingestion_worker(limit=1, task_ids=[task.taskId])

                response = execute_retrieval(
                    InternalRetrievalRequestModel(
                        traceId="trace_qdrant_priority_search",
                        query="What approval is required before production unlock?",
                        tenantId="tenant_qdrant",
                        orgId="org_qdrant",
                    )
                )

                self.assertGreater(len(response.chunks), 0)
                self.assertEqual(response.chunks[0].source, "python-qdrant-retrieval")

    def test_bm25_provider_returns_keyword_hits_from_ingested_chunks(self) -> None:
        task = create_ingestion_task(
            IngestionTaskCreateRequestModel(
                traceId="trace_bm25_ingested",
                knowledgeBaseId="kb_bm25",
                documentId="doc_bm25",
                requestedBy="admin_bm25",
                tenantId="tenant_bm25",
                orgId="org_bm25",
                source=IngestionSourceModel(
                    sourceType="upload",
                    uri="data:text/plain,Runbook says rollback approval requires dual canary success before unlock.",
                    filename="runbook.txt",
                    mimeType="text/plain",
                    sizeBytes=96,
                ),
                executionPlan=IngestionExecutionPlanModel(),
            )
        )
        run_ingestion_worker(limit=1, task_ids=[task.taskId])

        provider = BM25RetrievalProvider()
        results = provider.search(
            InternalRetrievalRequestModel(
                traceId="trace_bm25_search",
                query="rollback approval dual canary unlock",
                tenantId="tenant_bm25",
                orgId="org_bm25",
                knowledgeBaseIds=["kb_bm25"],
            ),
            extract_terms("rollback approval dual canary unlock"),
        )

        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].source, "python-bm25-retrieval")
        self.assertEqual(results[0].metadata["provider"], "bm25")

    def test_hybrid_retrieval_adds_fusion_metadata(self) -> None:
        with fake_qdrant_server() as (server, _state):
            with patched_env(
                {
                    "PYTHON_RETRIEVAL_BACKEND": "hybrid",
                    "PYTHON_QDRANT_URL": f"http://127.0.0.1:{server.server_port}",
                    "PYTHON_QDRANT_COLLECTION": "fusion_chunks",
                }
            ):
                clear_retrieval_provider_cache()
                task = create_ingestion_task(
                    IngestionTaskCreateRequestModel(
                        traceId="trace_hybrid_fusion",
                        knowledgeBaseId="kb_hybrid_fusion",
                        documentId="doc_hybrid_fusion",
                        requestedBy="admin_hybrid",
                        tenantId="tenant_hybrid",
                        orgId="org_hybrid",
                        source=IngestionSourceModel(
                            sourceType="upload",
                            uri="data:text/plain,Atlas release checklist requires rollback approval and two canary windows before unlock.",
                            filename="atlas-fusion.txt",
                            mimeType="text/plain",
                            sizeBytes=120,
                        ),
                        executionPlan=IngestionExecutionPlanModel(
                            embedding={"enabled": True, "model": "mock-embed", "adapter": "local"},
                            indexing={"enabled": True, "indexName": "fusion_chunks", "storeType": "qdrant"},
                        ),
                    )
                )
                run_ingestion_worker(limit=1, task_ids=[task.taskId])

                response = execute_retrieval(
                    InternalRetrievalRequestModel(
                        traceId="trace_hybrid_fusion_search",
                        query="rollback approval canary unlock",
                        tenantId="tenant_hybrid",
                        orgId="org_hybrid",
                    )
                )

                self.assertGreater(len(response.chunks), 0)
                self.assertEqual(response.chunks[0].metadata["retrievalMode"], "hybrid")
                self.assertEqual(response.chunks[0].metadata["fusionStrategy"], "rrf")
                self.assertIn("keywordSource", response.chunks[0].metadata)
                self.assertIn("denseSource", response.chunks[0].metadata)

    def test_hybrid_retrieval_applies_bge_reranker_reordering(self) -> None:
        with fake_qdrant_server() as (qdrant_server, _state):
            with fake_reranker_server({"scores": [0.93, 0.22], "indices": [1, 0]} ) as reranker_server:
                with patched_env(
                    {
                        "PYTHON_RETRIEVAL_BACKEND": "hybrid",
                        "PYTHON_QDRANT_URL": f"http://127.0.0.1:{qdrant_server.server_port}",
                        "PYTHON_QDRANT_COLLECTION": "rerank_chunks",
                        "PYTHON_RERANKER_BACKEND": "bge",
                        "PYTHON_BGE_RERANKER_URL": f"http://127.0.0.1:{reranker_server.server_port}/rerank",
                    }
                ):
                    clear_retrieval_provider_cache()
                    provider = QdrantIndexProvider(
                        base_url=f"http://127.0.0.1:{qdrant_server.server_port}",
                        collection="rerank_chunks",
                    )
                    provider.upsert_records(
                        [
                            QdrantIndexRecord(
                                chunk_id="chunk_rerank_a",
                                knowledge_base_id="kb_rerank",
                                document_id="doc_rerank_a",
                                title="Alpha Memo",
                                content="Alpha memo mentions approval and unlock.",
                                tenant_id="tenant_rerank",
                                org_id="org_rerank",
                                metadata={"filename": "alpha.txt"},
                            ),
                            QdrantIndexRecord(
                                chunk_id="chunk_rerank_b",
                                knowledge_base_id="kb_rerank",
                                document_id="doc_rerank_b",
                                title="Atlas Launch Memo",
                                content="Atlas launch memo requires two canary windows before unlock.",
                                tenant_id="tenant_rerank",
                                org_id="org_rerank",
                                metadata={"filename": "atlas.txt"},
                            ),
                        ],
                        index_name="rerank_chunks",
                    )

                    response = execute_retrieval(
                        InternalRetrievalRequestModel(
                            traceId="trace_rerank_search",
                            query="approval before unlock",
                            tenantId="tenant_rerank",
                            orgId="org_rerank",
                            knowledgeBaseIds=["kb_rerank"],
                        )
                    )

                    self.assertGreater(len(response.chunks), 1)
                    self.assertEqual(response.chunks[0].title, "Atlas Launch Memo")
                    self.assertEqual(response.chunks[0].metadata["rerankSource"], "bge-reranker-v2-m3")

    def test_hybrid_retrieval_uses_legacy_bge_url_by_default(self) -> None:
        with fake_qdrant_server() as (qdrant_server, _state):
            with fake_reranker_server({"scores": [0.91, 0.17], "indices": [1, 0]}) as reranker_server:
                with patched_env(
                    {
                        "PYTHON_RETRIEVAL_BACKEND": "hybrid",
                        "PYTHON_QDRANT_URL": f"http://127.0.0.1:{qdrant_server.server_port}",
                        "PYTHON_QDRANT_COLLECTION": "legacy_bge_chunks",
                        "BGE_RERANKER_URL": f"http://127.0.0.1:{reranker_server.server_port}/rerank",
                    }
                ):
                    clear_retrieval_provider_cache()
                    provider = QdrantIndexProvider(
                        base_url=f"http://127.0.0.1:{qdrant_server.server_port}",
                        collection="legacy_bge_chunks",
                    )
                    provider.upsert_records(
                        [
                            QdrantIndexRecord(
                                chunk_id="chunk_legacy_a",
                                knowledge_base_id="kb_legacy",
                                document_id="doc_legacy_a",
                                title="Alpha Memo",
                                content="Alpha memo mentions approval and unlock.",
                                tenant_id="tenant_legacy",
                                org_id="org_legacy",
                                metadata={"filename": "alpha.txt"},
                            ),
                            QdrantIndexRecord(
                                chunk_id="chunk_legacy_b",
                                knowledge_base_id="kb_legacy",
                                document_id="doc_legacy_b",
                                title="Atlas Launch Memo",
                                content="Atlas launch memo requires two canary windows before unlock.",
                                tenant_id="tenant_legacy",
                                org_id="org_legacy",
                                metadata={"filename": "atlas.txt"},
                            ),
                        ],
                        index_name="legacy_bge_chunks",
                    )

                    response = execute_retrieval(
                        InternalRetrievalRequestModel(
                            traceId="trace_legacy_bge_search",
                            query="approval before unlock",
                            tenantId="tenant_legacy",
                            orgId="org_legacy",
                            knowledgeBaseIds=["kb_legacy"],
                        )
                    )

                    self.assertGreater(len(response.chunks), 1)
                    self.assertEqual(response.chunks[0].title, "Atlas Launch Memo")
                    self.assertEqual(response.chunks[0].metadata["rerankSource"], "bge-reranker-v2-m3")

    def test_hybrid_retrieval_accepts_v1_rerank_response_shape(self) -> None:
        with fake_qdrant_server() as (qdrant_server, _state):
            with fake_reranker_server(
                {
                    "results": [
                        {"index": 1, "relevance_score": 0.94, "document": {"text": "Atlas launch memo requires two canary windows before unlock."}},
                        {"index": 0, "relevance_score": 0.21, "document": {"text": "Alpha memo mentions approval and unlock."}},
                    ]
                }
            ) as reranker_server:
                with patched_env(
                    {
                        "PYTHON_RETRIEVAL_BACKEND": "hybrid",
                        "PYTHON_QDRANT_URL": f"http://127.0.0.1:{qdrant_server.server_port}",
                        "PYTHON_QDRANT_COLLECTION": "v1_rerank_chunks",
                        "PYTHON_RERANKER_BACKEND": "bge",
                        "PYTHON_BGE_RERANKER_URL": f"http://127.0.0.1:{reranker_server.server_port}/v1/rerank",
                    }
                ):
                    clear_retrieval_provider_cache()
                    provider = QdrantIndexProvider(
                        base_url=f"http://127.0.0.1:{qdrant_server.server_port}",
                        collection="v1_rerank_chunks",
                    )
                    provider.upsert_records(
                        [
                            QdrantIndexRecord(
                                chunk_id="chunk_v1_a",
                                knowledge_base_id="kb_v1",
                                document_id="doc_v1_a",
                                title="Alpha Memo",
                                content="Alpha memo mentions approval and unlock.",
                                tenant_id="tenant_v1",
                                org_id="org_v1",
                                metadata={"filename": "alpha.txt"},
                            ),
                            QdrantIndexRecord(
                                chunk_id="chunk_v1_b",
                                knowledge_base_id="kb_v1",
                                document_id="doc_v1_b",
                                title="Atlas Launch Memo",
                                content="Atlas launch memo requires two canary windows before unlock.",
                                tenant_id="tenant_v1",
                                org_id="org_v1",
                                metadata={"filename": "atlas.txt"},
                            ),
                        ],
                        index_name="v1_rerank_chunks",
                    )

                    response = execute_retrieval(
                        InternalRetrievalRequestModel(
                            traceId="trace_v1_rerank_search",
                            query="approval before unlock",
                            tenantId="tenant_v1",
                            orgId="org_v1",
                            knowledgeBaseIds=["kb_v1"],
                        )
                    )

                    self.assertGreater(len(response.chunks), 1)
                    self.assertEqual(response.chunks[0].title, "Atlas Launch Memo")
                    self.assertEqual(response.chunks[0].metadata["rerankSource"], "bge-reranker-v2-m3")


if __name__ == "__main__":
    unittest.main()
