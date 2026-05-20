from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ragent_python.contracts.ingestion import (
    IngestionExecutionPlanModel,
    IngestionSourceModel,
    IngestionTaskStatusModel,
)
from ragent_python.storage.ingestion_repository import SQLiteIngestionRepository


class SQLiteIngestionRepositoryTests(unittest.TestCase):
    def test_sqlite_repository_persists_tasks_across_instances(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "ingestion.db"
            repository_a = SQLiteIngestionRepository(str(db_path))
            repository_b = SQLiteIngestionRepository(str(db_path))

            task = IngestionTaskStatusModel(
                taskId="ing_sqlite_1",
                traceId="trace_sqlite_1",
                knowledgeBaseId="kb_sqlite",
                documentId="doc_sqlite",
                requestedBy="admin_sqlite",
                tenantId="tenant_sqlite",
                orgId="org_sqlite",
                source=IngestionSourceModel(
                    sourceType="upload",
                    uri="file:///tmp/sqlite.pdf",
                    filename="sqlite.pdf",
                    mimeType="application/pdf",
                    sizeBytes=2048,
                ),
                status="pending",
                currentStage="queued",
                executionPlan=IngestionExecutionPlanModel(),
            )
            repository_a.upsert(task)

            loaded = repository_b.get_by_id("ing_sqlite_1")
            pending = repository_b.list_pending(limit=5)

            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.taskId, task.taskId)
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0].taskId, task.taskId)


if __name__ == "__main__":
    unittest.main()
