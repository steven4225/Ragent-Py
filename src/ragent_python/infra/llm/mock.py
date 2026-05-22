"""Mock generation adapter.

Mirrors the legacy hardcoded template in `chat_service._build_assistant_text`
so existing tests stay green. The mock is the unconditional last fallback in
the resolver chain; `/healthz` surfaces it so E2E gates can reject it.
"""

from __future__ import annotations

from typing import AsyncIterator

from ragent_python.core.generation.adapter import (
    GenerationChunk,
    GenerationRequest,
    GenerationResult,
)


class MockGenerationAdapter:
    name = "mock"

    def is_available(self) -> bool:
        return True

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        text = self._render(request)
        return GenerationResult(
            text=text,
            finish_reason="stop",
            input_tokens=None,
            output_tokens=None,
            model="mock-phase1",
            provider=self.name,
            metadata={"mode": "phase1-local-retrieval"},
        )

    async def stream(self, request: GenerationRequest) -> AsyncIterator[GenerationChunk]:
        text = self._render(request)
        words = text.split(" ")
        if not words:
            yield GenerationChunk(delta="", finish_reason="stop")
            return
        for index, word in enumerate(words):
            piece = word if index == 0 else " " + word
            yield GenerationChunk(delta=piece, finish_reason=None)
        yield GenerationChunk(delta="", finish_reason="stop")

    @staticmethod
    def _render(request: GenerationRequest) -> str:
        last_user = next(
            (msg.content for msg in reversed(request.messages) if msg.role == "user"),
            "",
        )
        return f"Python chat runtime is active. Received message: {last_user.strip()}"
