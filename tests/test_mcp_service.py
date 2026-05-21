from __future__ import annotations

import json
import os
import tempfile
import unittest

from ragent_python.contracts.mcp import (
    MCPActorModel,
    MCPExecuteRequestModel,
    MCPExecutionContextModel,
    MCPPlannedToolCallModel,
)
from ragent_python.config import get_settings
from ragent_python.contracts.ingestion import IngestionExecutionPlanModel, IngestionSourceModel, IngestionTaskCreateRequestModel
from ragent_python.services.ingestion_service import create_ingestion_task
from ragent_python.services.mcp_service import execute_mcp_runtime
from ragent_python.storage.ingestion_repository import ingestion_repository


class MCPServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        ingestion_repository.clear()
        os.environ.pop("PYTHON_PLATFORM_STATE_PATH", None)
        os.environ.pop("TS_PLATFORM_STATE_PATH", None)
        get_settings.cache_clear()

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
        self.assertEqual(response.toolCalls[-1].output["summary"], "Admin role required.")

    def test_admin_can_read_scoped_setting_from_platform_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, "platform-state.json")
            with open(state_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "settings": [
                            {
                                "key": "auth.scope.e2e.dynamic",
                                "value": "enabled",
                                "description": "dynamic setting",
                                "tenantId": "tenant_dynamic",
                                "orgId": "org_dynamic",
                            }
                        ]
                    },
                    handle,
                )
            os.environ["PYTHON_PLATFORM_STATE_PATH"] = state_path
            get_settings.cache_clear()

            response = execute_mcp_runtime(
                MCPExecuteRequestModel(
                    plannedCalls=[
                        MCPPlannedToolCallModel(
                            toolCallId="tool_3",
                            toolName="get_system_setting",
                            args={"key": "auth.scope.e2e.dynamic"},
                        )
                    ],
                    context=MCPExecutionContextModel(
                        traceId="trace_3",
                        actor=MCPActorModel(
                            userId="admin_1",
                            role="admin",
                            tenantId="tenant_dynamic",
                            orgId="org_dynamic",
                        ),
                    ),
                )
            )

            self.assertEqual(response.toolCalls[-1].status, "succeeded")
            self.assertEqual(response.toolCalls[-1].output["data"]["value"], "enabled")

    def test_admin_can_read_ingestion_task_tool(self) -> None:
        task = create_ingestion_task(
            IngestionTaskCreateRequestModel(
                traceId="trace_ingestion_tool",
                knowledgeBaseId="kb_tool",
                documentId="doc_tool",
                requestedBy="admin_tool",
                tenantId="tenant_tool",
                orgId="org_tool",
                source=IngestionSourceModel(
                    sourceType="upload",
                    uri="data:text/plain;base64,SGVsbG8=",
                    filename="tool.txt",
                    mimeType="text/plain",
                    sizeBytes=5,
                ),
                executionPlan=IngestionExecutionPlanModel(),
            )
        )

        response = execute_mcp_runtime(
            MCPExecuteRequestModel(
                plannedCalls=[
                    MCPPlannedToolCallModel(
                        toolCallId="tool_4",
                        toolName="get_ingestion_task",
                        args={"taskId": task.taskId},
                    )
                ],
                context=MCPExecutionContextModel(
                    traceId="trace_4",
                    actor=MCPActorModel(
                        userId="admin_2",
                        role="admin",
                        tenantId="tenant_tool",
                        orgId="org_tool",
                    ),
                ),
            )
        )

        self.assertEqual(response.toolCalls[-1].status, "succeeded")
        self.assertEqual(response.toolCalls[-1].output["data"]["taskId"], task.taskId)


if __name__ == "__main__":
    unittest.main()
