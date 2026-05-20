from __future__ import annotations

import hashlib
import math
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.contracts.public_api import RetrievalChunkModel


@dataclass(frozen=True, slots=True)
class QdrantIndexRecord:
    chunk_id: str
    knowledge_base_id: str
    document_id: str
    title: str
    content: str
    tenant_id: str | None = None
    org_id: str | None = None
    metadata: dict[str, Any] | None = None


class QdrantIndexProvider:
    provider_name = "python-qdrant-retrieval"

    def __init__(
        self,
        *,
        base_url: str,
        collection: str,
        api_key: str | None = None,
        timeout_ms: int = 5000,
        vector_size: int = 8,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.collection = collection.strip() or "ragent_python_chunks"
        self.api_key = (api_key or "").strip()
        self.timeout_ms = timeout_ms
        self.vector_size = max(2, vector_size)
        self._collection_ready = False

    def upsert_records(
        self,
        records: list[QdrantIndexRecord],
        *,
        index_name: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not records:
            return {
                "status": "succeeded",
                "indexName": index_name or self.collection,
                "storeType": "qdrant",
                "source": "python-qdrant-indexer",
                "operation": "upsert",
                "recordCount": 0,
                "indexedChunkCount": 0,
                "skippedRecordCount": 0,
                "replacedRecordCount": 0,
                "deletedRecordCount": 0,
                "records": [],
                "errorMessage": None,
                "metadata": {
                    "backend": "python",
                    "indexBackend": "qdrant",
                    "collection": self.collection,
                    "qdrantURL": self.base_url,
                    "idempotencyKey": idempotency_key or "",
                },
            }

        self._ensure_collection()
        points = [
            {
                "id": _point_id_for_chunk(record.chunk_id),
                "vector": embed_text(record.content, dimensions=self.vector_size),
                "payload": {
                    "chunkId": record.chunk_id,
                    "knowledgeBaseId": record.knowledge_base_id,
                    "documentId": record.document_id,
                    "title": record.title,
                    "content": record.content,
                    "tenantId": record.tenant_id,
                    "orgId": record.org_id,
                    **(record.metadata or {}),
                },
            }
            for record in records
        ]
        self._request("PUT", f"/collections/{self.collection}/points", json_body={"points": points})
        return {
            "status": "succeeded",
            "indexName": index_name or self.collection,
            "storeType": "qdrant",
            "source": "python-qdrant-indexer",
            "operation": "upsert",
            "recordCount": len(records),
            "indexedChunkCount": len(records),
            "skippedRecordCount": 0,
            "replacedRecordCount": 0,
            "deletedRecordCount": 0,
            "records": [],
            "errorMessage": None,
            "metadata": {
                "backend": "python",
                "indexBackend": "qdrant",
                "collection": self.collection,
                "qdrantURL": self.base_url,
                "vectorDimensions": self.vector_size,
                "idempotencyKey": idempotency_key or "",
            },
        }

    def search(self, request: InternalRetrievalRequestModel, query_terms: list[str]) -> list[RetrievalChunkModel]:
        if not request.query.strip():
            return []
        self._ensure_collection()
        query_vector = embed_text(request.query, dimensions=self.vector_size)
        response = self._request(
            "POST",
            f"/collections/{self.collection}/points/search",
            json_body={
                "vector": query_vector,
                "limit": max(1, min(request.topK, 20)),
                "with_payload": True,
                "filter": _build_filter(request),
            },
        )
        hits = response.get("result", [])
        results: list[RetrievalChunkModel] = []
        for hit in hits:
            payload = hit.get("payload") or {}
            content = payload.get("content")
            chunk_id = payload.get("chunkId") or hit.get("id")
            document_id = payload.get("documentId")
            knowledge_base_id = payload.get("knowledgeBaseId")
            title = payload.get("title") or payload.get("filename") or "Untitled"
            if not all(isinstance(value, str) for value in [content, chunk_id, document_id, knowledge_base_id]):
                continue
            results.append(
                RetrievalChunkModel(
                    chunkId=str(chunk_id),
                    knowledgeBaseId=knowledge_base_id,
                    documentId=document_id,
                    title=str(title),
                    content=content,
                    score=float(hit.get("score") or 0.0),
                    source=self.provider_name,
                    metadata={
                        "provider": "qdrant",
                        "indexBackend": "qdrant",
                        "collection": self.collection,
                        "filename": payload.get("filename"),
                    },
                )
            )
        return results

    def _ensure_collection(self) -> None:
        if self._collection_ready:
            return
        response = self._request("GET", f"/collections/{self.collection}", allow_statuses={404})
        if response is None:
            self._request(
                "PUT",
                f"/collections/{self.collection}",
                json_body={
                    "vectors": {
                        "size": self.vector_size,
                        "distance": "Cosine",
                    }
                },
            )
        self._collection_ready = True

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        allow_statuses: set[int] | None = None,
    ) -> dict[str, Any] | None:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["api-key"] = self.api_key
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_ms / 1000) as client:
            response = client.request(method, path, headers=headers, json=json_body)
        if allow_statuses and response.status_code in allow_statuses:
            return None
        response.raise_for_status()
        return response.json()


def embed_text(text: str, *, dimensions: int = 8) -> list[float]:
    vector = [0.0] * dimensions
    normalized_terms = [token for token in text.lower().split() if token.strip()]
    if not normalized_terms:
        return vector
    for token in normalized_terms:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for index in range(dimensions):
            chunk = digest[index * 4 : index * 4 + 4]
            value = int.from_bytes(chunk, byteorder="big", signed=False)
            centered = (value / 0xFFFFFFFF) * 2 - 1
            vector[index] += centered
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _build_filter(request: InternalRetrievalRequestModel) -> dict[str, Any] | None:
    must: list[dict[str, Any]] = []
    if request.tenantId:
        must.append({"key": "tenantId", "match": {"value": request.tenantId}})
    if request.orgId:
        must.append({"key": "orgId", "match": {"value": request.orgId}})
    if not request.knowledgeBaseIds:
        return {"must": must} if must else None
    if len(request.knowledgeBaseIds) == 1:
        must.append({"key": "knowledgeBaseId", "match": {"value": request.knowledgeBaseIds[0]}})
        return {"must": must}
    return {
        "must": must,
        "should": [
            {"key": "knowledgeBaseId", "match": {"value": knowledge_base_id}}
            for knowledge_base_id in request.knowledgeBaseIds
        ],
    }


def _point_id_for_chunk(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"ragent-python:{chunk_id}"))
