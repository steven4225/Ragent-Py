"""Typed renderer blocks.

The assistant message can attach a list of typed blocks that the frontend
renders deterministically (product cards, comparison tables, evidence panels,
etc.) instead of relying on markdown heuristics. Step A only ships three
universal blocks; module-specific blocks (e.g. ProductCardBlock,
SpecCompareBlock) are registered by their owning module under
`modules/<name>/blocks.py` and contributed via `ModuleHookResult.renderer_blocks`.

Backward compatibility: when `AssistantMessageBlocks.blocks` is empty or the
field is absent, the frontend falls back to rendering the legacy
``MessageModel.content`` as a single text block.
"""

from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel, Field


class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    content: str


class EvidenceChunk(BaseModel):
    chunk_id: str
    title: str
    content: str
    source: str
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceBlock(BaseModel):
    type: Literal["evidence"] = "evidence"
    chunks: list[EvidenceChunk] = Field(default_factory=list)


class ToolCallBlock(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    tool_call_id: str
    tool_name: str
    status: Literal["queued", "running", "succeeded", "failed"]
    args: dict[str, Any] = Field(default_factory=dict)
    summary: str | None = None
    output: Any | None = None


RendererBlock = Union[TextBlock, EvidenceBlock, ToolCallBlock]


class AssistantMessageBlocks(BaseModel):
    trace_id: str
    blocks: list[RendererBlock] = Field(default_factory=list)
