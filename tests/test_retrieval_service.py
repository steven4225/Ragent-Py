from __future__ import annotations

import unittest

from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.services.retrieval_service import execute_retrieval


class RetrievalServiceTests(unittest.TestCase):
    def test_retrieval_returns_matching_chunks(self) -> None:
        response = execute_retrieval(
            InternalRetrievalRequestModel(
                traceId="trace_test",
                query="payroll benefits",
                tenantId="tenant_test",
            )
        )

        self.assertEqual(response.traceId, "trace_test")
        self.assertEqual(response.source, "python-local-retrieval")
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


if __name__ == "__main__":
    unittest.main()
