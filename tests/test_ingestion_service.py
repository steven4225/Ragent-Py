from __future__ import annotations

import unittest

from ragent_python.contracts.ingestion import (
    IngestionExecutionPlanModel,
    IngestionSourceModel,
    IngestionTaskCreateRequestModel,
)
from ragent_python.services.ingestion_service import create_ingestion_task, get_ingestion_task, list_ingestion_tasks
from ragent_python.storage.ingestion_repository import ingestion_repository
from ragent_python.worker.ingestion_worker import run_ingestion_worker


class IngestionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        ingestion_repository.clear()

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

    def test_worker_run_transitions_task_to_completed(self) -> None:
        task = create_ingestion_task(
            IngestionTaskCreateRequestModel(
                traceId="trace_ingestion_3",
                knowledgeBaseId="kb_product",
                documentId="doc_product_1",
                requestedBy="admin_3",
                tenantId="tenant_c",
                orgId="org_c",
                source=IngestionSourceModel(
                    sourceType="upload",
                    uri="file:///tmp/product.md",
                    filename="product.md",
                    mimeType="text/markdown",
                    sizeBytes=512,
                ),
                executionPlan=IngestionExecutionPlanModel(),
            )
        )

        result = run_ingestion_worker(limit=1, task_ids=[task.taskId])
        updated = get_ingestion_task(task.taskId)

        self.assertEqual(result.processedTaskIds, [task.taskId])
        self.assertEqual(result.succeededTaskIds, [task.taskId])
        self.assertEqual(result.failedTaskIds, [])
        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, "succeeded")
        self.assertEqual(updated.currentStage, "completed")
        self.assertEqual(updated.attemptCount, 1)
        self.assertIsNotNone(updated.startedAt)
        self.assertIsNotNone(updated.finishedAt)
        self.assertEqual(updated.trace[-1].stage, "completed")

    def test_worker_run_can_mark_task_failed(self) -> None:
        task = create_ingestion_task(
            IngestionTaskCreateRequestModel(
                traceId="trace_ingestion_4",
                knowledgeBaseId="kb_failure",
                documentId="doc_failure_1",
                requestedBy="admin_4",
                tenantId="tenant_d",
                orgId="org_d",
                source=IngestionSourceModel(
                    sourceType="upload",
                    uri="fail:///tmp/failure.pdf",
                    filename="failure.pdf",
                    mimeType="application/pdf",
                    sizeBytes=128,
                ),
                executionPlan=IngestionExecutionPlanModel(),
                metadata={"forceFailure": True},
            )
        )

        result = run_ingestion_worker(limit=1, task_ids=[task.taskId])
        updated = get_ingestion_task(task.taskId)

        self.assertEqual(result.processedTaskIds, [task.taskId])
        self.assertEqual(result.failedTaskIds, [task.taskId])
        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, "failed")
        self.assertEqual(updated.currentStage, "failed")
        self.assertEqual(updated.failureStage, "parser")
        self.assertEqual(updated.trace[-1].stage, "failed")


if __name__ == "__main__":
    unittest.main()
