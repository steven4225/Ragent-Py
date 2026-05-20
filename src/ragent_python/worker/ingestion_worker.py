from __future__ import annotations

import base64
from urllib.parse import unquote_to_bytes
from uuid import uuid4

from ragent_python.contracts.ingestion import (
    IngestionProcessingTraceEventModel,
    IngestionTaskStatusModel,
    IngestionWorkerRunResponseModel,
)
from ragent_python.contracts.public_api import utc_now_iso
from ragent_python.retrieval.providers import get_index_provider
from ragent_python.retrieval.qdrant_provider import QdrantIndexRecord
from ragent_python.storage.ingestion_repository import ingestion_repository


def run_ingestion_worker(limit: int = 1, task_ids: list[str] | None = None) -> IngestionWorkerRunResponseModel:
    worker_id = f"worker_{uuid4().hex[:8]}"
    processed_task_ids: list[str] = []
    succeeded_task_ids: list[str] = []
    failed_task_ids: list[str] = []
    skipped_task_ids: list[str] = []

    candidates = ingestion_repository.claim_pending(worker_id=worker_id, limit=limit, task_ids=task_ids or None)
    if task_ids:
        scheduled_ids = {task.taskId for task in candidates}
        skipped_task_ids.extend([task_id for task_id in task_ids if task_id not in scheduled_ids])

    for task in candidates:
        processed_task_ids.append(task.taskId)
        updated_task = _process_task(task, worker_id=worker_id)
        if updated_task.status == "succeeded":
            succeeded_task_ids.append(updated_task.taskId)
        elif updated_task.status == "failed":
            failed_task_ids.append(updated_task.taskId)

    return IngestionWorkerRunResponseModel(
        workerId=worker_id,
        processedTaskIds=processed_task_ids,
        succeededTaskIds=succeeded_task_ids,
        failedTaskIds=failed_task_ids,
        skippedTaskIds=skipped_task_ids,
    )


def _process_task(task: IngestionTaskStatusModel, worker_id: str) -> IngestionTaskStatusModel:
    started_at = utc_now_iso()
    running_task = _update_task(
        task,
        status="running",
        current_stage="parser",
        started_at=started_at,
        attempt_count=task.attemptCount + 1,
        trace_event=IngestionProcessingTraceEventModel(
            traceId=task.traceId,
            taskId=task.taskId,
            stage="worker-claimed",
            level="info",
            status="running",
            message="Python ingestion worker claimed the task.",
            tenantId=task.tenantId,
            orgId=task.orgId,
            metadata={"backend": "python", "workerId": worker_id},
        ),
    )
    running_task = _update_task(
        running_task,
        status="running",
        current_stage="parser",
        trace_event=IngestionProcessingTraceEventModel(
            traceId=task.traceId,
            taskId=task.taskId,
            stage="parsing",
            level="info",
            status="running",
            message="Mock parser started.",
            tenantId=task.tenantId,
            orgId=task.orgId,
            metadata={"backend": "python", "workerId": worker_id},
        ),
    )

    should_fail = bool(task.metadata.get("forceFailure")) or str(task.source.uri).startswith("fail://")
    if should_fail:
        failed_task = _update_task(
            running_task,
            status="failed",
            current_stage="failed",
            finished_at=utc_now_iso(),
            failure_reason="Simulated worker failure",
            failure_stage="parser",
            error_message="Simulated worker failure",
            retryable=False,
            trace_event=IngestionProcessingTraceEventModel(
                traceId=task.traceId,
                taskId=task.taskId,
                stage="failed",
                level="error",
                status="failed",
                message="Mock parser failed.",
                tenantId=task.tenantId,
                orgId=task.orgId,
                metadata={"backend": "python", "workerId": worker_id},
            ),
        )
        ingestion_repository.upsert(failed_task)
        return failed_task

    parsed_text = _extract_source_text(task)
    parser_result = {
        "parserName": "python-mock-parser",
        "parserVersion": "0.1.0",
        "status": "succeeded",
        "warnings": [],
        "parsedDocument": {
            "documentId": task.documentId,
            "title": task.source.filename,
            "mimeType": task.source.mimeType,
            "language": "en",
            "charCount": len(parsed_text),
            "pageCount": 1,
            "metadata": {"backend": "python", "workerId": worker_id},
            "content": {
                "text": parsed_text,
                "sections": [],
            },
        },
        "chunks": [],
        "metrics": {
            "parseDurationMs": 5,
            "chunkDurationMs": 3,
        },
        "errorMessage": None,
    }
    chunks = [
        {
            "chunkId": f"{task.taskId}_chunk_0",
            "documentId": task.documentId,
            "chunkIndex": 0,
            "text": parsed_text,
            "charCount": len(parsed_text),
            "tokenCount": max(1, len(parsed_text.split())),
            "metadata": {
                "sectionPath": [],
                "startOffset": 0,
                "endOffset": len(parsed_text),
                "pageNumber": 1,
            },
        }
    ]

    chunked_task = _update_task(
        running_task,
        status="running",
        current_stage="chunker",
        parser_result=parser_result,
        chunks=chunks,
        trace_event=IngestionProcessingTraceEventModel(
            traceId=task.traceId,
            taskId=task.taskId,
            stage="chunking",
            level="info",
            status="running",
            message="Mock chunker produced one chunk.",
            tenantId=task.tenantId,
            orgId=task.orgId,
            metadata={"backend": "python", "workerId": worker_id, "chunkCount": len(chunks)},
        ),
    )

    current_task = chunked_task
    if current_task.executionPlan.embedding.enabled:
        embedding_result = {
            "status": "succeeded",
            "model": current_task.executionPlan.embedding.model or "mock-embedding-model",
            "source": "python-mock-embedding",
            "vectorCount": len(chunks),
            "dimensions": 8,
            "artifacts": [],
            "errorMessage": None,
            "metadata": {"backend": "python", "workerId": worker_id},
        }
        current_task = _update_task(
            current_task,
            status="running",
            current_stage="embedding",
            embedding_result=embedding_result,
            trace_event=IngestionProcessingTraceEventModel(
                traceId=task.traceId,
                taskId=task.taskId,
                stage="embedding",
                level="info",
                status="running",
                message="Mock embedding completed.",
                tenantId=task.tenantId,
                orgId=task.orgId,
                metadata={"backend": "python", "workerId": worker_id},
            ),
        )

    if current_task.executionPlan.indexing.enabled:
        try:
            index_write_result = _index_chunks(current_task=current_task, worker_id=worker_id)
        except Exception as exc:
            failed_task = _update_task(
                current_task,
                status="failed",
                current_stage="failed",
                finished_at=utc_now_iso(),
                failure_reason="Indexing failed",
                failure_stage="indexing",
                error_message=str(exc),
                retryable=False,
                trace_event=IngestionProcessingTraceEventModel(
                    traceId=task.traceId,
                    taskId=task.taskId,
                    stage="failed",
                    level="error",
                    status="failed",
                    message="Indexing failed.",
                    tenantId=task.tenantId,
                    orgId=task.orgId,
                    metadata={"backend": "python", "workerId": worker_id, "stage": "indexing"},
                ),
            )
            ingestion_repository.upsert(failed_task)
            return failed_task
        current_task = _update_task(
            current_task,
            status="running",
            current_stage="indexing",
            index_write_result=index_write_result,
            trace_event=IngestionProcessingTraceEventModel(
                traceId=task.traceId,
                taskId=task.taskId,
                stage="indexing",
                level="info",
                status="running",
                message="Mock indexing completed.",
                tenantId=task.tenantId,
                orgId=task.orgId,
                metadata={"backend": "python", "workerId": worker_id},
            ),
        )

    completed_task = _update_task(
        current_task,
        status="succeeded",
        current_stage="completed",
        finished_at=utc_now_iso(),
        retryable=False,
        trace_event=IngestionProcessingTraceEventModel(
            traceId=task.traceId,
            taskId=task.taskId,
            stage="completed",
            level="info",
            status="succeeded",
            message="Python ingestion worker completed the task.",
            tenantId=task.tenantId,
            orgId=task.orgId,
            metadata={"backend": "python", "workerId": worker_id},
        ),
    )
    ingestion_repository.upsert(completed_task)
    return completed_task


def _extract_source_text(task: IngestionTaskStatusModel) -> str:
    uri = str(task.source.uri)
    if uri.startswith("data:"):
        header, _, payload = uri.partition(",")
        if not payload:
            return f"Parsed content for {task.source.filename}"
        try:
            raw_bytes = base64.b64decode(payload) if ";base64" in header else unquote_to_bytes(payload)
            decoded = raw_bytes.decode("utf-8", errors="replace").strip()
            if decoded:
                return decoded
        except Exception:
            pass
    return f"Parsed content for {task.source.filename}"


def _index_chunks(*, current_task: IngestionTaskStatusModel, worker_id: str) -> dict:
    store_type = current_task.executionPlan.indexing.storeType or "mock-store"
    index_name = current_task.executionPlan.indexing.indexName or "mock-index"
    provider = get_index_provider(store_type)
    if provider is None:
        return {
            "status": "succeeded",
            "indexName": index_name,
            "storeType": store_type,
            "source": "python-mock-indexer",
            "operation": "upsert",
            "recordCount": len(current_task.chunks),
            "indexedChunkCount": len(current_task.chunks),
            "skippedRecordCount": 0,
            "replacedRecordCount": 0,
            "deletedRecordCount": 0,
            "records": [],
            "errorMessage": None,
            "metadata": {"backend": "python", "workerId": worker_id},
        }

    parser_document = current_task.parserResult.get("parsedDocument", {}) if isinstance(current_task.parserResult, dict) else {}
    document_title = parser_document.get("title") if isinstance(parser_document.get("title"), str) else current_task.source.filename
    records = [
        QdrantIndexRecord(
            chunk_id=str(chunk["chunkId"]),
            knowledge_base_id=current_task.knowledgeBaseId,
            document_id=str(chunk["documentId"]),
            title=document_title,
            content=str(chunk["text"]),
            tenant_id=current_task.tenantId,
            org_id=current_task.orgId,
            metadata={
                "filename": current_task.source.filename,
                "taskId": current_task.taskId,
                "traceId": current_task.traceId,
                "chunkIndex": chunk.get("chunkIndex", 0),
                "sourceUri": current_task.source.uri,
            },
        )
        for chunk in current_task.chunks
        if isinstance(chunk, dict) and {"chunkId", "documentId", "text"}.issubset(chunk)
    ]
    result = provider.upsert_records(records, index_name=index_name, idempotency_key=current_task.taskId)
    result.setdefault("metadata", {})
    result["metadata"].update({"backend": "python", "workerId": worker_id})
    return result


def _update_task(
    task: IngestionTaskStatusModel,
    *,
    status: str,
    current_stage: str,
    trace_event: IngestionProcessingTraceEventModel,
    started_at: str | None = None,
    finished_at: str | None = None,
    attempt_count: int | None = None,
    parser_result: dict | None = None,
    embedding_result: dict | None = None,
    index_write_result: dict | None = None,
    chunks: list[dict] | None = None,
    retryable: bool | None = None,
    failure_reason: str | None = None,
    failure_stage: str | None = None,
    error_message: str | None = None,
) -> IngestionTaskStatusModel:
    updated_task = task.model_copy(
        update={
            "status": status,
            "currentStage": current_stage,
            "updatedAt": utc_now_iso(),
            "startedAt": started_at if started_at is not None else task.startedAt,
            "finishedAt": finished_at if finished_at is not None else task.finishedAt,
            "attemptCount": attempt_count if attempt_count is not None else task.attemptCount,
            "parserResult": parser_result if parser_result is not None else task.parserResult,
            "embeddingResult": embedding_result if embedding_result is not None else task.embeddingResult,
            "indexWriteResult": index_write_result if index_write_result is not None else task.indexWriteResult,
            "chunks": chunks if chunks is not None else task.chunks,
            "retryable": retryable if retryable is not None else task.retryable,
            "failureReason": failure_reason if failure_reason is not None else task.failureReason,
            "failureStage": failure_stage if failure_stage is not None else task.failureStage,
            "errorMessage": error_message if error_message is not None else task.errorMessage,
            "trace": [*task.trace, trace_event],
        }
    )
    ingestion_repository.upsert(updated_task)
    return updated_task
