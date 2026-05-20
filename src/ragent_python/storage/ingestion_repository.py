from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Protocol

from ragent_python.config import PROJECT_ROOT, get_settings
from ragent_python.contracts.ingestion import IngestionTaskStatusModel


class IngestionRepository(Protocol):
    def upsert(self, task: IngestionTaskStatusModel) -> None: ...

    def get_by_id(self, task_id: str) -> IngestionTaskStatusModel | None: ...

    def list(self, tenant_id: str | None = None, org_id: str | None = None) -> list[IngestionTaskStatusModel]: ...

    def list_pending(self, limit: int = 1, task_ids: list[str] | None = None) -> list[IngestionTaskStatusModel]: ...

    def claim_pending(
        self,
        worker_id: str,
        limit: int = 1,
        task_ids: list[str] | None = None,
    ) -> list[IngestionTaskStatusModel]: ...

    def clear(self) -> None: ...


class InMemoryIngestionRepository:
    def __init__(self) -> None:
        self._tasks: dict[str, IngestionTaskStatusModel] = {}

    def upsert(self, task: IngestionTaskStatusModel) -> None:
        self._tasks[task.taskId] = task

    def get_by_id(self, task_id: str) -> IngestionTaskStatusModel | None:
        return self._tasks.get(task_id)

    def list(self, tenant_id: str | None = None, org_id: str | None = None) -> list[IngestionTaskStatusModel]:
        tasks = list(self._tasks.values())
        if tenant_id is not None:
            tasks = [task for task in tasks if task.tenantId == tenant_id]
        if org_id is not None:
            tasks = [task for task in tasks if task.orgId == org_id]
        return sorted(tasks, key=lambda task: task.createdAt, reverse=True)

    def list_pending(self, limit: int = 1, task_ids: list[str] | None = None) -> list[IngestionTaskStatusModel]:
        tasks = list(self._tasks.values())
        if task_ids:
            allowed_ids = set(task_ids)
            tasks = [task for task in tasks if task.taskId in allowed_ids]
        pending = [task for task in tasks if task.status == "pending" and task.currentStage == "queued"]
        return sorted(pending, key=lambda task: task.createdAt)[: max(limit, 0)]

    def claim_pending(
        self,
        worker_id: str,
        limit: int = 1,
        task_ids: list[str] | None = None,
    ) -> list[IngestionTaskStatusModel]:
        claimed: list[IngestionTaskStatusModel] = []
        for task in self.list_pending(limit=limit, task_ids=task_ids):
            updated = task.model_copy(
                update={
                    "status": "running",
                    "updatedAt": task.updatedAt,
                    "metadata": {
                        **task.metadata,
                        "claimedByWorkerId": worker_id,
                    },
                }
            )
            self.upsert(updated)
            claimed.append(updated)
        return claimed

    def clear(self) -> None:
        self._tasks.clear()


class SQLiteIngestionRepository:
    def __init__(self, db_path: str) -> None:
        path = Path(db_path)
        if not path.is_absolute():
            path = PROJECT_ROOT.parent / path
        self._db_path = path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ingestion_tasks (
                    task_id TEXT PRIMARY KEY,
                    tenant_id TEXT,
                    org_id TEXT,
                    status TEXT NOT NULL,
                    current_stage TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def upsert(self, task: IngestionTaskStatusModel) -> None:
        payload_json = json.dumps(task.model_dump(mode="json"), ensure_ascii=False)
        with closing(self._connect()) as connection:
            self._upsert_connection(connection, task, payload_json)
            connection.commit()

    def get_by_id(self, task_id: str) -> IngestionTaskStatusModel | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload_json FROM ingestion_tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        return IngestionTaskStatusModel.model_validate(json.loads(row["payload_json"]))

    def list(self, tenant_id: str | None = None, org_id: str | None = None) -> list[IngestionTaskStatusModel]:
        where_clauses: list[str] = []
        params: list[str] = []
        if tenant_id is not None:
            where_clauses.append("tenant_id = ?")
            params.append(tenant_id)
        if org_id is not None:
            where_clauses.append("org_id = ?")
            params.append(org_id)
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"SELECT payload_json FROM ingestion_tasks {where_sql} ORDER BY created_at DESC"
        with closing(self._connect()) as connection:
            rows = connection.execute(query, params).fetchall()
        return [IngestionTaskStatusModel.model_validate(json.loads(row["payload_json"])) for row in rows]

    def list_pending(self, limit: int = 1, task_ids: list[str] | None = None) -> list[IngestionTaskStatusModel]:
        where_clauses = ["status = 'pending'", "current_stage = 'queued'"]
        params: list[object] = []
        if task_ids:
            placeholders = ",".join("?" for _ in task_ids)
            where_clauses.append(f"task_id IN ({placeholders})")
            params.extend(task_ids)
        params.append(max(limit, 0))
        query = f"""
            SELECT payload_json
            FROM ingestion_tasks
            WHERE {' AND '.join(where_clauses)}
            ORDER BY created_at ASC
            LIMIT ?
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, params).fetchall()
        return [IngestionTaskStatusModel.model_validate(json.loads(row["payload_json"])) for row in rows]

    def claim_pending(
        self,
        worker_id: str,
        limit: int = 1,
        task_ids: list[str] | None = None,
    ) -> list[IngestionTaskStatusModel]:
        claimed: list[IngestionTaskStatusModel] = []
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = self._list_pending_rows(connection, limit=limit, task_ids=task_ids)
            for row in rows:
                task = IngestionTaskStatusModel.model_validate(json.loads(row["payload_json"]))
                updated = task.model_copy(
                    update={
                        "status": "running",
                        "updatedAt": task.updatedAt,
                        "metadata": {
                            **task.metadata,
                            "claimedByWorkerId": worker_id,
                        },
                    }
                )
                self._upsert_connection(connection, updated)
                claimed.append(updated)
            connection.commit()
        return claimed

    def clear(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute("DELETE FROM ingestion_tasks")
            connection.commit()

    def _list_pending_rows(
        self,
        connection: sqlite3.Connection,
        *,
        limit: int,
        task_ids: list[str] | None,
    ) -> list[sqlite3.Row]:
        where_clauses = ["status = 'pending'", "current_stage = 'queued'"]
        params: list[object] = []
        if task_ids:
            placeholders = ",".join("?" for _ in task_ids)
            where_clauses.append(f"task_id IN ({placeholders})")
            params.extend(task_ids)
        params.append(max(limit, 0))
        query = f"""
            SELECT payload_json
            FROM ingestion_tasks
            WHERE {' AND '.join(where_clauses)}
            ORDER BY created_at ASC
            LIMIT ?
        """
        return connection.execute(query, params).fetchall()

    def _upsert_connection(
        self,
        connection: sqlite3.Connection,
        task: IngestionTaskStatusModel,
        payload_json: str | None = None,
    ) -> None:
        serialized = payload_json if payload_json is not None else json.dumps(task.model_dump(mode="json"), ensure_ascii=False)
        connection.execute(
            """
            INSERT INTO ingestion_tasks (
                task_id,
                tenant_id,
                org_id,
                status,
                current_stage,
                created_at,
                updated_at,
                payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
                tenant_id = excluded.tenant_id,
                org_id = excluded.org_id,
                status = excluded.status,
                current_stage = excluded.current_stage,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at,
                payload_json = excluded.payload_json
            """,
            (
                task.taskId,
                task.tenantId,
                task.orgId,
                task.status,
                task.currentStage,
                task.createdAt,
                task.updatedAt,
                serialized,
            ),
        )


def create_ingestion_repository() -> IngestionRepository:
    settings = get_settings()
    backend = settings.ingestion_backend.strip().lower()
    if backend == "memory":
        return InMemoryIngestionRepository()
    if backend == "sqlite":
        return SQLiteIngestionRepository(settings.ingestion_sqlite_path)
    raise ValueError(f"Unsupported ingestion backend: {settings.ingestion_backend}")


ingestion_repository = create_ingestion_repository()
