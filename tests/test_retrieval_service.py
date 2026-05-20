from __future__ import annotations

import unittest

from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.contracts.ingestion import (
    IngestionExecutionPlanModel,
    IngestionSourceModel,
    IngestionTaskCreateRequestModel,
)
from ragent_python.services.ingestion_service import create_ingestion_task
from ragent_python.services.retrieval_service import execute_retrieval
from ragent_python.storage.ingestion_repository import ingestion_repository
from ragent_python.worker.ingestion_worker import run_ingestion_worker


class RetrievalServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        ingestion_repository.clear()

    def test_retrieval_returns_matching_chunks(self) -> None:
        response = execute_retrieval(
            InternalRetrievalRequestModel(
                traceId="trace_test",
                query="payroll benefits",
                tenantId="tenant_test",
            )
        )

        self.assertEqual(response.traceId, "trace_test")
        self.assertEqual(response.source, "python-composite-retrieval")
        self.assertGreater(len(response.chunks), 0)
        self.assertEqual(response.chunks[0].knowledgeBaseId, "kb_policy")

    def test_retrieval_respects_top_k(self) -> None:
        response = execute_retrieval(
            InternalRetrievalRequestModel(
                traceId="trace_test",
                query="product roadmap release",
                tenantId="tenant_test",
                topK=1,
            )
        )

        self.assertEqual(len(response.chunks), 1)

    def test_retrieval_can_search_ingested_chunks(self) -> None:
        task = create_ingestion_task(
            IngestionTaskCreateRequestModel(
                traceId="trace_ingested_retrieval",
                knowledgeBaseId="kb_ingested",
                documentId="doc_ingested",
                requestedBy="admin_retrieval",
                tenantId="tenant_test",
                orgId="org_test",
                source=IngestionSourceModel(
                    sourceType="upload",
                    uri="file:///tmp/ingested-retrieval.pdf",
                    filename="ingested-retrieval.pdf",
                    mimeType="application/pdf",
                    sizeBytes=1024,
                ),
                executionPlan=IngestionExecutionPlanModel(
                    embedding={"enabled": True, "model": "mock-embed", "adapter": "local"},
                    indexing={"enabled": True, "indexName": "kb_ingested", "storeType": "mock-qdrant"},
                ),
            )
        )
        run_ingestion_worker(limit=1, task_ids=[task.taskId])

        response = execute_retrieval(
            InternalRetrievalRequestModel(
                traceId="trace_test_ingested",
                query="ingested retrieval pdf",
                tenantId="tenant_test",
                orgId="org_test",
                knowledgeBaseIds=["kb_ingested"],
            )
        )

        self.assertGreater(len(response.chunks), 0)
        self.assertEqual(response.chunks[0].knowledgeBaseId, "kb_ingested")
        self.assertEqual(response.chunks[0].source, "python-ingestion-retrieval")
        self.assertEqual(response.chunks[0].metadata["provider"], "ingestion-task")


if __name__ == "__main__":
    unittest.main()
