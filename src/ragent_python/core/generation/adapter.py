"""GenerationAdapter contract.

The adapter abstracts a single LLM provider behind two operations:
`generate()` for one-shot completion and `stream()` for incremental delta
streaming. Token budgets, stop sequences, and metadata flow through the
request so the platform (not the module) controls cost and observability.

Step A only defines the contract and the data shapes; concrete providers
(OpenAI, Anthropic, Ollama) land in `infra/llm/*` in a later step. A `mock`
provider lives in `infra/llm/mock.py` to keep tests and dev flows running.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field


GenerationRole = Literal["system", "user", "assistant", "tool"]
GenerationFinishReason = Literal["stop", "length", "tool_call", "content_filter", "error"]


class GenerationMessage(BaseModel):
    role: GenerationRole
    content: str
    name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GenerationRequest(BaseModel):
    messages: list[GenerationMessage]
    max_input_tokens: int = 16000
    max_output_tokens: int = 2000
    temperature: float = 0.2
    stop: list[str] = Field(default_factory=list)
    model_hint: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GenerationChunk(BaseModel):
    delta: str
    finish_reason: GenerationFinishReason | None = None


class GenerationResult(BaseModel):
    text: str
    finish_reason: GenerationFinishReason
    input_tokens: int | None = None
    output_tokens: int | None = None
    model: str | None = None
    provider: str
    metadata: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class GenerationAdapter(Protocol):
    """Provider-agnostic generation interface."""

    name: str

    async def generate(self, request: GenerationRequest) -> GenerationResult: ...

    def stream(self, request: GenerationRequest) -> AsyncIterator[GenerationChunk]: ...

    def is_available(self) -> bool: ...
