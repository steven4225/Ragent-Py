from __future__ import annotations

import json
import unittest

from ragent_python.contracts.internal_api import InternalChatRequestModel
from ragent_python.services.chat_service import build_chat_turn_response, iter_chat_stream_events


class ChatServiceTests(unittest.TestCase):
    def setUp(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
