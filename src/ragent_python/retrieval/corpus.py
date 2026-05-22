"""Retrieval corpus iterators.

After Step C the six-chunk demo dataset (`LOCAL_KNOWLEDGE`,
`LocalKnowledgeChunk`, `iter_local_corpus`) is owned by
`modules/demo_corpus/`. This module re-exports those symbols so legacy
call sites (`bm25_provider`, `providers`) stay byte-for-byte compatible,
and keeps the ingestion-corpus iterator that is platform-level
(not module-owned).
"""

from __future__ import annotations

from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.modules.demo_corpus.corpus import (
    LOCAL_KNOWLEDGE,
    LocalKnowledgeChunk,
    iter_local_corpus,
)
from ragent_python.retrieval.types import RetrievalCorpusChunk
from ragent_python.storage.ingestion_repository import ingestion_repository


__all__ = [
    "LOCAL_KNOWLEDGE",
    "LocalKnowledgeChunk",
    "RetrievalCorpusChunk",
    "iter_ingestion_corpus",
    "iter_local_corpus",
]


def iter_ingestion_corpus(request: InternalRetrievalRequestModel) -> list[RetrievalCorpusChunk]:
    tasks = ingestion_repository.list(tenant_id=request.tenantId, org_id=request.orgId)
    results: list[RetrievalCorpusChunk] = []
    for task in tasks:
        if task.status != "succeeded" or task.currentStage != "completed":
            continue
        if request.knowledgeBaseIds and task.knowledgeBaseId not in request.knowledgeBaseIds:
            continue

        parsed_document = None
        if isinstance(task.parserResult, dict):
            parsed_document = task.parserResult.get("parsedDocument")
        document_title = (
            parsed_document.get("title")
            if isinstance(parsed_document, dict) and isinstance(parsed_document.get("title"), str)
            else task.source.filename
        )

        for chunk in task.chunks:
            text = chunk.get("text") if isinstance(chunk, dict) else None
            chunk_id = chunk.get("chunkId") if isinstance(chunk, dict) else None
            document_id = chunk.get("documentId") if isinstance(chunk, dict) else None
            if not isinstance(text, str) or not isinstance(chunk_id, str) or not isinstance(document_id, str):
                continue
            results.append(
                RetrievalCorpusChunk(
                    chunk_id=chunk_id,
                    knowledge_base_id=task.knowledgeBaseId,
                    document_id=document_id,
                    title=document_title,
                    content=text,
                    tenant_id=task.tenantId,
                    org_id=task.orgId,
                    metadata={
                        "provider": "ingestion-task",
                        "taskId": task.taskId,
                        "filename": task.source.filename,
                    },
                    source="python-ingestion-retrieval",
                )
            )
    return results
