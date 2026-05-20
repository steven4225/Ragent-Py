from __future__ import annotations

import unittest

from ragent_python.contracts.ingestion import (
    IngestionExecutionPlanModel,
    IngestionSourceModel,
    IngestionTaskCreateRequestModel,
)
from ragent_python.services.ingestion_service import create_ingestion_task, get_ingestion_task, list_ingestion_tasks


class IngestionServiceTests(unittest.TestCase):
    def test_create_ingestion_task_returns_queued_pending_status(self) -> None:
        task = create_ingestion_task(
            IngestionTaskCreateRequestModel(
                traceId="trace_ingestion_1",
                knowledgeBaseId="kb_policy",
                documentId="doc_policy_1",
                requestedBy="admin_1",
                tenantId="tenant_a",
                orgId="org_a",
                source=IngestionSourceModel(
                    sourceType="upload",
                    uri="file:///tmp/policy.pdf",
                    filename="policy.pdf",
                    mimeType="application/pdf",
                    sizeBytes=1024,
                ),
                executionPlan=IngestionExecutionPlanModel(),
            )
        )

        self.assertTrue(task.taskId.startswith("ing_"))
        self.assertEqual(task.status, "pending")
        self.assertEqual(task.currentStage, "queued")
        self.assertEqual(len(task.trace), 2)
        self.assertEqual(task.trace[0].stage, "task-created")
        self.assertEqual(task.trace[1].stage, "queued")

    def test_get_and_list_ingestion_tasks_scope_by_tenant_and_org(self) -> None:
        task = create_ingestion_task(
            IngestionTaskCreateRequestModel(
                traceId="trace_ingestion_2",
                knowledgeBaseId="kb_ops",
                documentId="doc_ops_1",
                requestedBy="admin_2",
                tenantId="tenant_b",
                orgId="org_b",
                source=IngestionSourceModel(
                    sourceType="upload",
                    uri="file:///tmp/ops.md",
                    filename="ops.md",
                    mimeType="text/markdown",
                    sizeBytes=256,
                ),
                executionPlan=IngestionExecutionPlanModel(),
            )
        )

        loaded = get_ingestion_task(task.taskId)
        scoped_items = list_ingestion_tasks(tenant_id="tenant_b", org_id="org_b").items

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.taskId, task.taskId)
        self.assertTrue(any(item.taskId == task.taskId for item in scoped_items))


if __name__ == "__main__":
    unittest.main()
