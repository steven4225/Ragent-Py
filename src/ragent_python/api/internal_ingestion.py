from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ragent_python.contracts.ingestion import IngestionTaskListResponseModel, IngestionTaskStatusModel
from ragent_python.contracts.internal_api import InternalIngestionTaskCreateRequestModel
from ragent_python.services.ingestion_service import create_ingestion_task, get_ingestion_task, list_ingestion_tasks

router = APIRouter(prefix="/internal/ingestion", tags=["ingestion"])


@router.get("/tasks", response_model=IngestionTaskListResponseModel)
async def internal_list_ingestion_tasks(
    tenantId: str | None = Query(default=None),
    orgId: str | None = Query(default=None),
) -> IngestionTaskListResponseModel:
    return list_ingestion_tasks(tenant_id=tenantId, org_id=orgId)


@router.post("/tasks", response_model=IngestionTaskStatusModel)
async def internal_create_ingestion_task(
    request: InternalIngestionTaskCreateRequestModel,
) -> IngestionTaskStatusModel:
    return create_ingestion_task(request)


@router.get("/tasks/{task_id}", response_model=IngestionTaskStatusModel)
async def internal_get_ingestion_task(task_id: str) -> IngestionTaskStatusModel:
    task = get_ingestion_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={"code": "INGESTION_TASK_NOT_FOUND", "message": "Task not found."})
    return task
