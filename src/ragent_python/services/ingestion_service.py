from __future__ import annotations

from uuid import uuid4

from ragent_python.contracts.ingestion import (
    IngestionProcessingTraceEventModel,
    IngestionTaskCreateRequestModel,
    IngestionTaskListResponseModel,
    IngestionTaskStatusModel,
)
from ragent_python.contracts.public_api import utc_now_iso
from ragent_python.storage.ingestion_repository import ingestion_repository


def create_ingestion_task(request: IngestionTaskCreateRequestModel) -> IngestionTaskStatusModel:
    timestamp = utc_now_iso()
    task_id = f"ing_{uuid4().hex[:12]}"

    trace = [
        IngestionProcessingTraceEventModel(
            traceId=request.traceId,
            taskId=task_id,
            stage="task-created",
            level="info",
            status="pending",
            message="Python ingestion task created.",
            tenantId=request.tenantId,
            orgId=request.orgId,
            metadata={"backend": "python"},
        ),
        IngestionProcessingTraceEventModel(
            traceId=request.traceId,
            taskId=task_id,
            stage="queued",
            level="info",
            status="pending",
            message="Python ingestion task is queued for worker pickup.",
            tenantId=request.tenantId,
            orgId=request.orgId,
            metadata={"backend": "python", "queue": "phase1-placeholder"},
        ),
    ]

    task = IngestionTaskStatusModel(
        taskId=task_id,
        traceId=request.traceId,
        knowledgeBaseId=request.knowledgeBaseId,
        documentId=request.documentId,
        requestedBy=request.requestedBy,
        tenantId=request.tenantId,
        orgId=request.orgId,
        source=request.source,
        status="pending",
        currentStage="queued",
        createdAt=timestamp,
        updatedAt=timestamp,
        executionPlan=request.executionPlan,
        trace=trace,
        metadata={
            **request.metadata,
            "backend": "python",
            "executionMode": "phase1-skeleton",
        },
    )
    ingestion_repository.upsert(task)
    return task


def get_ingestion_task(task_id: str) -> IngestionTaskStatusModel | None:
    return ingestion_repository.get_by_id(task_id)


def list_ingestion_tasks(tenant_id: str | None = None, org_id: str | None = None) -> IngestionTaskListResponseModel:
    return IngestionTaskListResponseModel(items=ingestion_repository.list(tenant_id=tenant_id, org_id=org_id))
