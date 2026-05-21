"""UI rendering contracts.

Defines the typed renderer blocks that flow from the Python execution plane
to the TS rendering layer. Python is the source of truth; the TS side either
hand-mirrors the schema in `web/lib/contracts.ts` (Step A/B/C) or consumes a
JSON-Schema-generated artefact (Step E).
"""

from ragent_python.ui_contracts.blocks import (
    EvidenceBlock,
    RendererBlock,
    TextBlock,
    ToolCallBlock,
    AssistantMessageBlocks,
)

__all__ = [
    "AssistantMessageBlocks",
    "EvidenceBlock",
    "RendererBlock",
    "TextBlock",
    "ToolCallBlock",
]
