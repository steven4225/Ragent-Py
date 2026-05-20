from __future__ import annotations

import json
import unittest
from base64 import b64encode

from ragent_python.contracts.ingestion import (
    IngestionExecutionPlanModel,
    IngestionSourceModel,
    IngestionTaskCreateRequestModel,
)
from ragent_python.contracts.internal_api import InternalChatRequestModel
from ragent_python.services.ingestion_service import create_ingestion_task
from ragent_python.services.chat_service import build_chat_turn_response, iter_chat_stream_events
from ragent_python.storage.ingestion_repository import ingestion_repository
from ragent_python.worker.ingestion_worker import run_ingestion_worker


class ChatServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        ingestion_repository.clear()
        self.request = InternalChatRequestModel(
            message="hello from test",
            conversationId="conv_test",
            userId="user_test",
            tenantId="tenant_test",
            orgId="org_test",
            role="user",
        )

    def test_build_chat_turn_response_returns_compatible_shape(self) -> None:
        response = build_chat_turn_response(self.request)

        self.assertTrue(response.traceId.startswith("chat_"))
        self.assertEqual(response.conversation.conversationId, "conv_test")
        self.assertEqual(response.userMessage.role, "user")
        self.assertEqual(response.userMessage.content, "hello from test")
        self.assertEqual(response.assistantMessage.role, "assistant")
        self.assertIn("Python chat runtime is active.", response.assistantMessage.content)
        self.assertFalse(response.plan.useRetrieval)
        self.assertFalse(response.plan.useTools)

    def test_chat_can_reference_newly_ingested_evidence(self) -> None:
        source_text = "Zephyr migration runbook says rollout owners must verify staging metrics before launch."
        encoded = b64encode(source_text.encode("utf-8")).decode("ascii")
        task = create_ingestion_task(
            IngestionTaskCreateRequestModel(
                traceId="trace_chat_ingested",
                knowledgeBaseId="kb_chat_ingested",
                documentId="doc_chat_ingested",
                requestedBy="admin_chat",
                tenantId="tenant_test",
                orgId="org_test",
                source=IngestionSourceModel(
                    sourceType="upload",
                    uri=f"data:text/plain;base64,{encoded}",
                    filename="zephyr-runbook.txt",
                    mimeType="text/plain",
                    sizeBytes=len(source_text),
                ),
                executionPlan=IngestionExecutionPlanModel(),
            )
        )
        run_ingestion_worker(limit=1, task_ids=[task.taskId])

        response = build_chat_turn_response(
            InternalChatRequestModel(
                message="What does the zephyr runbook say about rollout owners?",
                conversationId="conv_ingested",
                userId="user_test",
                tenantId="tenant_test",
                orgId="org_test",
                role="user",
            )
        )

        self.assertTrue(response.plan.useRetrieval)
        self.assertIn("Zephyr migration runbook says rollout owners", response.assistantMessage.content)
        self.assertEqual(response.assistantMessage.metadata["retrievalSource"], "python-composite-retrieval")

    def test_stream_emits_expected_phase1_events(self) -> None:
        events = [json.loads(line) for line in iter_chat_stream_events(self.request)]

        self.assertGreaterEqual(len(events), 5)
        self.assertEqual(events[0]["type"], "chat.started")
        self.assertEqual(events[1]["type"], "thinking.delta")
        self.assertEqual(events[2]["type"], "thinking.completed")
        self.assertEqual(events[-2]["type"], "message.completed")
        self.assertEqual(events[-1]["type"], "chat.completed")

        delta_events = [event for event in events if event["type"] == "message.delta"]
        self.assertGreater(len(delta_events), 0)
        self.assertTrue(all(isinstance(event["delta"], str) for event in delta_events))

    def test_stream_emits_tool_call_events_when_message_requests_tools(self) -> None:
        request = InternalChatRequestModel(
            message="please list knowledge bases",
            conversationId="conv_tools",
            userId="user_test",
            tenantId="tenant_test",
            orgId="org_test",
            role="user",
        )

        events = [json.loads(line) for line in iter_chat_stream_events(request)]
        tool_events = [event for event in events if event["type"] == "tool.call"]

        self.assertGreaterEqual(len(tool_events), 3)
        self.assertEqual(tool_events[0]["toolCall"]["status"], "queued")
        self.assertEqual(tool_events[1]["toolCall"]["status"], "running")
        self.assertEqual(tool_events[-1]["toolCall"]["status"], "succeeded")

    def test_stream_message_completed_preserves_retrieval_and_tool_metadata(self) -> None:
        source_text = "Atlas launch memo says rollback approval requires two green canary windows before production unlock."
        encoded = b64encode(source_text.encode("utf-8")).decode("ascii")
        task = create_ingestion_task(
            IngestionTaskCreateRequestModel(
                traceId="trace_stream_metadata",
                knowledgeBaseId="kb_stream_metadata",
                documentId="doc_stream_metadata",
                requestedBy="admin_chat",
                tenantId="tenant_test",
                orgId="org_test",
                source=IngestionSourceModel(
                    sourceType="upload",
                    uri=f"data:text/plain;base64,{encoded}",
                    filename="atlas-launch.txt",
                    mimeType="text/plain",
                    sizeBytes=len(source_text),
                ),
                executionPlan=IngestionExecutionPlanModel(),
            )
        )
        run_ingestion_worker(limit=1, task_ids=[task.taskId])

        request = InternalChatRequestModel(
            message="Please check setting chat.defaultModel and explain what the atlas launch memo requires before production unlock.",
            conversationId="conv_stream_metadata",
            userId="user_test",
            tenantId="tenant_test",
            orgId="org_test",
            role="admin",
        )

        events = [json.loads(line) for line in iter_chat_stream_events(request)]
        tool_events = [event for event in events if event["type"] == "tool.call"]
        completed = next(event for event in events if event["type"] == "message.completed")
        metadata = completed["assistantMessage"]["metadata"]

        self.assertGreaterEqual(len(tool_events), 3)
        self.assertEqual(metadata["retrievalSource"], "python-composite-retrieval")
        self.assertGreater(metadata["context"]["evidenceCount"], 0)
        self.assertGreater(len(metadata["retrievalExecution"]["chunks"]), 0)
        self.assertGreater(len(metadata["toolCalls"]), 0)
        self.assertEqual(metadata["toolCalls"][-1]["toolName"], "get_system_setting")
        self.assertEqual(metadata["toolCalls"][-1]["status"], "succeeded")


if __name__ == "__main__":
    unittest.main()
