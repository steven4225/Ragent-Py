from __future__ import annotations

from typing import Iterable

from ragent_python.contracts.ingestion import IngestionTaskStatusModel


class InMemoryIngestionRepository:
    def __init__(self) -> None:
        self._tasks: dict[str, IngestionTaskStatusModel] = {}

    def upsert(self, task: IngestionTaskStatusModel) -> None:
        self._tasks[task.taskId] = task

    def get_by_id(self, task_id: str) -> IngestionTaskStatusModel | None:
        return self._tasks.get(task_id)

    def list(self, tenant_id: str | None = None, org_id: str | None = None) -> list[IngestionTaskStatusModel]:
        tasks: Iterable[IngestionTaskStatusModel] = self._tasks.values()
        if tenant_id is not None:
            tasks = [task for task in tasks if task.tenantId == tenant_id]
        if org_id is not None:
            tasks = [task for task in tasks if task.orgId == org_id]
        return sorted(tasks, key=lambda task: task.createdAt, reverse=True)


ingestion_repository = InMemoryIngestionRepository()
