from __future__ import annotations

import unittest

from ragent_python.contracts.mcp import (
    MCPActorModel,
    MCPExecuteRequestModel,
    MCPExecutionContextModel,
    MCPPlannedToolCallModel,
)
from ragent_python.services.mcp_service import execute_mcp_runtime


class MCPServiceTests(unittest.TestCase):
    def test_list_knowledge_bases_tool_succeeds(self) -> None:
        response = execute_mcp_runtime(
            MCPExecuteRequestModel(
                plannedCalls=[
                    MCPPlannedToolCallModel(
                        toolCallId="tool_1",
                        toolName="list_knowledge_bases",
                        args={"limit": 10},
                    )
                ],
                context=MCPExecutionContextModel(
                    traceId="trace_1",
                    actor=MCPActorModel(
                        userId="user_1",
                        role="user",
                        tenantId="tenant_1",
                    ),
                ),
            )
        )

        statuses = [tool_call.status for tool_call in response.toolCalls]
        self.assertIn("queued", statuses)
        self.assertIn("running", statuses)
        self.assertIn("succeeded", statuses)

    def test_admin_guard_denies_setting_tool_for_user(self) -> None:
        response = execute_mcp_runtime(
            MCPExecuteRequestModel(
                plannedCalls=[
                    MCPPlannedToolCallModel(
                        toolCallId="tool_2",
                        toolName="get_system_setting",
                        args={"key": "chat.defaultModel"},
                    )
                ],
                context=MCPExecutionContextModel(
                    traceId="trace_2",
                    actor=MCPActorModel(
                        userId="user_2",
                        role="user",
                        tenantId="tenant_2",
                    ),
                ),
            )
        )

        final_status = response.toolCalls[-1].status
        self.assertEqual(final_status, "failed")


if __name__ == "__main__":
    unittest.main()
