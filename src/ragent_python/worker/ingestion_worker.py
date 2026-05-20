from __future__ import annotations

from uuid import uuid4

from ragent_python.contracts.ingestion import (
    IngestionProcessingTraceEventModel,
    IngestionTaskStatusModel,
    IngestionWorkerRunResponseModel,
)
from ragent_python.contracts.public_api import utc_now_iso
from ragent_python.storage.ingestion_repository import ingestion_repository


def run_ingestion_worker(limit: int = 1, task_ids: list[str] | None = None) -> IngestionWorkerRunResponseModel:
    worker_id = f"worker_{uuid4().hex[:8]}"
    processed_task_ids: list[str] = []
    succeeded_task_ids: list[str] = []
    failed_task_ids: list[str] = []
    skipped_task_ids: list[str] = []

    candidates = ingestion_repository.list_pending(limit=limit, task_ids=task_ids or None)
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
            "charCount": 96,
            "pageCount": 1,
            "metadata": {"backend": "python", "workerId": worker_id},
            "content": {
                "text": f"Parsed content for {task.source.filename}",
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
            "text": f"Parsed content for {task.source.filename}",
            "charCount": 35,
            "tokenCount": 8,
            "metadata": {
                "sectionPath": [],
                "startOffset": 0,
                "endOffset": 35,
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
        index_write_result = {
            "status": "succeeded",
            "indexName": current_task.executionPlan.indexing.indexName or "mock-index",
            "storeType": current_task.executionPlan.indexing.storeType or "mock-store",
            "source": "python-mock-indexer",
            "operation": "upsert",
            "recordCount": len(chunks),
            "indexedChunkCount": len(chunks),
            "skippedRecordCount": 0,
            "replacedRecordCount": 0,
            "deletedRecordCount": 0,
            "records": [],
            "errorMessage": None,
            "metadata": {"backend": "python", "workerId": worker_id},
        }
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
